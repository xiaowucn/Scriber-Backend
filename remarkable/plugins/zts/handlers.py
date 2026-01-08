import datetime
import http
import json
import logging
from collections import defaultdict
from itertools import groupby
from pathlib import Path

import speedy
from marshmallow import Schema, fields
from marshmallow.validate import OneOf

from remarkable.base_handler import Auth, BaseHandler
from remarkable.checker.helpers import audit_file_rules
from remarkable.common import field_validate
from remarkable.common.apispec_decorators import use_kwargs
from remarkable.common.constants import ZTS_DOC_TYPES_ANNUAL, ZTS_DOC_TYPES_SEMI, ZTSProjectStatus
from remarkable.common.enums import AuditAnswerType
from remarkable.common.exceptions import CustomError
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.models.query_helper import AsyncPagination, PaginationSchema
from remarkable.models.zts import ZTSProjectInfo
from remarkable.plugins import Plugin, PostFileValidator
from remarkable.plugins.cgs.services.comment import edit_answer_data
from remarkable.plugins.zts.service import ZTSFileService, ZTSProjectService
from remarkable.plugins.zts.utils import RULE_INFO
from remarkable.pw_models.audit_rule import NewAuditResult
from remarkable.pw_models.model import NewFileProject, NewMold
from remarkable.pw_models.question import NewQuestion
from remarkable.worker.tasks import process_file

plugin = Plugin(Path(__file__).parent.name)
logger = logging.getLogger(__name__)


class MetaDataSchema(Schema):
    filename = fields.Str(required=True)
    year = fields.Str(required=True, validate=field_validate.Regexp(r"^\d{4}$"))
    report_type = fields.Str(required=True, validate=OneOf(["本期年报", "本期半年报", "往期年报"]))


class FileUploadSchema(Schema):
    metadata = fields.Str(required=True)
    exchange = fields.Str(required=True, validate=OneOf(["上交所", "深交所"]))
    ext_uid = fields.Str(required=True, data_key="user_id")
    record_id = fields.Str(required=True)


@plugin.route(r"/files")
class FilesUploadHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(
        {
            "post_files": fields.List(
                fields.Raw(validate=PostFileValidator.check),
                required=True,
                data_key="file",
                validate=field_validate.Length(min=2, max=3),
            )
        },
        location="files",
    )
    @use_kwargs(FileUploadSchema, location="form")
    async def post(self, post_files: list, metadata: str, exchange: str, ext_uid: str, record_id: str):
        date = datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        user = await NewAdminUser.find_by_kwargs(ext_id=ext_uid)
        if not user:
            return self.error("invalid parameters: user_id.", status_code=http.HTTPStatus.BAD_REQUEST)

        files_meta = {}
        year_group_by_type = {}
        metadata_schema = MetaDataSchema()
        for item in json.loads(metadata):
            item = metadata_schema.load(item)
            year_group_by_type[item["report_type"]] = item["year"]
            files_meta[item["filename"]] = {"report_year": item["year"], "doc_type": item["report_type"]}

        try:
            if set(year_group_by_type.keys()) == ZTS_DOC_TYPES_SEMI:
                assert int(year_group_by_type["本期半年报"]) - int(year_group_by_type["往期年报"]) == 1
            elif set(year_group_by_type.keys()) == ZTS_DOC_TYPES_ANNUAL:
                assert int(year_group_by_type["本期年报"]) - int(year_group_by_type["往期年报"]) == 1
            else:
                return self.error("invalid parameters: report_type.", status_code=http.HTTPStatus.BAD_REQUEST)
        except Exception:
            return self.error("invalid parameters: year.", status_code=http.HTTPStatus.BAD_REQUEST)

        try:
            files = []
            async with pw_db.atomic():
                project = await ZTSProjectService.create(
                    name=date, uid=user.id, exchange=exchange, status=ZTSProjectStatus.TODO.value, record_id=record_id
                )

                for file in post_files:
                    if file.filename not in files_meta:
                        raise CustomError("invalid parameters: metadata.", resp_status_code=http.HTTPStatus.BAD_REQUEST)
                    meta = files_meta[file.filename]
                    file = await ZTSFileService.create(
                        file.filename,
                        file.body,
                        molds=[],
                        pid=project.id,
                        tree_id=project.rtree_id,
                        uid=user.id,
                        doc_type=meta["doc_type"],
                        report_year=meta["report_year"],
                    )
                    files.append(file)

            for file in files:
                await process_file(file)

        except Exception as exp:
            logger.exception(exp)
            return self.error("上传失败", status_code=http.HTTPStatus.BAD_REQUEST)
        return self.data({"project_id": project.id})


class ProjectSchema(PaginationSchema):
    exchange = fields.Str(load_default="", validate=OneOf(["上交所", "深交所"]))
    status = fields.Str(load_default="", validate=OneOf(ZTSProjectStatus.member_values()))
    project_id = fields.Int(load_default=0)
    file_name = fields.Str(load_default="")
    user_name = fields.Str(load_default="")


@plugin.route(r"/projects")
class ProjectsHandler(BaseHandler):
    @use_kwargs(ProjectSchema, location="query")
    @Auth("browse")
    async def get(self, exchange, status, project_id, file_name, user_name, page, size):
        cond = speedy.peewee_plus.orm.TRUE
        if exchange:
            cond &= ZTSProjectInfo.exchange == exchange
        if status:
            cond &= NewFileProject.status == status
        if project_id:
            cond &= NewFileProject.id == project_id
        if user_name:
            cond &= NewAdminUser.name.contains(user_name)
        if file_name:
            cond &= NewFile.name.contains(file_name)

        query = (
            NewFileProject.select(
                NewFileProject,
                ZTSProjectInfo,
                NewAdminUser.name.alias("user_name"),
            )
            .distinct(NewFileProject.id)
            .join(ZTSProjectInfo)
            .join(NewAdminUser, on=(NewFileProject.uid == NewAdminUser.id))
            .join(NewFile, on=(NewFileProject.id == NewFile.pid))
            .where(cond)
            .order_by(NewFileProject.id.desc())
        )
        data = await AsyncPagination(query.dicts(), page=page, size=size).data()

        return self.data(data)


@plugin.route(r"/projects/files")
class ProjectFilesHandler(BaseHandler):
    @use_kwargs({"project_ids": fields.Str(required=True)}, location="query")
    @Auth("browse")
    async def get(self, project_ids: str):
        project_ids = [int(x) for x in project_ids.split(",")]
        data = await ZTSFileService.get_files_by_project_ids(project_ids)
        ret = defaultdict(list)
        for item in data:
            ret[item["project"]].append(item)
        return self.data({"items": [{"project_id": k, "files": v} for k, v in ret.items()]})


@plugin.route(r"/projects/(\d+)/results")
class ResultHandler(BaseHandler):
    @Auth("browse")
    async def get(self, pid):
        pid = int(pid)
        query = (
            NewAuditResult.select()
            .join(NewFile, on=(NewAuditResult.fid == NewFile.id))
            .where(NewFile.pid == pid, NewAuditResult.answer_type == AuditAnswerType.final_answer)
        )
        results = await pw_db.execute(query.order_by(NewAuditResult.id))
        data = defaultdict(list)
        for result in results:
            data[result.name].append(result.to_dict())
        return self.data(data)


@plugin.route(r"/rule_info")
class RuleInfoHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs({"mold_id": fields.Int(required=True)}, location="query")
    async def get(self, mold_id: int):
        mold = await NewMold.find_by_id(mold_id)
        if not mold:
            return self.error(_("Item not found"), http.HTTPStatus.NOT_FOUND)
        return self.data(RULE_INFO[mold.name])


@plugin.route(r"/projects/(\d+)/answer_data")
class AnswerDataHandler(BaseHandler):
    post_args = {
        "add": fields.List(fields.Dict(validate=lambda x: set(x.keys()) == {"fid", "key", "data", "value", "schema"})),
        "update": fields.List(fields.Dict(validate=lambda x: set(x.keys()) == {"id", "fid", "key", "data", "value"})),
        "delete": fields.List(fields.Dict(validate=lambda x: set(x.keys()) == {"id", "key", "fid"})),
    }

    @staticmethod
    def group_by_fid(items: list):
        ret = defaultdict(list)
        for qid, data in groupby(items, key=lambda x: x.pop("fid")):
            ret[qid] = list(data)
        return ret

    @Auth("browse")
    @use_kwargs(post_args, location="json")
    async def post(self, pid, add, update, delete):
        pid = int(pid)
        add = self.group_by_fid(add)
        update = self.group_by_fid(update)
        delete = self.group_by_fid(delete)

        files = await NewFile.find_by_pid(pid)
        last_question = None
        for file in files:
            question = await NewQuestion.get_master_question(file.id)
            if not question:
                return self.error(f"can't find question for {file.id}")
            last_question = question
            await edit_answer_data(question.id, add[file.id], update[file.id], delete[file.id], self.current_user.id)
        if last_question:
            await audit_file_rules(fid=last_question.fid)

        return self.data({})
