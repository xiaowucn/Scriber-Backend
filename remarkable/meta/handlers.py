import hashlib
import importlib
import io
import json
import logging
import os
import shutil
import sys
import time
from io import BytesIO
from pathlib import Path
from subprocess import TimeoutExpired

import peewee
import qrcode
from webargs import fields

from remarkable.base_handler import Auth, BaseHandler, PermCheckHandler, route
from remarkable.common.apispec_decorators import doc, use_kwargs
from remarkable.common.constants import PdfinsightRetCode, PDFParseStatus
from remarkable.common.enums import TaskType
from remarkable.common.exceptions import CustomError, InvalidInterdocError, PDFInsightNotFound, ShellCmdError
from remarkable.common.storage import localstorage
from remarkable.common.util import (
    compact_dumps,
    get_ocr_expire_msg,
    read_zip_first_file,
    release_parse_file_lock,
    subprocess_exec,
)
from remarkable.config import ENV, get_config, project_root
from remarkable.db import db, init_rdb, pw_db
from remarkable.file_flow.tasks import create_flow_task
from remarkable.file_flow.tasks.task import TaskStatus
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.diff.common import CCXI_CACHE_PATH
from remarkable.pw_db_services import PeeweeService
from remarkable.pw_models.model import AlembicVersion, NewTimeRecord
from remarkable.service.new_file import NewFileService, _ModelVersion
from remarkable.worker.tasks import process_file, upload_file_to_studio_extract

logger = logging.getLogger(__name__)


@route(r"/test")
class TestHandler(BaseHandler):
    @doc(summary="测试接口", description="这是一个用来测试服务是否正常的接口", tags=["meta"])
    @Auth("browse")
    async def get(self):
        alembic_ver = await pw_db.first(AlembicVersion.select())
        with pw_db.allow_sync():
            admin = (
                NewAdminUser.select(NewAdminUser.permission)
                .where(NewAdminUser.name == "admin")
                .order_by(NewAdminUser.id.desc())
                .first()
            )
        pg_ver = await pw_db.first("select version()", default_row_type=peewee.ROW.DICT)
        return self.data({"pw": {**alembic_ver.to_dict(), "perms": admin.permission, "pg_ver": pg_ver}})

    @Auth("browse")
    async def post(self):
        url = self.request.full_url()
        return self.data({"url": url})


@route(r"/lab")
class LabHandler(BaseHandler):
    @Auth("browse")
    async def get(self):
        time.sleep(5)
        return self.data({})


@route(r"/diagnosis")
class DiagnosisHandler(BaseHandler):
    args = {
        "is_qrcode": fields.Bool(load_default=True, data_key="qrcode"),
        "fid": fields.Int(load_default=0),
    }

    @doc(summary="诊断接口", description="获得服务的部分配置,版本参数", tags=["meta"])
    @Auth("manage_user")
    @use_kwargs(args, location="query")
    async def get(self, is_qrcode, fid):
        ret = {
            "proj_dir": project_root,
            "env": ENV,
            "py_ver": ".".join([str(i) for i in sys.version_info[:3]]),
            "git_rev": await self.run_in_executor(self.get_git_revision),
            "alembic_ver": await db.raw_sql("select version_num from alembic_version", "scalar"),
            "pg_ver": (await db.raw_sql("select version()", "scalar")).split(",")[0],
            "pg_size": await db.raw_sql(
                "SELECT pg_size_pretty(pg_database_size('{}'))".format(get_config("db.dbname")), "scalar"
            ),
            "redis_ver": (await self.run_in_executor(init_rdb().info, "server")).get("redis_version"),
            "disk_usage": await self.run_in_executor(self.get_disk_usage),
            "uptime": (await self.run_in_executor(subprocess_exec, "uptime")).strip(),
            "online_uids": await self.run_in_executor(self.get_online_users),
            "session_count": await self.run_in_executor(self.get_session_count),
            "env_params": self.get_env_params(),
            "queued_tasks": await self.run_in_executor(init_rdb().llen, "celery"),
        }
        if fid:
            file = await NewFile.find_by_id(fid)
            if not file:
                return self.error(_("not found file"))
            model_version = read_zip_first_file(localstorage.mount(file.pdfinsight_path()), msgspec_type=_ModelVersion)
            ret["model_version"] = model_version.model_version

        if not is_qrcode:
            return self.data(ret)
        img = await self.run_in_executor(self.draw_qrcode, ret)
        return await self.export(img, content_type="image/png")

    @staticmethod
    def draw_qrcode(data):
        img = qrcode.make(compact_dumps(data))
        img_buffer = BytesIO()
        img.save(img_buffer)
        return img_buffer.getvalue()

    @classmethod
    def get_disk_usage(cls):
        total, used, free = shutil.disk_usage(Path("/"))
        multi = 2**30
        return {
            "total": f"{total // multi}G",
            "used": f"{used // multi}G",
            "free": f"{free // multi}G",
            "proj_dir": f"{cls.get_dir_disk_usage('')}",
            "data_dir": f"{cls.get_dir_disk_usage('data')}",
            "pg_dir": f"{cls.get_dir_disk_usage('data/pg_data')}",
        }

    @staticmethod
    def get_dir_disk_usage(dir_path):
        abs_path = Path(project_root) / dir_path
        try:
            ret = subprocess_exec(f"du -sh {abs_path}", timeout=3)
        except (ShellCmdError, TimeoutExpired):
            return ""
        return ret.strip().split()[0]

    @classmethod
    def get_git_revision(cls):
        ret = {
            "branch": subprocess_exec("git branch --show-current 2>/dev/null").strip(),
            "ver": subprocess_exec("git rev-parse --short HEAD 2>/dev/null").strip(),
        }
        revision_path = Path(project_root) / ".git_revision"
        if revision_path.is_file():
            with open(revision_path, "r") as file_obj:
                for k in ret:
                    ret[k] = file_obj.readline().strip()
        return f"{ret['ver']}@{ret['branch']}"

    @classmethod
    def get_online_users(cls):
        def _uid_iter():
            for s_key in init_rdb().scan_iter(f"{get_config('app.app_id', 'scriber')}:uid:*"):
                uid = s_key.split(":")[-1]
                if not uid.startswith("-"):  # -1 为非法用户 id
                    yield uid

        return ",".join(_uid_iter())

    @classmethod
    def get_session_count(cls):
        return len(list(init_rdb().scan_iter(f"{get_config('app.app_id', 'scriber')}:session:*")))

    @staticmethod
    def get_env_params():
        ret = {
            name.replace("SCRIBER_", "").replace("PDFPARSER_", ""): os.getenv(name)
            for name in os.environ
            if name.startswith("SCRIBER_") or name.startswith("PDFPARSER_")
        }
        return ret or None


@route("/load-handlers")
class LoadHandler(BaseHandler):
    @doc(summary="加载指定 Handler", tags=["meta"])
    @use_kwargs({"names": fields.List(fields.Str(), data_key="name")}, location="query")
    @Auth("browse")
    async def get(self, names: list[str]):
        handlers = set(route.HANDLERS)
        errors = []
        for plugin in names:
            logger.info(f"Importing {plugin=}")
            try:
                mod = await self.run_in_executor(importlib.import_module, f"remarkable.plugins.{plugin}")
            except ModuleNotFoundError as exp:
                errors.append(f"{exp}")
                logger.warning(f"{exp}")
            else:
                getattr(mod, "init", lambda: logger.warning('\tNo "init" func found'))()

        patterns = set(route.HANDLERS) - handlers
        if not patterns:
            return self.error("\n".join(errors) or "No handlers loaded", 400)

        self.application.add_handlers(r".*", [(p, route.HANDLERS[p]) for p in patterns])
        for handler in patterns:
            logger.info("\t%s", handler)
        msg = f"Loaded {len(patterns)} handlers"
        logger.info(msg)
        return self.data(msg)


@route(r"/files/(\d+)/hash/([0-9a-fA-F]+)/preprocess_complete")
class PreProcessCallbackHandler(PermCheckHandler):
    async def post(self, fid, checksum):
        fid = int(fid)
        # 有可能回调之前该file已经被删除,但仍期望能执行clean_and_save()
        file = await NewFile.find_by_id(fid, include_deleted=True)
        if not file:
            raise CustomError(_("not found file"))

        conditions = (NewFile.hash == file.hash, NewFile.pdfinsight.is_null(), NewFile.id != file.id)
        same_files = await pw_db.execute(NewFile.select(include_deleted=True).where(*conditions))

        if get_config("client.name") == "nafmii" and self.get_argument("status", None) == "start":
            if file.pdf_parse_status == PDFParseStatus.PDFINSIGHT_PARSING:
                logger.info(f"file {file.id} is in parsing status, no need to update status")
                return self.data(None)
            await NewTimeRecord.update_record(fid, "insight_queue_stamp")
            for file in same_files:
                await NewTimeRecord.update_record(file.id, "insight_queue_stamp")
            await file.update_(pdf_parse_status=PDFParseStatus.PDFINSIGHT_PARSING)
            logger.info(f"file {file.id} is in status {file.pdf_parse_status}, the file start to parse")
            return self.data(None)

        release_parse_file_lock(checksum)

        inter_doc = self.request.files.get("file", None)
        pdf_file = self.request.files.get("pdf", None)
        revise_docx = self.request.files.get("revise_docx", None)
        origin_docx = self.request.files.get("origin_docx", None)
        error_code = self.get_argument("error_code", None)
        # ret_status = self.get_argument('status', None)
        # error_msg = self.get_argument('error_msg', None)

        flow_task = await create_flow_task(get_config("client.name"), start_value=TaskStatus.parsing)
        db_service = PeeweeService.create()

        if error_code and int(error_code) == PdfinsightRetCode.COLORING_FAILED:
            # docx 在涂色流程解析异常时会回传错误信息（error_code=30），然后走pdf解析流程（as_pdf=1）
            await flow_task.receive_fail_callback(file.id, caused_by_coloring=True, db_service=db_service)

            flow_task.current_state = TaskStatus.initialized
            enable_ocr = await db_service.molds.verify_enable_ocr(
                file.molds, (get_config("web.force_ocr_mold_list") or [])
            )
            await flow_task.parse_file(
                file, enable_orc=enable_ocr, force_as_pdf=True, force=True, db_service=db_service
            )
            logger.info(f"Coloring process parsing exception, re-parse, {file.id=}")
            return self.error("Coloring process parsing exception, re-parse")

        if not inter_doc:
            # 未收到interdoc文件，视为解析失败
            await flow_task.receive_fail_callback(file.id, db_service=db_service)
            logging.error(
                f"No interdoc found for file: {file.id=}, {file.name=}, {file.hash=}, {file.pdf_parse_status=}."
            )
            return self.error(_("not found upload document"))

        if not file.pdf and not pdf_file:
            # 本地pdf文件不存在,且没有收到pdf文件，视为解析失败
            await flow_task.receive_fail_callback(file.id, db_service=db_service)
            logging.error(f"No PDF found for file: {file.id=}, {file.name=}, {file.hash=}, {file.pdf_parse_status=}.")
            return self.error(_("not found upload pdf"))

        same_fid = await pw_db.first(NewFile.select(NewFile.id).where(NewFile.hash == file.hash, NewFile.id != file.id))
        await self.run_in_executor(
            self.clean_and_save, file, inter_doc, pdf_file, revise_docx, origin_docx, same_fid is not None
        )
        await pw_db.update(file, only=["pdfinsight", "pdf", "revise_docx", "docx", "page"])
        await self.update_file_info(file)

        # 30min内上传的同hash文件不会跑解析,于此处更新pdfinsight数据及后续操作
        for same_file in same_files:
            await same_file.update_(
                pdf_parse_status=file.pdf_parse_status,
                pdfinsight=file.pdfinsight,
                pdf=file.pdf,
                revise_docx=file.revise_docx,
                meta_info=file.meta_info,
                docx=file.docx,
            )
        await self.post_pipe_after_succeed(file, *same_files)

        return self.write(file.to_dict())

    @staticmethod
    async def update_file_info(file: NewFile):
        ocr_expired_info = get_ocr_expire_msg(PdfinsightReader(localstorage.mount(file.pdfinsight_path())))
        meta_info = file.meta_info or {}
        meta_info.update(ocr_expired_info)
        params = {"meta_info": meta_info, "pdf_parse_status": PDFParseStatus.PARSED}
        if ocr_expired_info["is_ocr_expired"]:
            params["pdf_parse_status"] = PDFParseStatus.OCR_EXPIRED
        else:
            try:
                NewFileService.check_pdfinsight(file)
            except (PDFInsightNotFound, InvalidInterdocError) as exp:
                # 这里认为 interdoc 数据有问题 所以修改的是 pdf_parse_status
                logger.warning(str(exp))
                params["pdf_parse_status"] = (
                    PDFParseStatus.FAIL if isinstance(exp, PDFInsightNotFound) else PDFParseStatus.UN_CONFIRMED
                )

        await file.update_(**params)

    @staticmethod
    async def post_pipe_after_succeed(*files: NewFile):
        for file in files:
            if file.studio_upload_id is None:
                upload_file_to_studio_extract.delay(file.id, file.molds)
            await NewTimeRecord.update_record(file.id, "insight_parse_stamp")
            await process_file(file, force_predict=True, create_cache=True)

    @staticmethod
    def clean_and_save(file: NewFile, inter_doc, pdf_file, revise_docx, origin_docx, exist_same_file):
        from utensils.zip import read_zip_first_file

        # Remove expired files
        if file.pdfinsight_path() and not exist_same_file:
            localstorage.delete_file(file.pdfinsight_path())
            localstorage.delete_dir(file.label_cache_dir)
            # romove ccxi pdfinsight cache
            ccxi_path = os.path.join(CCXI_CACHE_PATH, file.pdfinsight[:2], file.pdfinsight[2:])
            localstorage.delete_file(ccxi_path)

        inter_doc = inter_doc[0]
        file.pdfinsight = hashlib.md5(inter_doc["body"]).hexdigest()
        page = len(json.loads(read_zip_first_file(io.BytesIO(inter_doc["body"]))).get("pages", []))
        file.page = page
        localstorage.write_file(file.pdfinsight_path(), inter_doc["body"])

        # 新上传的非pdf文件 file.pdf 为空 使用inv重跑时 file.pdf是有值的
        # 会导致旧的pdf删除不掉 新的不会更新 所以不能加and前面  not file_obj.pdf 的条件
        # if not file_obj.pdf and pdf_file:
        if pdf_file:
            if file.pdf_path() and not exist_same_file:
                # 当前file新数据和旧数据有差异时，旧的pdf_file 会成为垃圾文件，故先清理掉
                # 存在同hash的其他file时,本着不修改旧数据的原则，跳过此操作
                localstorage.delete_file(file.pdf_path())

            pdf_file = pdf_file[0]
            file.pdf = hashlib.md5(pdf_file["body"]).hexdigest()
            localstorage.write_file(file.pdf_path(), pdf_file["body"])
        if get_config("web.store_revise_docx") and revise_docx:
            if file.revise_docx_path() and not exist_same_file:
                localstorage.delete_file(file.revise_docx_path())

            revise_docx = revise_docx[0]
            file.revise_docx = hashlib.md5(revise_docx["body"]).hexdigest()
            localstorage.write_file(file.revise_docx_path(), revise_docx["body"])

        if file.task_type == TaskType.CLEAN_FILE.value and origin_docx and file.is_word:
            if file.docx_path() and not exist_same_file:
                localstorage.delete_file(file.docx_path())

            origin_docx = origin_docx[0]
            file.docx = hashlib.md5(origin_docx["body"]).hexdigest()
            localstorage.write_file(file.docx_path(), origin_docx["body"])
