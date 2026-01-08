import io
import logging
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

import speedy.peewee_plus.orm
import tornado
from marshmallow import fields

from remarkable.base_handler import Auth, DbQueryHandler
from remarkable.common import field_validate
from remarkable.common.apispec_decorators import doc, use_kwargs
from remarkable.common.constants import AIStatus, HistoryAction, PDFParseStatus, TagType, TokenStatus
from remarkable.common.exceptions import CustomError
from remarkable.common.storage import localstorage
from remarkable.config import get_config
from remarkable.db import db, peewee_transaction_wrapper, pw_db
from remarkable.models.ccxi import CCXIFileProject, CCXIFileTree
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import ADMIN, NewAdminUser
from remarkable.models.query_helper import AsyncPagination
from remarkable.plugins import Plugin
from remarkable.pw_models.model import (
    NewCCXIContract,
    NewFileProject,
    NewFileTree,
    NewHistory,
    NewMold,
    NewSpecialAnswer,
    NewTag,
    NewTagRelation,
    NewTimeRecord,
)
from remarkable.pw_models.question import NewQuestion
from remarkable.service.new_file import NewFileService
from remarkable.service.new_file_project import NewFileProjectService
from remarkable.service.new_file_tree import NewFileTreeService
from remarkable.service.new_mold import NewMoldService
from remarkable.worker.tasks import process_file

plugin = Plugin(Path(__file__).parent.name)


project_args = {
    "prj_num": fields.String(required=True, validate=field_validate.Length(min=1, max=128)),
    "prj_type": fields.String(
        required=True, validate=field_validate.OneOf(["信贷ABS", "ABN", "企业ABS", "非标", "底层资产"])
    ),
    "name": fields.String(required=True, validate=field_validate.Length(min=1, max=128)),
    "uid": fields.Int(required=True),
    "participants": fields.List(fields.Int(), load_default=[]),
}

file_tree_args = {
    "name": fields.String(required=True, validate=field_validate.Length(min=1, max=128)),
    "version": fields.String(required=True, validate=field_validate.Length(min=1, max=128)),
    "uid": fields.Int(required=True),
}

file_tag_args = {
    "name": fields.String(required=True, validate=field_validate.Length(min=1)),
    "molds": fields.List(fields.Int(), required=True, validate=field_validate.Length(min=1)),
}

supported_exts = [".doc", ".docx", ".pdf"]


class CCXIHandler(DbQueryHandler):
    async def check_project_permission(self, uid, prj_num, project=None):
        user = await NewAdminUser.find_by_id(uid)
        if not user:
            raise CustomError(_("您没有操作该项目的权限"), errors="0001")
        if not project:
            project = await NewFileProject.find_by_kwargs(name=prj_num)
            if not project:
                raise CustomError(_("Item Not Found"), errors="0002")
        if project.meta:
            participants = project.meta.get("participants", [])
            if user.ext_id in [str(x) for x in participants]:
                return True

        raise CustomError(_("您没有操作该项目的权限"), errors="0001")

    def write_error(self, status_code, **kwargs):
        exc = kwargs.get("exc_info")[1]
        logging.exception(exc)
        if isinstance(exc, CustomError):
            self.error(exc.msg, status_code=exc.resp_status_code, errors=exc.errors)
        elif status_code == 422 and "exc_info" in kwargs:
            if hasattr(exc, "messages"):
                if getattr(exc, "headers", None):
                    for name, val in exc.headers.items():
                        self.set_header(name, val)
                if isinstance(exc.log_message, dict):
                    self.error(message=str(exc.log_message), errors="0010")
                else:
                    self.error(message=_(exc.log_message), errors="0010")
        elif isinstance(exc, tornado.web.HTTPError):
            self.error(exc.reason, status_code=exc.status_code)
        else:
            self.error(str(exc), status_code=status_code)

    def error(self, message, status_code=200, errors=None, binary=None):
        self.set_status(status_code)
        if message == TokenStatus.EXPIRED:
            errors = "0007"
        elif message == TokenStatus.INVALID:
            errors = "0008"

        self.send_json({"status": "error", "message": message, "code": errors}, binary=binary)


@plugin.route(r"/project")
class CCXIProjectListHandler(CCXIHandler):
    @Auth("browse")
    @doc(tags=["ccxi"])
    @use_kwargs(project_args, location="json")
    @peewee_transaction_wrapper
    async def post(self, prj_num, **kwargs):
        exists = await NewFileProject.find_by_kwargs(name=prj_num)  # prj_num 存在project.name
        if exists:
            return self.error(message="项目编号已存在", errors="0004")

        project = await NewFileProjectService.create(prj_num, meta=kwargs)
        ccxi_project = CCXIFileProject(project)
        return self.data(ccxi_project.to_dict())


@plugin.route(r"/project/(?P<prj_num>\w*)")
class CCXIProjectHandler(CCXIHandler):
    @Auth("browse")
    @doc(tags=["ccxi"])
    @use_kwargs({"name": project_args["name"], "participants": project_args["participants"]}, location="json")
    async def put(self, prj_num, name, participants):
        project = await NewFileProject.find_by_kwargs(name=prj_num)
        if not project:
            return self.error(message="找不到该项目", errors="0002")
        params = {"name": name}
        if participants:
            params["participants"] = participants
        project.meta.update(params)
        async with pw_db.atomic():
            await project.update_(meta=project.meta)
            project_tree = await NewFileTree.find_by_id(project.rtree_id)
            await project_tree.update_(meta=project.meta)
            ccxi_project = CCXIFileProject(project)
            return self.data(ccxi_project.to_dict())

    @Auth("browse")
    @doc(tags=["ccxi"])
    @peewee_transaction_wrapper
    async def delete(self, prj_num):
        project = await NewFileProject.find_by_kwargs(name=prj_num)
        if not project:
            return self.error(message="找不到该项目", errors="0002")
        await project.delete_()
        return self.data({})


@plugin.route(r"/project/(?P<prj_num>\w*)/tree")
class CCXIFileTreeListHandler(CCXIHandler):
    @Auth("browse")
    @doc(tags=["ccxi"])
    @use_kwargs(file_tree_args, location="json")
    @peewee_transaction_wrapper
    async def post(self, prj_num, version, **kwargs):
        project = await NewFileProject.find_by_kwargs(name=prj_num)
        if not project:
            return self.error(message="找不到该项目", errors="0002")

        exists = await NewFileTreeService.exist(project.rtree_id, version)
        if exists:
            return self.error(message="该项目下该版本号已存在", errors="0005")

        kwargs.update({"prj_num": prj_num})
        file_tree = await NewFileTree.create(
            **{
                "ptree_id": project.rtree_id,
                "pid": project.id,
                "name": version,  # version存在file_tree.name
                "meta": kwargs,
                "uid": ADMIN.id,
            }
        )
        ccxi_file_tree = CCXIFileTree(file_tree)
        return self.data(ccxi_file_tree.to_dict())


@plugin.route(r"/project/(?P<prj_num>\w*)/tree/(?P<version>\w*)")
class CCXIFileTreeHandler(CCXIHandler):
    @Auth("browse")
    @doc(tags=["ccxi"])
    async def get(self, prj_num, version):
        project = await NewFileProject.find_by_kwargs(name=prj_num)
        if not project:
            return self.error(message="找不到该项目", errors="0002")

        file_tree = await NewFileTree.find_by_kwargs(pid=project.id, name=version)
        if not file_tree:
            return self.error(message="找不到该版本", errors="0003")

        await self.check_project_permission(self.current_user.id, project.id, project=project)

        data = {"pid": project.id, "tree_id": file_tree.id}
        return self.data(data)

    @Auth("browse")
    @doc(tags=["ccxi"])
    @use_kwargs({"name": file_tree_args["name"]}, location="json")
    @peewee_transaction_wrapper
    async def put(self, prj_num, version, name):
        project = await NewFileProject.find_by_kwargs(name=prj_num)
        if not project:
            return self.error(message="找不到该项目", errors="0002")

        file_tree = await NewFileTree.find_by_kwargs(pid=project.id, name=version)
        if not file_tree:
            return self.error(message="找不到该版本", errors="0003")

        file_tree.meta.update({"name": name})
        await file_tree.update_(meta=file_tree.meta)

        ccxi_file_tree = CCXIFileTree(file_tree)
        return self.data(ccxi_file_tree.to_dict())

    @Auth("browse")
    @doc(tags=["ccxi"])
    @peewee_transaction_wrapper
    async def delete(self, prj_num, version):
        project = await NewFileProject.find_by_kwargs(name=prj_num)
        if not project:
            return self.error(message="找不到该项目", errors="0002")

        file_tree = await NewFileTree.find_by_kwargs(pid=project.id, name=version)
        if not file_tree:
            return self.error(message="找不到该版本", errors="0003")
        await file_tree.delete_()
        return self.data({})


@plugin.route(r"/tree/(?P<tree_id>\w*)/file")
class CCXIFileHandler(CCXIHandler):
    file_args = {
        "file_metas": fields.List(
            fields.Raw(), data_key="file", required=True, error_messages={"required": "not found upload document"}
        ),
    }
    form_args = {
        "tag": fields.Int(required=True),
    }

    @Auth("browse")
    @doc(tags=["ccxi"])
    @use_kwargs(form_args, location="form")
    @use_kwargs(file_args, location="files")
    async def post(self, tree_id, file_metas, tag):
        if not await NewTag.all_ids_exists([tag]):
            raise CustomError(_("Not all ids valid."))

        tree = await NewFileTree.find_by_id(tree_id)
        if not tree:
            raise CustomError(_("can't find the tree"))
        project = await NewFileProject.find_by_id(tree.pid)
        if not project:
            raise CustomError(_("can't find the project"))
        await self.check_project_permission(self.current_user.id, project.id, project=project)

        ret = []
        for file_meta in file_metas:
            if os.path.splitext(file_meta["filename"])[-1].lower() not in supported_exts:
                return self.error(_("Unsupported file type detected"))
            file = await NewFileService.create_file(
                file_meta["filename"],
                file_meta["body"],
                [],
                project.id,
                tree.id,
                self.current_user.id,
            )
            await NewTagRelation.update_tag_relation([tag], file)
            await NewTimeRecord.update_record(file.id, "upload_stamp")
            await process_file(file)
            ret.append(file.to_dict())
        return self.data(ret)


@plugin.route(r"/file/(\d+)")
class CCXIFilesHandler(CCXIHandler):
    args = {
        "name": fields.String(required=True),
        "molds": fields.List(fields.Int(), required=True),
        "tags": fields.List(fields.Int(), required=True),
    }

    @staticmethod
    async def check_molds_limit(project, file, check_molds):
        molds_limit = get_config("ccxi.molds_limit")

        project_molds_limit = molds_limit.get(project.meta["prj_type"])
        if not check_molds or not project_molds_limit:
            return
        mold_name_map = {}
        mold_ids_limit = {}
        molds = await pw_db.execute(NewMold.select().where(NewMold.name.in_(project_molds_limit.keys())))
        for mold in molds:
            mold_name_map[mold.name] = mold.id
            if mold.name in project_molds_limit:
                mold_ids_limit[mold.id] = {
                    "name": mold.name,
                    "limit": project_molds_limit[mold.name]["limit"],
                    "mutually_exclusive": project_molds_limit[mold.name].get("mutually_exclusive", []),
                }

        mold_counter = Counter()
        peer_files = await pw_db.execute(NewFile.select().where(NewFile.tree_id == file.tree_id, NewFile.id != file.id))
        for peer_file in peer_files:
            mold_counter.update(peer_file.molds)

        for mold_id in check_molds:
            if mold_id not in mold_ids_limit:
                continue

            mold_limit = mold_ids_limit[mold_id]
            mold_name = mold_limit["name"]

            for exclusive_mold_name in mold_limit["mutually_exclusive"]:
                if mold_counter[mold_name_map.get(exclusive_mold_name)] > 0:
                    raise CustomError(_(f"当前版本下已有:{exclusive_mold_name},不能再增加该Schema:{mold_name}"))

            if mold_counter[mold_id] + 1 > mold_limit["limit"]:
                raise CustomError(_(f"当前版本下该Schema:{mold_name}的文件数量已达到其上限:{mold_limit['limit']}."))

    @Auth("browse")
    @doc(tags=["ccxi"])
    @use_kwargs(args, location="json")
    @peewee_transaction_wrapper
    async def put(self, fid, name, molds, tags):
        fid = int(fid)
        file = await NewFile.find_by_id(fid)
        if not file:
            raise CustomError(_("not found file"))
        if not await NewTag.all_ids_exists(tags):
            raise CustomError(_("Not all ids valid."))
        project = await NewFileProject.find_by_id(file.pid)
        if not project:
            raise CustomError(_("can't find the project"))
        await self.check_project_permission(self.current_user.id, project.id, project)
        await self.check_molds_limit(project, file, molds)

        if name != file.name:
            await file.update_(name=name)
        await NewFileService.update_molds(file, molds)
        await process_file(file)
        await NewTagRelation.update_tag_relation(tags, file)

        return self.data(file.to_dict())


@plugin.route(r"/tags")
class CCXITagsHandler(CCXIHandler):
    @Auth("browse")
    @doc(tags=["ccxi"])
    @use_kwargs(AsyncPagination.web_args, location="query")
    async def get(self, page, size):
        sql = f"""
        WITH mold_tag AS
                (select t.name, array_remove(array_agg(tr.relational_id), NULL) molds
                from tag t left join tag_relation tr on t.id = tr.tag_id
                where t.tag_type = {TagType.MOLD} group by t.name)
        select t.id, t.name, t.tag_type, coalesce(mt.molds, array[]::integer[]) molds
        from tag t left join mold_tag mt on t.name = mt.name
        where t.tag_type = {TagType.FILE}
        """
        params = {"page": page, "size": size}
        pagedata = await self.pagedata_from_request(self, sql, "", orderby="order by t.id", params=params)
        return self.data(pagedata)

    @Auth("manage_prj")
    @doc(tags=["ccxi"])
    @use_kwargs(file_tag_args, location="json")
    @peewee_transaction_wrapper
    async def post(self, name, molds):
        tag_type = TagType.FILE
        exists = await NewTag.find_by_kwargs(name=name, tag_type=tag_type)
        if exists:
            return self.error("文件类型已存在")
        tag = await NewTag.create(name=name, tag_type=tag_type)

        await NewMoldService.set_same_name_tag_on_molds(tag, molds)

        await NewHistory.save_operation_history(
            tag.id,
            self.current_user.id,
            HistoryAction.CREATE_TAG.value,
            self.current_user.name,
            meta=tag.to_dict(),
        )
        return self.data(tag.to_dict())


@plugin.route(r"/tag/(\d+)")
class CCXITagHandler(CCXIHandler):
    @Auth("browse")
    @doc(tags=["ccxi"])
    async def get(self, tid):
        sql = f"""
            WITH mold_tag AS
                    (select t.name, array_agg(tr.relational_id) molds from tag t left join tag_relation tr on t.id =
                    tr.tag_id
                    where t.tag_type = {TagType.MOLD} group by t.name)
            select t.id, t.name, t.tag_type, mt.molds from tag t left join mold_tag mt on t.name = mt.name
            where t.id = :tid
            """
        data = await db.raw_sql(sql, "first", tid=tid)
        if not data:
            raise CustomError("未找到该文件类型")
        return self.data(dict(data))

    @Auth("manage_prj")
    @doc(tags=["ccxi"])
    @use_kwargs(file_tag_args, location="json")
    @peewee_transaction_wrapper
    async def put(self, tid, name, molds):
        tag_type = TagType.FILE
        tag = await NewTag.find_by_id(tid)
        if not tag:
            raise CustomError("未找到该文件类型")

        if name != tag.name:
            if await NewTag.find_by_kwargs(name=name, tag_type=tag_type):
                return self.error("文件类型已存在")

        await tag.update_(name=name)
        await NewMoldService.set_same_name_tag_on_molds(tag, molds)

        await NewHistory.save_operation_history(
            tag.id,
            self.current_user.id,
            HistoryAction.MODIFY_TAG.value,
            self.current_user.name,
            meta=tag.to_dict(),
        )

        return self.data(tag.to_dict())


@plugin.route(r"/summary/ai_status")
class CCXIAIStatusSummaryHandler(CCXIHandler):
    args = {
        "prj_num": project_args["prj_num"],
        "version": fields.String(validate=field_validate.Length(min=1, max=128), load_default=""),
    }

    @Auth("browse")
    @doc(tags=["ccxi"])
    @use_kwargs(args, location="query")
    async def get(self, prj_num, version):
        project = await NewFileProject.find_by_kwargs(name=prj_num)
        if not project:
            return self.error(message="找不到该项目", errors="0002")

        if version:
            file_tree = await NewFileTree.find_by_kwargs(pid=project.id, name=version)
            if not file_tree:
                return self.error(message="找不到该版本", errors="0003")
            cond = f"file.tree_id = {file_tree.id}"
        else:
            cond = f"file.pid = {project.id}"
        sql = f"""select count(question.id), question.ai_status
        from question join file on question.fid=file.id
        where {cond}
        group by question.ai_status;"""
        questions = await db.raw_sql(sql, "all")

        data = {
            "prj_num": prj_num,
            "version": version,
            "total": 0,
            "doing": 0,
            "finish": 0,
            "failed": 0,
            "disable": 0,
            "unknown": 0,
        }
        total = 0
        for count, si_status in questions:
            key = "unknown"
            if si_status in (AIStatus.DOING, AIStatus.TODO):
                key = "doing"
            elif si_status == AIStatus.FINISH:
                key = "finish"
            elif si_status == AIStatus.FAILED:
                key = "failed"
            elif si_status == AIStatus.DISABLE:
                key = "disable"
            data[key] = count
            total += count
        data["total"] = total

        return self.data(data)


@plugin.route(r"/result/(?P<prj_num>\w*)/(?P<version>\w*)")
class CCXIResultHandler(CCXIHandler):
    args = {"keys": fields.String(data_key="fields", load_default="", validate=field_validate.Length(min=1))}

    @staticmethod
    def answer_filter(answer, keys):
        def _list_filter(items):
            filtered_list = []

            for value in items:
                if isinstance(value, list):
                    _value = _list_filter(value)
                # value is instance of dict:
                else:
                    _value = _dict_filter(value)
                if _value:
                    filtered_list.append(_value)
            return filtered_list

        def _dict_filter(_dict):
            filtered_dict = {}

            for key, value in _dict.items():
                if key in keys:
                    filtered_dict[key] = value
                    continue

                _value = None
                if isinstance(value, list):
                    _value = _list_filter(value)
                # value is instance of dict:
                elif value and "title" not in value:
                    _value = _dict_filter(value)

                if _value:
                    filtered_dict[key] = _value
            return filtered_dict

        if not keys:
            return answer
        return _dict_filter(answer)

    @Auth("browse")
    @doc(tags=["ccxi"])
    @use_kwargs(args, location="query")
    async def get(self, prj_num, version, keys):
        keys = list(filter(None, [x.strip() for x in keys.split(",")]))
        project = await NewFileProject.find_by_kwargs(name=prj_num)
        if not project:
            return self.error(message="找不到该项目", errors="0002")

        file_tree = await NewFileTree.find_by_kwargs(pid=project.id, name=version)
        if not file_tree:
            return self.error(message="找不到该版本", errors="0003")
        answers = {}
        molds = await NewMold.find_by_kwargs(delegate="all")
        mold_map = {m.id: m.name for m in molds}
        schemas = {}
        files = await NewFile.find_by_tree_id(file_tree.id)
        for file in files:
            questions = await NewQuestion.find_by_fid(file.id)
            if file.pdf_parse_status != PDFParseStatus.COMPLETE or not questions or not questions[0].answer:
                answers[file.name] = {}
                continue
            answer = await NewSpecialAnswer.get_answers(questions[0].id, NewSpecialAnswer.ANSWER_TYPE_JSON, top=1)
            if not answer:
                return self.error(f"{file.name}的导出答案未生成!")
            answers[file.name] = self.answer_filter(answer[0].data, keys)
            schemas[file.name] = mold_map.get(questions[0].mold)

        data = {"prj_num": prj_num, "version": version, "data": answers, "schemas": schemas}
        return self.data(data)


@plugin.route(r"/project/(?P<prj_num>\w*)/tree/(?P<version>\w*)/files")
class CCXIFileListHandler(CCXIHandler):
    @Auth("browse")
    @doc(tags=["ccxi"])
    async def get(self, prj_num, version):
        project = await NewFileProject.find_by_kwargs(name=prj_num)
        if not project:
            return self.error(message="找不到该项目", errors="0002")

        file_tree = await NewFileTree.find_by_kwargs(pid=project.id, name=version)
        if not file_tree:
            return self.error(message="找不到该版本", errors="0003")

        files = await pw_db.execute(
            NewFile.select(NewFile.id, NewFile.name).where(NewFile.tree_id == file_tree.id).dicts()
        )
        data = {"prj_num": prj_num, "version": version, "data": list(files)}
        return self.data(data)


@plugin.route(r"/files")
class CCXIFileDownloader(CCXIHandler):
    args = {"ids": fields.String(required=True, validate=field_validate.Regexp(r"[\d,]*\d$"))}

    @Auth("browse")
    @doc(tags=["ccxi"])
    @use_kwargs(args, location="query")
    async def get(self, ids):
        ids = [int(x.strip()) for x in ids.split(",")]
        if len(ids) > get_config("ccxi.download_files_limit", 20):
            raise CustomError(_("Too many files downloaded at once "))

        if not await NewFile.all_ids_exists(ids):
            return self.error(message="并非所有 ID 都有效", errors="0009")

        files = await NewFile.find_by_ids(ids)
        if len(files) == 1:
            return await self.export(localstorage.mount(files[0].path()), files[0].name)

        res = io.BytesIO()
        with ZipFile(res, "w") as res_fp:
            for file in files:
                data = localstorage.read_file(file.path())
                res_fp.writestr(file.name, data)
        return await self.export(res.getvalue(), f"{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}.zip")


# 以下为中诚信市场部的接口


@plugin.route(r"/market/contracts")
class CCXIMarketContracts(DbQueryHandler):
    args = {
        "contract_no": fields.String(load_default=""),
        "company_name": fields.String(load_default=""),
        "project_name": fields.String(load_default=""),
        "third_party_name": fields.String(load_default=""),
        "area": fields.String(load_default=""),
        "variety": fields.String(load_default=""),
        "date_signed_start": fields.Int(load_default=None),
        "date_signed_end": fields.Int(load_default=None),
        "created_utc_start": fields.Int(load_default=None),
        "created_utc_end": fields.Int(load_default=None),
    }

    @Auth("browse")
    @doc(tags=["ccxi-market"])
    @use_kwargs(AsyncPagination.web_args, location="query")
    @use_kwargs(args, location="query")
    async def get(self, page, size, **kwargs):
        cond = speedy.peewee_plus.orm.TRUE

        if kwargs["contract_no"]:
            cond &= NewCCXIContract.contract_no.contains(kwargs["contract_no"])
        if kwargs["company_name"]:
            cond &= NewCCXIContract.company_name.contains(kwargs["company_name"])
        if kwargs["project_name"]:
            cond &= NewCCXIContract.project_name.contains(kwargs["project_name"])
        if kwargs["third_party_name"]:
            cond &= NewCCXIContract.third_party_name.contains(kwargs["third_party_name"])
        if kwargs["area"]:
            cond &= NewCCXIContract.area.contains(kwargs["area"])
        if kwargs["variety"]:
            cond &= NewCCXIContract.variety == kwargs["variety"]
        if kwargs["date_signed_start"]:
            cond &= NewCCXIContract.date_signed >= kwargs["date_signed_start"]
        if kwargs["date_signed_end"]:
            cond &= NewCCXIContract.date_signed <= kwargs["date_signed_end"]
        if kwargs["created_utc_start"]:
            cond &= NewCCXIContract.created_utc >= kwargs["created_utc_start"]
        if kwargs["created_utc_end"]:
            cond &= NewCCXIContract.created_utc <= kwargs["created_utc_end"]

        query = NewCCXIContract.select().where(cond).order_by(NewCCXIContract.id.desc())
        data = await AsyncPagination(query, page=page, size=size).data()

        return self.data(data)


@plugin.route(r"/market/contract/(\d+)")
class CCXIMarketContract(DbQueryHandler):
    @Auth("browse")
    @doc(tags=["ccxi-market"])
    async def get(self, contract_id):
        data = await NewCCXIContract.find_by_id(contract_id)
        if not data:
            return self.error(_("Item Not Found"))
        return self.data(data.to_dict())
