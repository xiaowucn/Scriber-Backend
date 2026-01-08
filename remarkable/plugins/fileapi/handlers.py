import http
import io
import logging
import os
from collections import defaultdict

import speedy.peewee_plus.orm
from marshmallow import Schema, fields
from pdfparser.pdftools.pdf_util import PDFUtil
from pdfparser.pdftools.pdfium_util import PDFiumUtil
from peewee import JOIN
from tornado.httputil import HTTPFile

from remarkable import config
from remarkable.base_handler import Auth, BaseHandler, DbQueryHandler, PermCheckHandler
from remarkable.common import field_validate
from remarkable.common.apispec_decorators import doc, use_args, use_kwargs
from remarkable.common.constants import (
    SUPPORTED_SUFFIXES,
    FileAnswerMergeStrategy,
    HistoryAction,
    PDFParseStatus,
    PublicStatus,
    TagType,
)
from remarkable.common.enums import ClientName, FileTask, NafmiiEventStatus, NafmiiEventType, TaskType
from remarkable.common.exceptions import CustomError
from remarkable.common.schema import attribute_id
from remarkable.common.storage import localstorage
from remarkable.common.util import (
    arun_singleton_task,
    generate_timestamp,
    release_parse_file_lock,
    run_singleton_task,
)
from remarkable.config import get_config
from remarkable.db import peewee_transaction_wrapper, pw_db
from remarkable.file_flow.tasks import create_flow_task
from remarkable.file_flow.tasks.task import TaskStatus
from remarkable.file_flow.uploaded_file import UploadedFile
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.models.query_helper import AsyncPagination
from remarkable.plugins.fileapi import external_plugin, plugin
from remarkable.plugins.fileapi.common import (
    NoneOfWrapper,
    get_text_from_chars_with_white,
    get_text_in_box_with_ocr,
    is_valid_key_path_in_molds,
    predict_element,
)
from remarkable.plugins.fileapi.schema import TreeSchema
from remarkable.plugins.fileapi.upload_zip_file_handler import UploadZipFileBaseHandler
from remarkable.plugins.fileapi.worker import ChapterNode, PDFCache, create_pdf_cache, optimize_outline
from remarkable.pw_db_services import PeeweeService
from remarkable.pw_models.answer_data import DEFAULT_FILE_ANSWER_MERGE_STRATEGY
from remarkable.pw_models.law_judge import LawJudgeResult
from remarkable.pw_models.model import (
    NewAccuracyRecord,
    NewAuditStatus,
    NewFileProject,
    NewFileTree,
    NewHistory,
    NewMold,
    NewTag,
    NewTagRelation,
)
from remarkable.pw_models.question import NewQuestion
from remarkable.service.api_cleaner import post_pipe_after_api
from remarkable.service.new_file import NewFileService
from remarkable.service.new_file_project import NewFileProjectService
from remarkable.service.new_file_tree import NewFileTreeService, get_crumbs
from remarkable.service.new_question import NewQuestionService
from remarkable.worker.tasks import (
    inspect_rule_task,
    judge_file,
    preset_answer_by_fid,
    preset_answer_by_fid_task,
    process_extract_answer_by_studio,
    process_file,
    process_file_for_excel,
    re_extract_answer_by_studio,
)

default_task_type_with_scenario_args = {
    "default_scenario_id": fields.Int(load_default=None),
    "default_task_type": fields.String(load_default=None),
}

project_args = {
    "name": fields.String(required=True, validate=field_validate.Length(min=1)),
    "default_molds": fields.List(fields.Int(), load_default=[]),
    **default_task_type_with_scenario_args,
    "is_public": fields.Int(load_default=PublicStatus.PUBLIC.value),
    "visible": fields.Bool(load_default=True),
    "meta": fields.Dict(load_default=get_config("web.project_meta")),
}

tag_args = {
    "name": fields.String(required=True, validate=field_validate.Length(min=1)),
    "tag_type": fields.Integer(required=True, validate=field_validate.OneOf(TagType.member_values())),
}
logger = logging.getLogger(__name__)


@plugin.route(r"/project")
class ProjectListHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(project_args, location="json")
    async def post(self, name, default_molds, default_scenario_id, default_task_type, is_public, meta, visible):
        if (default_scenario_id and default_task_type is None) or (
            default_task_type == TaskType.JUDGE.value and default_scenario_id is None
        ):
            raise CustomError(_("Project defaults invalid"), resp_status_code=http.HTTPStatus.BAD_REQUEST)

        public = bool(is_public)

        exists = await NewFileProject.find_by_kwargs(name=name)
        if exists:
            raise CustomError(_("project name is existed"), resp_status_code=http.HTTPStatus.BAD_REQUEST)

        project = await NewFileProjectService.create(
            name,
            default_molds,
            uid=self.current_user.id,
            public=public,
            meta=meta,
            visible=visible,
            default_scenario_id=default_scenario_id,
            default_task_type=default_task_type,
        )

        await NewHistory.save_operation_history(
            project.id,
            self.current_user.id,
            HistoryAction.CREATE_PROJECT.value,
            self.current_user.name,
            meta=project.to_dict(),
        )

        self.data(project.to_dict())

    @Auth(["browse"])
    @use_kwargs(AsyncPagination.web_args, location="query")
    async def get(self, page, size):
        cond = NewFileProject.visible
        if not self.current_user.is_admin:
            cond &= (NewFileProject.uid == self.current_user.id) | NewFileProject.public
        query = (
            NewFileProject.select(
                NewFileProject,
                NewAdminUser.name.alias("user_name"),
            )
            .join(NewAdminUser, JOIN.LEFT_OUTER, on=(NewFileProject.uid == NewAdminUser.id))
            .where(cond)
            .order_by(NewFileProject.id.desc())
            .dicts()
        )
        data = await AsyncPagination(query, page=page, size=size).data()
        return self.data(data)


@plugin.route(r"/project/(\d+)")
class ProjectHandler(PermCheckHandler):
    put_schema = {
        "name": fields.String(validate=field_validate.Length(min=1)),
        "default_molds": fields.List(fields.Int()),
        **default_task_type_with_scenario_args,
        "permission": fields.String(validate=field_validate.OneOf(["public", "private"])),
        "meta": fields.Dict(),  # 中信托管部: product_type、product_name、product_num
    }

    @Auth(["browse"])
    async def get(self, pid):
        project = await NewFileProject.find_by_id(pid)
        if not project:
            return self.error(_("not found project"))
        await self.check_project_permission(pid, project=project)

        return self.data(project.to_dict())

    @Auth(["browse"])
    async def delete(self, pid):
        project = await NewFileProject.find_by_id(pid)
        if not project:
            raise CustomError(_("not found project"))
        await self.check_project_permission(pid, project=project, mode="write")

        async with pw_db.atomic():
            await NewHistory.save_operation_history(
                project.id,
                self.current_user.id,
                HistoryAction.DELETE_PROJECT.value,
                self.current_user.name,
                meta=project.to_dict(),
            )
            await project.soft_delete()

        if get_config("client.name") == "nafmii":
            await NewHistory.save_operation_history(
                None,
                self.current_user.id,
                HistoryAction.NAFMII_DEFAULT.value,
                self.current_user.name,
                meta=None,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.DELETE.value,
                    menu="识别文件管理",
                    subject="识别文件集",
                    content="删除识别文件集成功",
                ),
            )

        return self.data({})

    @Auth(["browse"])
    @use_args(put_schema, location="json")
    async def put(self, pid, params):
        project = await NewFileProject.find_by_id(pid)
        if not project:
            raise CustomError(_("not found project"))
        if (params["default_scenario_id"] and params["default_task_type"] is None) or (
            params["default_task_type"] == TaskType.JUDGE.value and params["default_scenario_id"] is None
        ):
            raise CustomError(_("Project defaults invalid"), resp_status_code=http.HTTPStatus.BAD_REQUEST)
        await self.check_project_permission(pid, project=project, mode="write")
        await NewFileProjectService.update(project, params, self.process_files)
        await NewHistory.save_operation_history(
            project.id,
            self.current_user.id,
            HistoryAction.MODIFY_PROJECT.value,
            self.current_user.name,
            meta=project.to_dict(),
        )
        return self.data(project.to_dict())

    @staticmethod
    async def process_files(files):
        for file in files:
            process_extract_answer_by_studio.delay(file.id, add_molds=file.molds)
            await process_file(file)


@plugin.route(r"/accuracy")
class AccuracyHandler(PermCheckHandler):
    args = {
        "type_": fields.String(data_key="type", load_default="1"),
        "test": fields.String(load_default="1"),
        "mold": fields.String(required=True),
    }

    @Auth("browse")
    @use_kwargs(args, location="query")
    async def get(self, type_, test, mold):
        query = (
            NewAccuracyRecord.select(NewAccuracyRecord.data)
            .where(
                NewAccuracyRecord.type == int(type_),
                NewAccuracyRecord.test == int(test),
                NewAccuracyRecord.mold == int(mold),
            )
            .order_by(NewAccuracyRecord.created_utc.desc())
        )
        data = await pw_db.scalar(query)
        return self.data(data if data else {})


@plugin.route(r"/tree/(\d+)")
class TreeHandler(PermCheckHandler):
    mold_param = {
        "name": fields.Str(validate=NoneOfWrapper([""])),  # 禁止空的项目名
        "ptree_id": fields.Int(),
        "default_molds": fields.List(fields.Int()),
        **default_task_type_with_scenario_args,
    }

    @Auth("browse")
    @use_kwargs(TreeSchema, location="query")
    async def get(self, tid: int, page: int, size: int, search_fid: int | None):
        tree = await NewFileTree.find_by_id(tid)
        if not tree:
            return self.error(_("not found tree"))
        await self.check_tree_permission(tid, tree=tree)
        res = tree.to_dict()
        trees = await NewFileTree.list_by_tree(int(tid))
        all_files_count = await pw_db.count(NewFile.select().where(NewFile.tree_id == tid, NewFile.deleted_utc == 0))

        async def gen_files():
            start = (page - 1) * size
            end = page * size
            res["trees"] = trees[start:end]
            need_file_count = size - len(res["trees"])
            if need_file_count:
                file_end = end - len(trees)
                file_offset = max(file_end - size + len(res["trees"]), 0)
                res["files"] = await NewFileTreeService.get_files_and_questions_by_tree(
                    tid, file_offset, need_file_count
                )
            else:
                res["files"] = []

        if search_fid:
            search_file_tree_id = await pw_db.scalar(NewFile.select(NewFile.tree_id).where(NewFile.id == search_fid))
            if search_file_tree_id != tree.id:
                search_fid = None
        while True:
            await gen_files()
            if search_fid is None:
                break
            if not res.get("files"):
                break
            if search_fid in [file["id"] for file in res["files"]]:
                break
            page += 1

        res["page"] = page
        res["total"] = all_files_count + len(trees)
        res["crumbs"] = await get_crumbs(tree.id)

        project = await NewFileProject.find_by_id(res["pid"])
        res["project_public"] = project.public

        return self.data(res)

    @Auth("browse")
    async def delete(self, tid):
        tree = await NewFileTree.find_by_id(tid)
        if not tree:
            return self.error(_("not found tree"))
        await self.check_tree_permission(tid, tree=tree, mode="write")

        async with PeeweeService.get_service(True) as service:
            await NewHistory.save_operation_history(
                tree.id,
                self.current_user.id,
                HistoryAction.DELETE_TREE.value,
                self.current_user.name,
                meta=tree.to_dict(),
            )

            await service.trees.delete_by_tree(tree)

        return self.data({})

    @Auth("browse")
    @use_args(mold_param, location="json")
    async def put(self, tid, form):
        tree = await NewFileTree.find_by_id(tid)
        if not tree:
            raise CustomError(_("not found tree"))
        if (form["default_scenario_id"] and form["default_task_type"] is None) or (
            form["default_task_type"] == TaskType.JUDGE.value and form["default_scenario_id"] is None
        ):
            raise CustomError(_("File tree defaults invalid"), resp_status_code=http.HTTPStatus.BAD_REQUEST)
        await self.check_tree_permission(tid, tree=tree, mode="write")

        tree = await NewFileTreeService.update(tree, form)

        await NewHistory.save_operation_history(
            tree.id,
            self.current_user.id,
            HistoryAction.MODIFY_TREE.value,
            self.current_user.name,
            meta=tree.to_dict(),
        )

        return self.data(tree.to_dict())


@plugin.route(r"/tree/(\d+)/name/(.*)")
class TreeNameHandler(BaseHandler):
    @Auth("browse")
    async def get(self, tid, name):
        exist = await NewFileTreeService.exist(tid, name)
        return self.data({"exists": exist})


@plugin.route(r"/tree/(\d+)/file")
class UploadFileHandler(PermCheckHandler):
    user_args = {
        "molds": fields.List(fields.Int(), load_default=[]),
        "name": fields.String(load_default=None),
        "num": fields.String(load_default=None),
        "task_type": fields.String(required=False, load_default=TaskType.EXTRACT.value),
        "scenario_id": fields.Int(load_default=None),
    }
    file_args = {
        "file_metas": fields.List(
            fields.Raw(), data_key="file", required=True, error_messages={"required": "not found upload document"}
        ),
        # 可以携带多个interdoc, 但是必须和file_metas一一对应
        # 对应文档直接使用interdoc的解析结果，不再向PDFinsight服务发起解析请求
        "interdocs": fields.List(fields.Raw(), data_key="interdoc", load_default=list),
    }

    args_schema = {
        "mold": fields.Int(load_default=None),
    }

    @Auth(["browse"])
    @use_kwargs(user_args, location="form")
    @use_kwargs(file_args, location="files")
    async def post(self, tid, file_metas, interdocs, molds, name, num, task_type, scenario_id):
        tree = await NewFileTree.find_by_id(tid)
        if not tree:
            raise CustomError(_("can't find the tree"))

        project = await NewFileProject.find_by_id(tree.pid)
        if not project:
            raise CustomError(_("can't find the project"))
        await self.check_tree_permission(tid, tree=tree, project=project)

        # if not molds:
        #     molds = await NewFileTree.find_default_molds(tid)
        if any(os.path.splitext(i["filename"])[-1].lower() not in SUPPORTED_SUFFIXES for i in file_metas):
            return self.error(_("Unsupported file type detected"))
        ret = []
        db_service = PeeweeService.create()
        enable_ocr = await db_service.molds.verify_enable_ocr(molds, get_config("web.force_ocr_mold_list", []))
        flow_task = await create_flow_task(get_config("client.name"), start_value=TaskStatus.initialized)

        for idx, file_meta in enumerate(file_metas):
            interdoc = interdocs[idx]["body"] if interdocs and idx < len(interdocs) else None
            async with pw_db.atomic():
                # fixme: 因为使用状态机, 链接和堆栈 out of control
                # (pg max_connections=1则超时; 或使用多个链接: SELECT * FROM pg_stat_activity where datname = 'config.get_config("db.dbname")';)
                newfile = await self.create_file_question(
                    file_meta, interdoc, molds, project, tree, name, num, task_type, scenario_id
                )
            ret.append(newfile.to_dict())
            if get_config("web.parse_pdf", True):
                await flow_task.parse_file(newfile, enable_orc=enable_ocr, db_service=db_service)
            else:
                # 不调pdfinsight解析服务,直接基于pdf文件生成缓存
                flow_task.current_state = TaskStatus.parse_success
                await flow_task.cache(newfile, force=True)

        return self.data(ret)

    async def create_file_question(
        self, file_meta, interdoc, molds, project, tree, name, num, task_type=None, scenario_id=None
    ):
        uploaded_file = UploadedFile(filename=file_meta["filename"], content=file_meta["body"])
        file_data = {"task_type": task_type, "molds": molds, "scenario_id": scenario_id}
        data = project.build_file_data(uploaded_file, tree.id, uid=self.current_user.id, data=file_data)
        flow_task = await create_flow_task(get_config("client.name"))
        allow_duplicated_name = get_config("web.allow_same_name_file_in_project", True)
        db_service = PeeweeService.create()
        newfile = await flow_task.create(
            data,
            uploaded_file,
            interdoc,
            using_pdfinsight_cache=True,
            allow_duplicated_name=allow_duplicated_name,
            db_service=db_service,
            question_name=name,
            question_num=num,
        )

        return newfile

    @Auth("browse")
    @use_kwargs(args_schema, location="query")
    @use_kwargs(AsyncPagination.web_args, location="query")
    async def get(self, tid, mold, page, size):
        tree_ids = await NewFileTree.find_all_sub_tree(int(tid), include_self=True)
        query = NewFileService.file_query(tree_ids, mold)
        res = await AsyncPagination(query.dicts(), page, size).data(
            dump_func=self.packer,
        )

        file_ids = [item["id"] for item in res["items"]]
        question_query = NewQuestionService.question_query_without_answer(file_ids)
        questions_by_fid = defaultdict(list)
        for question in await pw_db.execute(question_query.dicts()):
            questions_by_fid[question["fid"]].append(question)

        for item in res["items"]:
            item["questions"] = questions_by_fid[item["id"]]

        return self.data(res)

    @staticmethod
    def packer(row, fields):
        row["pid"] = row.pop("project")
        return row


@plugin.route(r"/tree/(\d+)/tree")
class CreateTreeHandler(PermCheckHandler):
    @Auth(["browse"])
    @use_kwargs(
        {name: project_args[name] for name in ("name", "default_molds", "default_scenario_id", "default_task_type")},
        location="json",
    )
    async def post(self, tid, name, default_molds, default_scenario_id, default_task_type):
        """创建目录"""
        if (default_scenario_id and default_task_type is None) or (
            default_task_type == TaskType.JUDGE.value and default_scenario_id is None
        ):
            raise CustomError(_("File tree defaults invalid"), resp_status_code=http.HTTPStatus.BAD_REQUEST)

        tree = await NewFileTree.find_by_id(tid)
        if not tree:
            raise CustomError(_("can't find the tree"))

        await self.check_tree_permission(tid, tree=tree)
        new_tree = await NewFileTreeService.create(
            tid=tid,
            uid=self.current_user.id,
            pid=tree.pid,
            name=name,
            default_molds=default_molds,
            default_scenario_id=default_scenario_id,
            default_task_type=default_task_type,
        )

        await NewHistory.save_operation_history(
            new_tree.id,
            self.current_user.id,
            HistoryAction.CREATE_TREE.value,
            self.current_user.name,
            meta=new_tree.to_dict(),
        )
        if config.get_config("client.name") == "nafmii":
            await NewHistory.save_operation_history(
                tree.id,
                self.current_user.id,
                HistoryAction.CREATE_TREE.value,
                self.current_user.name,
                meta=tree.to_dict(),
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.ADD.value,
                    menu=self.record_menu,
                    subject="文件夹",
                    content=f"新增文件夹{new_tree.id}成功",
                ),
            )

        return self.data(new_tree.to_dict())


@plugin.route(r"/trees/(\d+)/sse")
class UploadFileSSEHandler(UploadZipFileBaseHandler):
    @use_kwargs(
        {
            "task_type": fields.Str(load_default=TaskType.EXTRACT.value),
            "event_id": fields.Str(load_default=None),
            "scenario_id": fields.Int(load_default=None),
            "molds": fields.List(fields.Int(), load_default=[]),
        },
        location="form",
    )
    @use_kwargs({"file": fields.Raw(load_default=None)}, location="files")
    @Auth("browse")
    async def post(
        self,
        tid: str,
        task_type: str,
        event_id: str | None,
        file: HTTPFile | None,
        scenario_id: int | None,
        molds: list,
    ):
        tid = int(tid)
        tree = await NewFileTree.find_by_id(tid)
        if not tree:
            return self.error(_("not found tree"), status_code=http.HTTPStatus.NOT_FOUND)
        await self.upload_compressed_file(tid, task_type, event_id, file, scenario_id=scenario_id, molds=molds)


@plugin.route(r"/file/(\d+)")
class FileHandlerOrigin(PermCheckHandler):
    args = {
        "name": fields.String(required=True),
        "molds": fields.List(fields.Int(), required=True),
        "tags": fields.List(fields.Int(), load_default=list),
        "meta_info": fields.Dict(load_default=dict),
        "task_type": fields.String(load_default=None),
        "scenario_id": fields.Int(load_default=None),
    }

    @Auth("browse")
    async def get(self, fid):
        """文件下载"""
        await self.check_file_permission(fid)

        file: NewFile = await NewFile.find_by_id(fid)
        if not file:
            raise CustomError(_("not found file"))

        if file.task_type == TaskType.CLEAN_FILE.value and file.is_word:
            path = file.docx_path()
            filename = os.path.splitext(file.name)[0] + ".docx"
        else:
            path = file.path()
            filename = file.name
        try:
            data = localstorage.read_file(path, decrypt=bool(config.get_config("app.file_encrypt_key")))
        except FileNotFoundError:
            return self.error("文件不存在", status_code=http.HTTPStatus.NOT_FOUND)

        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.NAFMII_DEFAULT,
            user_name=self.current_user.name,
            meta=None,
            uid=self.current_user.id,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.EXPORT.value,
                menu=self.record_menu,
                subject="源文件",
                content="下载源文件成功",
            ),
        )
        return await self.export(data, filename)

    @use_kwargs(args, location="json")
    async def put(self, fid, task_type, name, molds, scenario_id, meta_info, tags):
        # 数据链路存在异步任务，不能用事务
        fid = int(fid)
        file = await NewFile.find_by_id(fid)
        if not file:
            raise CustomError(_("not found file"))
        if file.task_type == TaskType.CLEAN_FILE.value:
            raise CustomError(_("schema cannot be specified for clean documents"))
        await self.check_file_permission(fid, file=file, mode="write")

        if task_type == TaskType.JUDGE.value and not scenario_id:
            raise CustomError(_("大模型审核场景错误"))
        update_paras = {"scenario_id": scenario_id}
        if task_type and task_type != file.task_type:
            update_paras["task_type"] = task_type
        if meta_info:
            update_paras["meta_info"] = meta_info
        if name != file.name:
            if not get_config("web.allow_same_name_file_in_project", True):
                same_name_file = await NewFile.find_by_kwargs(name=name, pid=file.pid)
                if same_name_file:
                    raise CustomError(_("该项目下已存在同名的文件"))
            update_paras["name"] = name
        updated_info = file.updated_info(**update_paras)
        await file.update_(**update_paras)
        add_molds, delete_molds = await NewFileService.update_molds(file, molds)
        await NewTagRelation.update_tag_relation(tags, file, TagType.FILE)

        # molds 改变, 需要重新分析
        need_process_full = bool(add_molds or delete_molds)
        if not need_process_full and "task_type" in updated_info:
            before, after = updated_info["task_type"]
            if after not in (TaskType.EXTRACT.value, TaskType.AUDIT.value, TaskType.JUDGE.value):
                need_process_full = True
            elif before not in (TaskType.EXTRACT.value, TaskType.AUDIT.value, TaskType.JUDGE.value):
                need_process_full = True
            elif before == TaskType.JUDGE.value:
                # 之前仅有大模型审核的, 全部重跑 (增加跳过大模型审核不划算)
                need_process_full = True
            elif after == TaskType.JUDGE.value:
                # 之后仅剩大模型规则, reset
                await NewAuditStatus.reset(fid)
                questions = await pw_db.execute(
                    NewQuestion.select(NewQuestion.id, NewQuestion.mold, NewQuestion.llm_status).where(
                        NewQuestion.fid == fid
                    )
                )
                await NewQuestion.reset_predict_status(questions)
            elif before == TaskType.EXTRACT.value and after == TaskType.AUDIT.value:
                # 增加规则审核
                await NewAuditStatus.reset(fid)
                inspect_rule_task.delay(fid)
            elif before == TaskType.AUDIT.value and after == TaskType.EXTRACT.value:
                # 取消规则审核
                await NewAuditStatus.reset(fid)

        if need_process_full:
            # reset before process
            await NewAuditStatus.reset(fid)
            await LawJudgeResult.reset_judge_results(fid)
            questions = await pw_db.execute(
                NewQuestion.select(NewQuestion.id, NewQuestion.mold, NewQuestion.llm_status).where(
                    NewQuestion.fid == fid
                )
            )
            await NewQuestion.reset_predict_status(questions)
            if ClientName.cmfchina == config.get_config("client.name"):
                await process_file_for_excel(file)
            else:
                process_extract_answer_by_studio.delay(
                    file.id, list(add_molds), list(delete_molds), list(set(molds) - add_molds)
                )
                await process_file(file)
        elif "scenario_id" in updated_info:
            before, after = updated_info["scenario_id"]
            if after:
                await judge_file(file.id)  # 内部包含reset

        await NewHistory.save_operation_history(
            file.id,
            self.current_user.id,
            HistoryAction.MODIFY_FILE.value,
            self.current_user.name,
            meta=file.to_dict(),
        )
        if get_config("client.name") == "nafmii":
            name = await NewMold.get_name_by_id(molds[0])
            await NewHistory.save_operation_history(
                None,
                self.current_user.id,
                HistoryAction.NAFMII_DEFAULT.value,
                self.current_user.name,
                meta=None,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.MODIFY.value,
                    menu="识别文件管理",
                    subject="识别任务",
                    content=f"修改{fid}{name}成功",
                ),
            )
        return self.data({})

    async def delete(self, fid):
        _file = await NewFile.find_by_id(fid)
        if not _file:
            return self.error(_("not found file"))
        await self.check_file_permission(fid, file=_file, mode="write")

        async with pw_db.atomic():
            await NewHistory.save_operation_history(
                _file.id,
                self.current_user.id,
                HistoryAction.DELETE_FILE.value,
                self.current_user.name,
                meta=_file.to_dict(),
            )

            await _file.soft_delete()

        return self.data({})


class FileHandlerSchema(Schema):
    dirs = fields.List(fields.Int(), load_default=list)
    fids = fields.List(fields.Int(), load_default=list)


@plugin.route(r"/files/delete")
class FilesHandler(BaseHandler):
    @doc(summary="文件批量删除", description="删除所有给定文件id/目录id的文件", tag="file-management")
    @Auth("browse")
    @use_kwargs(FileHandlerSchema, location="json")
    async def post(self, dirs: list[int], fids: list[int]):
        async with pw_db.atomic():
            for did in dirs:
                if directory := await NewFileTree.get_by_id(did):
                    await NewHistory.save_operation_history(
                        did,
                        self.current_user.id,
                        HistoryAction.DELETE_TREE.value,
                        self.current_user.name,
                        meta=directory.to_dict(),
                    )
                    await directory.soft_delete()

            fids += await NewFileTree.get_fids(*dirs)
            for fid in set(fids):
                if file := await NewFile.find_by_id(fid):
                    await NewHistory.save_operation_history(
                        fid,
                        self.current_user.id,
                        HistoryAction.DELETE_FILE.value,
                        self.current_user.name,
                        meta=file.to_dict(),
                    )

                    await file.soft_delete()

        return self.data({"fids": fids})


class PredictFileHandlerSchema(FileHandlerSchema):
    merge_strategy = fields.Str(
        load_default=DEFAULT_FILE_ANSWER_MERGE_STRATEGY,
        validate=field_validate.OneOf(FileAnswerMergeStrategy.member_values()),
    )
    task = fields.Str(
        required=True,
        validate=field_validate.OneOf(FileTask.member_values()),
    )


@plugin.route(r"/files/execute")
class PredictFileHandler(BaseHandler):
    @doc(summary="文件批量预测/审核", tag="file-management")
    @Auth("browse")
    @use_kwargs(PredictFileHandlerSchema, location="json")
    async def post(self, task: str, dirs: list[int], fids: list[int], merge_strategy: str):
        if not (dirs or fids):
            return self.error(_("Invalid input parameters."), status_code=http.HTTPStatus.BAD_REQUEST)
        fids += await NewFileTree.get_fids(*dirs)
        lock_expired = get_config("web.run_lock_expired", 600)
        for fid in sorted(fids, reverse=True):
            get_lock, lock = await arun_singleton_task(self._do, task, fid, merge_strategy, lock_expired=lock_expired)
            if not get_lock:
                raise CustomError(
                    f"操作过于频繁,  请至少间隔{max(1, lock_expired // 60)}分钟",
                    resp_status_code=http.HTTPStatus.TOO_MANY_REQUESTS,
                )
        return self.data({})

    @staticmethod
    async def _do(task: str, fid: int, merge_strategy: str):
        await pw_db.execute(NewFile.update(updated_utc=generate_timestamp()).where(NewFile.id == fid))
        if task == FileTask.JUDGE:
            await judge_file(fid)
            return

        if task == FileTask.AUDIT or task == FileTask.INSPECT:
            await NewAuditStatus.reset(fid)
            inspect_rule_task.delay(fid)
            return

        if task == FileTask.PREDICT:
            await NewAuditStatus.reset(fid)
            await LawJudgeResult.reset_judge_results(fid)
            questions = await pw_db.execute(
                NewQuestion.select(NewQuestion.id, NewQuestion.mold, NewQuestion.llm_status).where(
                    NewQuestion.fid == fid
                )
            )
            await NewQuestion.reset_predict_status(questions)
            file = await NewFile.find_by_id(fid)
            re_extract_answer_by_studio.delay(file.id, file.molds)
            preset_answer_by_fid_task.delay(fid, force_predict=True, file_answer_merge_strategy=merge_strategy)
            return

        if task == FileTask.PARSE:
            await NewAuditStatus.reset(fid)
            await LawJudgeResult.reset_judge_results(fid)
            questions = await pw_db.execute(
                NewQuestion.select(NewQuestion.id, NewQuestion.mold, NewQuestion.llm_status).where(
                    NewQuestion.fid == fid
                )
            )
            await NewQuestion.reset_predict_status(questions)
            file = await NewFile.get_by_id(fid)
            await pw_db.update(file, pdf_parse_status=PDFParseStatus.PENDING)
            if ClientName.cmfchina == config.get_config("client.name"):
                await process_file_for_excel(file, force_predict=True)
            else:
                await process_file(file, force_predict=True)


@plugin.route(r"/files/(\d+)")
class FileHandler(PermCheckHandler):
    @Auth("browse")
    async def get(self, fid):
        await self.check_file_permission(fid)
        file = await NewFile.find_by_id(fid)
        if not file:
            raise CustomError(_("not found file"))

        data = file.to_dict()
        tree = await NewFileTree.find_by_id(file.tree_id)
        data["crumbs"] = await get_crumbs(tree.id)

        return self.data(data)


@plugin.route(r"/file/(\d+)/pdf")
class PdfFileHandler(PermCheckHandler):
    @Auth("browse")
    async def head(self, fid):
        return await self._do(fid)

    @Auth("browse")
    async def get(self, fid):
        return await self._do(fid)

    async def _do(self, fid):
        fid = int(fid)
        file = await NewFile.find_by_id(fid)
        if not file:
            raise CustomError(_("not found file"), resp_status_code=http.HTTPStatus.NOT_FOUND)
        await self.check_file_permission(fid, file=file)

        if not file.pdf:
            raise CustomError(_("the pdf file is not ready"), resp_status_code=http.HTTPStatus.BAD_REQUEST)

        if self.is_first_fetch_file():
            await NewHistory.save_operation_history(
                file.id,
                self.current_user.id,
                HistoryAction.OPEN_PDF.value,
                self.current_user.name,
                meta=None,
            )
        # data = localstorage.read_file(_file.raw_pdf_path() or _file.pdf_path(), auto_detect=True)
        # TODO: Do we need decrypt here?
        path = localstorage.mount(file.raw_pdf_path() or file.pdf_path())
        if not os.path.exists(path):
            return self.error("文件不存在", status_code=http.HTTPStatus.NOT_FOUND)
        return await self.export(path, os.path.splitext(file.name)[0] + ".pdf")


@plugin.route(r"/file/(\d+)/docx")
class DocxFileHandler(PermCheckHandler):
    @Auth("browse")
    async def get(self, fid):
        file = await NewFile.find_by_id(fid)
        if not file:
            raise CustomError(_("not found file"))
        if file.task_type != TaskType.PDF2WORD.value:
            raise CustomError(_("not found file"))
        await self.check_file_permission(fid, file=file)

        if not file.docx:
            raise CustomError(_("the docx file is not ready"))

        data = localstorage.read_file(file.docx_path(), auto_detect=True)
        return await self.export(data, os.path.splitext(file.name)[0] + ".docx")


# TODO 过渡方案,jpg格式不依赖缓存;待前端完全去掉对这块数据的依赖后去除
@plugin.route(r"/files/(\d+)/pages/(\d+)/image/(\d+).jpg")
class JpgImageHandler(PermCheckHandler):
    @Auth("browse")
    async def get(self, fid, page, width):
        file = await NewFile.find_by_id(fid)
        if not file:
            raise CustomError(_("not found file"))
        await self.check_file_permission(fid, file=file)

        if not file.pdf:
            raise CustomError(_("the pdf file is not ready"))

        pdf_path = localstorage.mount(file.pdf_path())
        params = {"format": "jpg", "scale_to_x": int(width)}
        image = PDFiumUtil.get_page_bitmap(pdf_path, int(page), **params)
        image = image.convert("RGB")
        b_image = io.BytesIO()
        image.save(b_image, format="JPEG")

        return await self.export(b_image.getvalue(), content_type="image/jpeg")


@plugin.route(r"/file/(\d+)/pageinfo")
class PdfPageInfoHandler(PermCheckHandler):
    @Auth("browse")
    async def get(self, fid):
        file = await NewFile.find_by_id(fid)
        if not file:
            raise CustomError(_("not found file"))
        await self.check_file_permission(fid, file=file)

        if not file.pdf:
            raise CustomError(_("Page-info data only for file.pdf"))

        pdf_cache = PDFCache(file)
        page_info_path = pdf_cache.page_info_path
        if not localstorage.exists(page_info_path):
            logger.warning(f"page_info_path: {page_info_path} not found, rebuilding...")
            await create_pdf_cache(file, force=True)
            logger.info(f"page_info_path: {page_info_path} rebuilt")
        return self.data(pdf_cache.get_page_info())


@plugin.route(r"/file/(\d+)/chapter-info")
class PdfChapterInfoHandler(PermCheckHandler):
    @Auth("browse")
    async def get(self, fid):
        file = await NewFile.find_by_id(fid)
        if not file:
            raise CustomError(_("not found file"))

        await self.check_file_permission(fid, file=file)

        await NewHistory.save_operation_history(
            file.id,
            self.current_user.id,
            HistoryAction.OPEN_PDF.value,
            self.current_user.name,
            meta=None,
        )

        if not file.pdf:
            raise CustomError(_("Chapter-info data only for file.pdf"))

        pdf_cache = PDFCache(file)
        info_path = pdf_cache.chapter_info_path
        if not localstorage.exists(info_path):
            logger.warning(f"chapter_info_path: {info_path} not found, rebuilding...")
            await create_pdf_cache(file, force=True)
            logger.info(f"chapter_info_path: {info_path} rebuilt")
        root_node: ChapterNode = pdf_cache.get_chapter_info()[-1]

        await post_pipe_after_api(file.id, None, HistoryAction.OPEN_PDF.value)

        return self.data(root_node.to_dict())


@plugin.route(r"/files/(\d+)/pages/(\d+)/y1/(\d+(?:\.\d+)?)")
class PDFChapterInfoHandler(PermCheckHandler):
    @Auth("browse")
    async def get(self, fid, page, y1):
        fid, page, y1 = int(fid), int(page), float(y1)
        file = await NewFile.find_by_id(fid)
        if not file:
            raise CustomError(_("not found file"))

        await self.check_file_permission(fid, file=file)
        return self.data(PDFCache(file).find_closest_chapter(page, y1).to_dict())


@plugin.route(r"/file/(\d+)/search")
class PdfFileSearchHandler(PermCheckHandler):
    keyword_schema = {"keyword": fields.Str(required=True)}

    @Auth("browse")
    @use_kwargs(keyword_schema, location="query")
    async def get(self, fid, keyword):
        file = await NewFile.find_by_id(fid)
        if not file:
            raise CustomError(_("not found file"))
        await self.check_file_permission(fid, file=file)
        pdf_cache = PDFCache(file)
        search_string_path = pdf_cache.search_string_path
        if not localstorage.exists(search_string_path):
            logger.warning(f"search_string_path: {search_string_path} not found, rebuilding...")
            await create_pdf_cache(file, force=True)
            logger.info(f"search_string_path: {search_string_path} rebuilt")
        find_res = pdf_cache.search(keyword)
        return self.data({"keyword": keyword, "results": find_res})


@plugin.route(r"/(?:project|file|tree)s/(\d+)/run")
class RunTaskHandler(BaseHandler):
    task_schema = {
        "task": fields.Str(required=True, validate=field_validate.OneOf(["preset", "inspect", "pdfinsight"])),
        "sync": fields.Bool(load_default=False),
    }

    @Auth("browse")
    @use_kwargs(task_schema, location="query")
    async def get(self, *args, **kwargs):
        """重跑:预测/合规/解析 任务"""
        fid = int(args[0])
        lock_key = f"rerun_task:{fid}"
        lock_expired = get_config("web.run_lock_expired", 600)
        get_lock, _ = run_singleton_task(lambda: None, lock_key=lock_key, lock_expired=lock_expired)
        if not get_lock:
            raise CustomError(f"操作过于频繁, 请至少间隔{max(1, lock_expired // 60)}分钟")

        if self.request.path.split(f"/{plugin.name}", maxsplit=1)[-1].startswith("/projects/"):
            cond = NewFile.pid == fid
        elif self.request.path.split(f"/{plugin.name}", maxsplit=1)[-1].startswith("/trees/"):
            cond = NewFile.tree_id == fid
        else:
            cond = NewFile.id == fid
        try:
            for file in await pw_db.execute(NewFile.select().where(cond)):
                if kwargs["task"] == "preset":
                    if kwargs["sync"]:
                        await preset_answer_by_fid(file.id, force_predict=True)
                    else:
                        preset_answer_by_fid_task.delay(file.id, force_predict=True)
                elif kwargs["task"] == "inspect":
                    # if kwargs["sync"]:
                    #     await do_inspect_rule_pipe(file.id)
                    # else:
                    # TODO: replace `gino` with `peewee`
                    inspect_rule_task.delay(file.id)
                elif kwargs["task"] == "pdfinsight":
                    release_parse_file_lock(file.hash)
                    await process_file(file, force_parse_file=True)
        except Exception as exp:
            logger.exception(exp)
            return self.error(_("rerun task failed"))

        if kwargs["sync"]:
            return self.data({})
        return self.data("task queued!")


@external_plugin.route(r"/file/(\d+)/pdfinsight")
@plugin.route(r"/file/(\d+)/pdfinsight")
class PdfinsightCallbackHandler(PermCheckHandler):
    @Auth("browse")
    async def get(self, fid):
        file = await NewFile.find_by_id(fid)
        if not file:
            raise CustomError(_("not found file"))

        if not file.pdfinsight:
            raise CustomError(_("the pdfinsight file is not ready"))
        return await self.export(localstorage.mount(file.pdfinsight_path()), f"{file.name}.zip")


@plugin.route(r"/tag")
class TagsHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(AsyncPagination.web_args, location="query")
    @use_kwargs(
        {"tag_type": fields.Integer(load_default=None, validate=field_validate.OneOf(TagType.member_values()))},
        location="query",
    )
    async def get(self, page, size, tag_type):
        cond = speedy.peewee_plus.orm.TRUE
        if tag_type:
            cond &= NewTag.tag_type == tag_type
        query = NewTag.select().where(cond)
        data = await AsyncPagination(query, page=page, size=size).data()

        return self.data(data)

    @Auth("manage_prj")
    @use_kwargs(tag_args, location="json")
    @peewee_transaction_wrapper
    async def post(self, name, tag_type):
        exists = await NewTag.find_by_kwargs(name=name, tag_type=tag_type)
        if exists:
            return self.error(_("tag already exists"))

        tag = await NewTag.create(name=name, tag_type=tag_type)
        await NewHistory.save_operation_history(
            tag.id,
            self.current_user.id,
            HistoryAction.CREATE_TAG.value,
            self.current_user.name,
            meta=tag.to_dict(),
        )
        return self.data(tag.to_dict())


@plugin.route(r"/tag/(\d+)")
class TagHandler(BaseHandler):
    @Auth("manage_prj")
    @use_kwargs(tag_args, location="json")
    @peewee_transaction_wrapper
    async def put(self, tid, name, tag_type):
        tag = await NewTag.find_by_id(tid)
        if not tag:
            raise CustomError(_("not found tag"))

        if name != tag.name:
            if await NewTag.find_by_kwargs(name=name, tag_type=tag_type):
                return self.error(_("tag already exists"))

        await tag.update_(name=name, tag_type=tag_type)

        await NewHistory.save_operation_history(
            tag.id,
            self.current_user.id,
            HistoryAction.MODIFY_TAG.value,
            self.current_user.name,
            meta=tag.to_dict(),
        )

        return self.data(tag.to_dict())

    @Auth("manage_prj")
    @peewee_transaction_wrapper
    async def delete(self, tid):
        tag = await NewTag.find_by_id(tid)
        if not tag:
            raise CustomError(_("not found tag"))
        tag_relations = await NewTagRelation.find_by_kwargs("all", tag_id=tag.id)
        if tag_relations:
            raise CustomError(
                f"{tag.name} " + _("is in use, cannot be deleted") + f" ids:{[x.id for x in tag_relations[:10]]}"
            )
        await tag.delete_()

        await NewHistory.save_operation_history(
            tag.id,
            self.current_user.id,
            HistoryAction.DELETE_TAG.value,
            self.current_user.name,
            meta=tag.to_dict(),
        )

        return self.data({})


@plugin.route(r"/files/(\d+)/outlines")
class GetOutlinesHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(
        {
            "page": fields.Int(load_default=None),
            "force": fields.Bool(load_default=False),
        },
        location="query",
    )
    async def get(self, fid, page, force):
        file = await NewFile.find_by_id(int(fid))
        if not file:
            return self.error(_("File not found"), status_code=http.HTTPStatus.NOT_FOUND)
        outlines = NewFileService.get_or_create_outlines(file, force=force)
        if page is None:
            return self.data(outlines)
        return self.data(outlines.get(str(page), []))


@plugin.route(r"/file/(\d+)/text_in_box")
class PDFTocTextInBoxHandler(PermCheckHandler):
    async def get_text_in_box(self, file, box, with_box):
        get_text = PDFUtil.get_text_from_chars_with_white
        if with_box == "true":
            get_text = get_text_from_chars_with_white

        pdf_cache = PDFCache(file)
        char_idx_range_path = pdf_cache.char_idx_range_path
        if not localstorage.exists(char_idx_range_path):
            logger.warning(f"char_idx_range_path: {char_idx_range_path} not found, rebuilding...")
            await create_pdf_cache(file, force=True)
            logger.info(f"char_idx_range_path: {char_idx_range_path} rebuilt")
        text, chars = await self.run_in_executor(pdf_cache.get_text_in_box, box, get_text)

        if not text and (config.get_config("client.ocr.enable")):
            try:
                text, chars = await get_text_in_box_with_ocr(box, file, get_text)
            except CustomError:
                return False, _(
                    "The OCR service access has expired, frame annotation failed, please contact the administrator."
                )

        if text:
            text = text[:-1] if text.endswith("\n") else text
            box["box"] = optimize_outline(chars)
        return True, {"box": box, "text": text if text else ""}

    @Auth("browse")
    async def post(self, fid):
        fid = int(fid)
        _file = await NewFile.find_by_id(fid)
        if not _file:
            raise CustomError(_("not found file"))
        await self.check_file_permission(fid, file=_file)
        with_box = self.get_query_argument("with_box", "false")
        req_data = self.get_json_body()
        results = []
        for box in req_data:
            ret, data = await self.get_text_in_box(_file, box, with_box)
            if not ret:
                return self.error(data)

            results.append(data)
        return self.data(results)


@plugin.route(r"/project/(?P<project_id>\d+)/file")
class ProjectFilesHandler(PermCheckHandler):
    args = {
        "mold_id": fields.Int(load_default=None),
        "answered": fields.Bool(load_default=False),
        "status": fields.Int(load_default=None),
        "fileid": fields.Str(load_default=""),
        "filename": fields.Str(load_default=""),
        "username": fields.Str(load_default=""),
    }

    @Auth(["browse"])
    @use_kwargs(AsyncPagination.web_args, location="query")
    @use_kwargs(args, location="query")
    async def get(self, project_id, mold_id, answered, status, fileid, filename, username, page, size):
        await self.check_project_permission(project_id)

        user = self.current_user
        if len([x for x in (filename, fileid, username) if x]) > 1:
            raise CustomError(_("The input search criteria is invalid"))

        if filename:
            filename = filename.replace("=", "==").replace("%", "=%").replace("_", "=_")
        if username:
            user = await NewAdminUser.find_by_kwargs(name=username)
            if not user:
                return self.data({"page": 1, "size": 20, "total": 0, "items": []})
            answered = True

        query = NewFileService.file_query(
            pid=project_id if project_id != -1 else None,
            mold=mold_id,
            uid=user.id,
            filename=filename,
            fileid=fileid,
            is_answered=answered,
            question_status=status,
        )
        res = await AsyncPagination(query.dicts(), page, size).data(
            dump_func=self.packer,
        )

        file_ids = [item["id"] for item in res["items"]]
        question_query = NewQuestionService.question_query_without_answer(
            file_ids=file_ids,
            uid=user.id,
            is_answered=answered,
            status=status,
        )
        questions_by_fid = defaultdict(list)
        for question in await pw_db.execute(question_query.dicts()):
            questions_by_fid[question["fid"]].append(question)

        for item in res["items"]:
            item["questions"] = questions_by_fid[item["id"]]

        return self.data(res)

    @staticmethod
    def packer(row, fields):
        row["pid"] = row.pop("project")
        return row


@plugin.route(r"/project/(\d+)/summary")
class SummaryHandler(PermCheckHandler):
    args = {
        "tree_id": fields.Int(required=True),
    }

    @Auth("browse")
    @use_kwargs(args, location="query")
    async def get(self, prj_id: str, tree_id: int):
        """
        查询汇总统计数字:
        当前项目or目录总文档数, 总页数, 标注完成数, 未标注完成数, 预测中文档数, 预测完成文档数
        每个用户的标注数量, 登录访问次数
        """

        tree_ids = await NewFileTreeService.get_related_tree_ids(tree_id)
        count_obj = await NewFileTreeService.get_ai_status_summary(prj_id, tree_ids)
        mark_summary = await NewQuestionService.get_mark_summary(prj_id, tree_ids, None)
        return self.data(
            {
                "total_file": count_obj.total_file,
                "total_question": count_obj.total_question,
                "total_page": count_obj.total_page if count_obj.total_page else 0,
                "finished": count_obj.finished,
                "conflicted": count_obj.conflicted,
                "marked": count_obj.marked,
                "predicting": count_obj.predicting,
                "predicted": count_obj.predicted,
                "users": mark_summary,
            }
        )


@plugin.route(r"/question/(?P<qid>\d+)/prompt/(?P<key>.+)")
class PromptHandler(PermCheckHandler):
    args_schema = {
        "group_by": fields.Str(data_key="groupby", load_default="item"),
        "has_accurate_answer": fields.Boolean(load_default=False),
        "related_molds": fields.Boolean(load_default=False),
    }

    @Auth("browse")
    @use_kwargs(args_schema, location="query")
    async def get(self, qid, key, group_by, has_accurate_answer, related_molds):
        key_path = key.split("|")
        question = await NewQuestion.find_by_id(qid)
        if related_molds:
            molds = await NewMold.get_related_molds(question.mold)
        else:
            mold = await NewMold.find_by_id(question.mold)
            molds = [mold]

        is_valid, mold = is_valid_key_path_in_molds(key_path, molds)
        if not is_valid:
            raise CustomError(_("key error (%s)" % key_path))
        if question.mold != mold.id:
            question = await NewQuestion.find_by_fid_mid(question.fid, mold.id)
        aid = attribute_id(key_path)
        data = predict_element(question.crude_answer, aid, group_by, has_accurate_answer=has_accurate_answer)
        return self.data(data)


@plugin.route(r"/file/search")
class PageSearchHandler(DbQueryHandler):
    args = {
        "filename": fields.String(load_default=""),
        "fileid": fields.Int(load_default=0),
        "username": fields.String(load_default=""),
        "project_id": fields.Int(load_default=0),
    }

    @Auth("browse")
    @use_kwargs(args, location="query")
    @use_kwargs(AsyncPagination.web_args, location="query")
    async def get(self, filename, fileid, username, project_id, page, size):
        answered = False
        user = self.current_user

        if not len([x for x in (filename, fileid, username) if x]) == 1:
            raise CustomError(_("The input search criteria is invalid"))

        if filename:
            filename = filename.replace("=", "==").replace("%", "=%").replace("_", "=_")
        if username:
            user = await NewAdminUser.find_by_kwargs(name=username)
            if not user:
                return self.data({"page": 1, "size": 20, "total": 0, "items": []})
            answered = True

        is_manager = self.current_user.is_admin

        query = NewFileService.file_query(
            pid=project_id,
            uid=user.id,
            filename=filename,
            fileid=fileid,
            is_answered=answered,
            is_manager=is_manager,
        )
        res = await AsyncPagination(query.dicts(), page, size).data(
            dump_func=self.packer,
        )
        file_ids = [item["id"] for item in res["items"]]
        question_query = NewQuestionService.question_query_without_answer(
            file_ids=file_ids,
            uid=user.id,
            is_answered=answered,
        )
        questions_by_fid = defaultdict(list)
        for question in await pw_db.execute(question_query.dicts()):
            questions_by_fid[question["fid"]].append(question)

        for item in res["items"]:
            item["questions"] = questions_by_fid[item["id"]]
        return self.data(res)

    @staticmethod
    def packer(row, fields):
        row["pid"] = row.pop("project")
        return row


@plugin.route(r"/tree/default")
class DefaultTreeHandler(BaseHandler):
    args = {
        "name": fields.Str(required=False, load_default="default"),
        "visible": fields.Bool(required=False, load_default=True),
    }

    @Auth("browse")
    @use_kwargs(args, location="query")
    async def get(self, name, visible):
        file_tree = await NewFileTree.find_by_kwargs(name=name)
        file_project = await NewFileProject.find_by_kwargs(name=name)
        if not (file_tree and file_project):
            default_mold_id = None
            config_map = list((get_config("prophet.config_map") or {}).keys())
            if config_map:
                default_mold_name = config_map[0]
                default_mold = await NewMold.find_by_name(name=default_mold_name)
                if not default_mold:
                    return self.error("No matched schema found, please check your config")
                default_mold_id = default_mold.id
                if name == get_config("customer_settings.default_tree_name"):
                    default_mold_id = None
            default_molds = [default_mold_id] if default_mold_id else []
            file_project = await NewFileProjectService.create(name=name, default_molds=default_molds, visible=visible)

        return self.data(
            {
                "file_tree_id": file_project.rtree_id,
                "file_project": file_project.id,
            }
        )


@plugin.route(r"/files/(?P<fid>\d+)/audit-status")
class QueryAuditStatusHandler(BaseHandler):
    @Auth("browse")
    async def get(self, fid):
        status = await NewAuditStatus.find_latest_status(int(fid))
        if status:
            return self.data(status.to_dict())
        return self.data({})
