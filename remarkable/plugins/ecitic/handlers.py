import http
import logging
import os
from collections import defaultdict
from datetime import datetime
from itertools import chain
from pathlib import Path

import peewee
import speedy.peewee_plus.orm
from marshmallow import Schema as MMSchema
from marshmallow import validates
from marshmallow.exceptions import ValidationError as MMValidationError
from pydantic import ValidationError
from webargs import fields

from remarkable.answer.common import is_empty_answer
from remarkable.base_handler import Auth, BaseHandler, PermCheckHandler
from remarkable.common import field_validate
from remarkable.common.apispec_decorators import use_kwargs
from remarkable.common.constants import (
    EciticExternalSource,
    EciticTgTaskType,
    EciticTgTriggerType,
    HistoryAction,
    ModelEnableStatus,
    SpecialAnswerType,
)
from remarkable.common.enums import AuditAnswerType, TaskType
from remarkable.common.exceptions import CustomError
from remarkable.common.schema import Schema
from remarkable.common.storage import localstorage
from remarkable.common.util import generate_timestamp, get_key_path, validate_timestamp
from remarkable.config import get_config
from remarkable.converter import SimpleJSONConverter
from remarkable.converter.utils import class_bakery, generate_customer_answer, prepare_data
from remarkable.db import peewee_transaction_wrapper, pw_db
from remarkable.models.ecitic import (
    EciticCompareRecord,
    EciticCompareRecordResultRef,
    EciticCompareResult,
    EciticFile,
    EciticFileInfo,
    EciticParaMap,
    EciticPush,
    EciticPushRecord,
    EciticTemplate,
)
from remarkable.models.model_version import NewModelVersion
from remarkable.models.new_file import NewFile
from remarkable.models.new_model_answer import ModelAnswer
from remarkable.models.new_user import NewAdminUser
from remarkable.models.query_helper import AsyncPagination
from remarkable.plugins import Plugin, PostFileValidator
from remarkable.plugins.ccxi.handlers import supported_exts
from remarkable.plugins.ecitic.common import (
    EciticExternalAnswerConverter,
    ecitic_get_files_and_questions_by_tree,
    ecitic_para_map_convert,
    ecitic_path_list,
    ecitic_tg_diff,
    ecitic_tg_push,
    get_push_data,
    is_valid_mappings,
    refresh_ecitic_new_file,
    split_path,
)
from remarkable.plugins.fileapi.worker import ChapterNode, PDFCache
from remarkable.pw_models.answer_data import NewAnswerData
from remarkable.pw_models.audit_rule import NewAuditResult
from remarkable.pw_models.model import (
    NewFileProject,
    NewFileTree,
    NewHistory,
    NewMold,
    NewSpecialAnswer,
)
from remarkable.pw_models.question import NewQuestion, QuestionWithFK
from remarkable.schema.special_answer import SpecialPageAnswer
from remarkable.service.answer import get_master_question_answer
from remarkable.service.ecitic import EciticTGFileService
from remarkable.service.new_file import CITICFileService, NewFileService, create_pdf_cache
from remarkable.service.new_file_project import NewFileProjectService
from remarkable.service.new_file_tree import get_crumbs
from remarkable.worker.tasks import process_file

plugin = Plugin(Path(__file__).parent.name)
logger = logging.getLogger(__name__)


class _PermCheckHandler(BaseHandler):
    async def get_file(self, fid: int | str) -> NewFile:
        file = await NewFile.find_by_id(int(fid), QuestionWithFK.select())
        if not file:
            raise CustomError(_("Project not exists!"), resp_status_code=http.HTTPStatus.NOT_FOUND)

        if file.uid != self.current_user.id and not await self.current_user.has_perms("manage_prj"):
            raise CustomError(
                _("You have no permission to access this project!"),
                resp_status_code=http.HTTPStatus.FORBIDDEN,
            )
        return file


@plugin.route(r"/files/(\d+)/chapter-info")
class PdfChapterInfoHandler(_PermCheckHandler):
    @Auth("browse")
    async def get(self, fid):
        file = await self.get_file(fid)
        pdf_cache = PDFCache(file)
        info_path = pdf_cache.chapter_info_path
        if not localstorage.exists(info_path):
            logger.warning(f"chapter_info_path: {info_path} not found, rebuilding...")
            await create_pdf_cache(file, force=True)
            logger.info(f"chapter_info_path: {info_path} rebuilt")
        root_node: ChapterNode = pdf_cache.get_chapter_info()[-1]
        return self.data(root_node.to_dict())


@plugin.route(r"/files/(\d+)/pageinfo")
class PageInfoHandler(_PermCheckHandler):
    @Auth("browse")
    async def get(self, fid):
        file = await self.get_file(fid)
        pdf_cache = PDFCache(file)
        page_info_path = pdf_cache.page_info_path
        if not localstorage.exists(page_info_path):
            logger.warning(f"page_info_path: {page_info_path} not found, rebuilding...")
            await create_pdf_cache(file, force=True)
            logger.info(f"page_info_path: {page_info_path} rebuilt")
        return self.data(pdf_cache.get_page_info())


@plugin.route(r"/files/(\d+)/pdf")
class GetFileHandler(_PermCheckHandler):
    @Auth("browse")
    async def head(self, fid):
        return await self._do(fid)

    @Auth("browse")
    async def get(self, fid):
        return await self._do(fid)

    async def _do(self, fid):
        file = await self.get_file(fid)

        if self.is_first_fetch_file():
            await NewHistory.save_operation_history(
                file.id,
                self.current_user.id,
                HistoryAction.OPEN_PDF.value,
                self.current_user.name,
                meta=file.to_dict(),
            )
        return await self.export(file.pdf_path(abs_path=True), os.path.splitext(file.name)[0] + ".pdf")


@plugin.route(r"/questions/(\d+)/answer")
class AnswerExportHandler(_PermCheckHandler):
    @Auth("browse")
    @use_kwargs(
        {
            "answer_type": fields.Str(load_default="json", validate=field_validate.OneOf(("json", "xlsx"))),
            "page": fields.Int(load_default=None),
            "fid": fields.Int(required=True, data_key="file_id"),
        },
        location="query",
    )
    async def get(self, qid, answer_type, page, fid):
        file = await self.get_file(fid)

        if not file.questions or not file.questions[0].answer:
            return self.error(_("Answer not ready yet!"), status_code=http.HTTPStatus.BAD_REQUEST)

        # NOTE: 订制业务，question 和 file 其实是一对一，所以直接取第一个 question 就算正常答案
        qid = file.questions[0].id

        if not await pw_db.exists(
            NewSpecialAnswer.select().where(
                NewSpecialAnswer.qid == qid,
                NewSpecialAnswer.answer_type == NewSpecialAnswer.ANSWER_TYPE_JSON,
                NewSpecialAnswer.data.is_null(False),
            )
        ):
            try:
                await generate_customer_answer(qid)
            except Exception as exp:
                raise CustomError(
                    _("Unsupported file found, ensure the document type is correct."),
                    resp_status_code=http.HTTPStatus.BAD_REQUEST,
                ) from exp

        answers = await NewSpecialAnswer.get_answers_by_page(qid, NewSpecialAnswer.ANSWER_TYPE_JSON, top=1, page=page)
        if answer_type == "json":
            return (
                self.data(answers[0])
                if answers
                else self.error(_("Answer not ready yet!"), status_code=http.HTTPStatus.BAD_REQUEST)
            )

        meta_data = await prepare_data(qid)
        data = await self.run_in_executor(self._to_excel, meta_data, answers[0])
        file_name = meta_data.file.meta_info.get("project_name", os.path.splitext(meta_data.file.name)[0])
        return await self.export(data, f"{file_name}-{datetime.now().strftime('%Y%m%d')}.xlsx")

    @staticmethod
    def _to_excel(meta_data, json_data):
        clz = class_bakery.get_class(meta_data.mold.name, class_bakery)
        wb_from_json = clz.load_workbook_from_json(json_data)
        return clz.to_excel(wb_from_json)

    @Auth("browse")
    @use_kwargs({"data": fields.Field(required=True)}, location="json")
    async def post(self, qid, data):
        qid = int(qid)
        file = await pw_db.first(
            NewFile.select().join(NewQuestion, on=(NewFile.id == NewQuestion.fid)).where(NewQuestion.id == qid)
        )
        if not file:
            return self.error(_("Project not exists!"), status_code=http.HTTPStatus.NOT_FOUND)

        if file.uid != self.current_user.id and not await self.current_user.has_perms("manage_prj"):
            return self.error(
                _("You have no permission to access this project!"),
                status_code=http.HTTPStatus.FORBIDDEN,
            )

        if isinstance(data, dict) and "pages" in data:
            try:
                SpecialPageAnswer.model_validate(data)
            except ValidationError:
                return self.error(_("Invalid answer data detected!"), status_code=http.HTTPStatus.BAD_REQUEST)
        await NewSpecialAnswer.update_or_create(qid, NewSpecialAnswer.ANSWER_TYPE_JSON, data)
        return self.data({})


@plugin.route(r"/supported_report_types")
class ReportTypesHandler(BaseHandler):
    @Auth("browse")
    async def get(self):
        return self.data(CITICFileService.report_types)


@plugin.route(r"/projects/(\d+)")
class UDProjectHandler(_PermCheckHandler):
    @Auth("browse")
    async def delete(self, file_id):
        file = await self.get_file(file_id)
        await file.soft_delete()
        return self.data({})


@plugin.route(r"/projects")
class CRProjectHandler(BaseHandler):
    param = {
        "project_name": fields.Str(required=True, validate=field_validate.Length(1)),
        "project_type": fields.Str(
            load_default=list(CITICFileService.report_types)[0],
            validate=field_validate.OneOf(list(CITICFileService.report_types)),
        ),
    }

    search_param = {
        "project_id": fields.Int(),
        "project_name": fields.Str(),
    }

    @Auth("browse")
    @use_kwargs(param, location="form")
    @use_kwargs(
        {
            "files": fields.List(
                fields.Raw(validate=PostFileValidator.check),
                required=True,
                data_key="file",
                validate=field_validate.Length(equal=1),
            )
        },
        location="files",
    )
    async def post(self, files, project_name, project_type):
        file = files[0]
        file = await CITICFileService.create(
            file["filename"], file["body"], project_name, project_type, self.current_user.id
        )
        await process_file(file)
        return self.data(file.to_dict())

    @Auth("browse")
    @use_kwargs(AsyncPagination.web_args, location="query")
    @use_kwargs(search_param, location="query")
    async def get(self, page, size, **params):
        cond = NewFile.deleted_utc == 0
        if not await self.current_user.has_perms("manage_prj"):
            cond &= NewFile.uid == self.current_user.id
        if "project_id" in params:
            cond &= NewFile.id == params["project_id"]
        if "project_name" in params:
            cond &= NewFile.meta_info["project_name"].ilike(f"%{params['project_name']}%")

        query = (
            NewFile.select(
                NewFile,
                NewQuestion.ai_status.alias("question_ai_status"),
                NewQuestion.id.alias("question_id"),
                NewAdminUser.name.alias("user_name"),
            )
            .join(
                NewQuestion,
                on=(
                    (NewFile.id == NewQuestion.fid)
                    & (
                        NewQuestion.mold.in_(
                            NewMold.select(NewMold.id).where(
                                NewMold.name.in_([i["name"] for i in CITICFileService.report_types.values()])
                            )
                        )
                    )
                ),
            )
            .join(
                NewAdminUser,
                join_type=peewee.JOIN.LEFT_OUTER,
                on=(NewFile.uid == NewAdminUser.id),
                include_deleted=True,
            )
            .where(cond)
            .order_by(NewFile.id.desc())
            .dicts()
        )
        data = await AsyncPagination(query, page, size).data(dump_func=self.packer)
        return self.data(data)

    @staticmethod
    def packer(row, *args):
        row["user_name"] = row["user_name"] or "已注销"
        return row


# *************** 以下为中信托管部接口 ******************


@plugin.route(r"/para/mappings")
class CRParaMappingHandler(BaseHandler):
    param = {
        "category": fields.Str(load_default=""),
        "label": fields.Str(load_default=""),
        "group_name": fields.Str(load_default=""),
        "to_value": fields.Str(load_default=""),
    }

    post_param = {
        "category": fields.Str(required=True),
        "field": fields.Str(required=True),
        "label": fields.Str(required=True),
        "group_name": fields.Str(required=True),
        "values": fields.List(fields.Str(), required=True),
        "to_value": fields.Str(required=True),
    }

    @Auth("browse")
    @use_kwargs(param, location="query")
    @use_kwargs(AsyncPagination.web_args, location="query")
    async def get(self, category, label, group_name, to_value, page, size):
        cond = speedy.peewee_plus.orm.TRUE
        query = EciticParaMap.select().order_by(EciticParaMap.id.desc()).dicts()
        if category:
            cond = EciticParaMap.category.contains(category)
        if label:
            cond &= EciticParaMap.label == label
        if group_name:
            cond &= EciticParaMap.group_name.contains(group_name)
        if to_value:
            cond &= EciticParaMap.to_value.contains(to_value)
        data = await AsyncPagination(query.where(cond), page, size).data()
        return self.data(data)

    @Auth("browse")
    @use_kwargs(post_param, location="json")
    @peewee_transaction_wrapper
    async def post(self, **kwargs):
        try:
            para_mapping = await EciticParaMap.create(**kwargs)
            await is_valid_mappings(para_mapping.field)
        except peewee.IntegrityError as exp:
            logger.exception(str(exp))
            return self.error(f"参数值:{kwargs['field']},参数统称:{kwargs['group_name']}的参数映射已存在,请勿重复创建")
        return self.data(para_mapping.to_dict())


@plugin.route(r"/para/mappings/(\d+)")
class UDParaMappingHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(CRParaMappingHandler.post_param, location="json")
    @peewee_transaction_wrapper
    async def put(self, mid, **kwargs):
        try:
            await EciticParaMap.update_by_pk(mid, **kwargs)
            await is_valid_mappings(kwargs["field"])
        except peewee.IntegrityError as exp:
            logger.exception(str(exp))
            return self.error(f"参数值:{kwargs['field']},参数统称:{kwargs['group_name']}的参数映射已存在,请勿重复创建")
        return self.data({})

    @Auth("browse")
    async def delete(self, mid):
        if mapping := await EciticParaMap.find_by_id(mid):
            await mapping.soft_delete()

        return self.data({})


@plugin.route(r"/para/mappings/convert/(\d+)")
class ParaMappingCheckHandler(BaseHandler):
    @Auth("browse")
    async def get(self, qid):
        question = await NewQuestion.find_by_id(qid)
        if not question:
            return self.error(_("Question not found"))
        answer, master_mold = await get_master_question_answer(question)
        is_success, data = await ecitic_para_map_convert(answer)
        return self.data(data["userAnswer"]["items"])


@plugin.route(r"/files/(?P<fid>\d+)/data")
@plugin.route(r"/question/(?P<question_id>\d+)/push")
class ParaPushHandler(BaseHandler):
    args = {
        "compare_record_id": fields.Int(load_default=None),
        "to_count": fields.Bool(load_default=False),  # 仅参与统计
    }

    @Auth("browse")
    async def get(self, fid):
        question = await pw_db.first(NewQuestion.select().where(NewQuestion.fid == fid))
        if not question:
            return self.error(_("Question not found"))
        file, push_data_list = await get_push_data(question.id)
        return self.data(push_data_list)

    @use_kwargs(args, location="query")
    @Auth("browse")
    async def post(self, question_id, compare_record_id, to_count):
        file, push_data_list = await get_push_data(
            question_id, compare_record_id, self.current_user.name, only_count=to_count
        )
        project = await NewFileProject.find_by_id(file.pid)
        if to_count:
            task_type = EciticTgTaskType.TO_COUNT
        else:
            task_type = EciticTgTaskType.COMPARE if compare_record_id else EciticTgTaskType.SINGLE
        try:
            records = await ecitic_tg_push(
                project.name,
                file,
                self.current_user.id,
                push_data_list,
                task_type,
                EciticTgTriggerType.MANUAL,
                compare_record_id,
            )
        except Exception as exp:
            logger.exception(exp)
            return self.error(_("Push Failed"))
        error = any(record.status == 0 for record in records)
        if error:
            return self.error(_("Push Failed"))
        return self.data({"records": [record.to_dict() for record in records]})


@plugin.route(r"/schema-items")
class SchemaItemsHandler(BaseHandler):
    params = {
        "mold": fields.Int(load_default=0),
        "for_convert": fields.Bool(load_default=False),
    }

    @use_kwargs(params, location="query")
    @Auth("browse")
    async def get(self, mold, for_convert):
        query = NewMold.select(NewMold.data)
        cond = peewee.SQL("true")
        if mold:
            cond &= NewMold.id == mold
        schemas = await pw_db.execute(query.where(cond))
        if not schemas:
            return self.error("错误，Schema不存在", status_code=404)

        schema_items = {}
        for schema in schemas:
            for schema_path, _ in Schema(schema.data).iter_schema_attr(True):
                path_list = ecitic_path_list(schema_path[1:])
                if for_convert and "拆分" not in path_list:
                    continue
                self.fill_schema_items(schema_items, path_list)

        return self.data(schema_items)

    @classmethod
    def fill_schema_items(cls, schema_items, path_list):
        if not path_list:
            return schema_items
        path = path_list.pop(0)
        if path not in schema_items:
            schema_items[path] = {}
        cls.fill_schema_items(schema_items[path], path_list)


@plugin.route(r"/templates")
class CRTemplateHandler(BaseHandler):
    post_param = {
        "name": fields.Str(required=True),
        "business_group": fields.Str(required=True),
        "mold": fields.Int(required=True),
        "fields": fields.List(fields.Str(), required=True),
        "uid": fields.Int(required=True),
        "is_default": fields.Bool(required=True),
    }

    @Auth("browse")
    @use_kwargs(AsyncPagination.web_args, location="query")
    @use_kwargs({"mold": fields.Int(required=False, load_default=0)}, location="query")
    async def get(self, mold, page, size):
        query = EciticTemplate.select(
            EciticTemplate.id,
            EciticTemplate.name,
            EciticTemplate.fields,
            EciticTemplate.business_group,
            EciticTemplate.is_default,
            EciticTemplate.created_utc,
            NewAdminUser.name.alias("uname"),
            NewMold.name.alias("mold"),
        )
        query = query.join(NewAdminUser, on=EciticTemplate.uid == NewAdminUser.id)
        query = query.join(NewMold, on=EciticTemplate.mold == NewMold.id)
        query = query.order_by(EciticTemplate.id.desc()).dicts()
        cond = speedy.peewee_plus.orm.TRUE
        if mold:
            cond &= EciticTemplate.mold == mold
        data = await AsyncPagination(query.where(cond), page, size).data()
        return self.data(data)

    @Auth("browse")
    @use_kwargs(post_param, location="json")
    @peewee_transaction_wrapper
    async def post(self, **kwargs):
        if kwargs["is_default"]:
            await EciticTemplate.keep_unique_default(kwargs["business_group"], kwargs["mold"])
        if await EciticTemplate.get_by_cond(EciticTemplate.name == kwargs["name"]):
            return self.error("模版名称已存在!")
        template = await EciticTemplate.create(**kwargs)
        return self.data(template.to_dict())


@plugin.route(r"/templates/(\d+)")
class UDTemplateHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(CRTemplateHandler.post_param, location="json")
    @peewee_transaction_wrapper
    async def put(self, tid, **kwargs):
        if kwargs["is_default"]:
            await EciticTemplate.keep_unique_default(kwargs["business_group"], kwargs["mold"])

        if await EciticTemplate.get_by_cond((EciticTemplate.name == kwargs["name"]) & (EciticTemplate.id != tid)):
            return self.error("模版名称已存在!")

        await EciticTemplate.update_by_pk(tid, **kwargs)
        return self.data({})

    @Auth("browse")
    async def delete(self, tid):
        if mapping := await EciticTemplate.find_by_id(tid):
            if push_config := await EciticPush.get_by_cond(EciticPush.template == tid):
                return self.error(f"模板已在推送设置管理中关联(id: {push_config.id})，无法删除！")
            await mapping.soft_delete()
        return self.data({})


@plugin.route(r"/business-groups")
class BusinessGroupHandler(BaseHandler):
    @Auth("browse")
    async def get(self):
        data = get_config("citics.business_groups") or []
        return self.data(data)


@plugin.route(r"/push/configs")
class CRPushConfigsHandler(BaseHandler):
    post_param = {
        "template": fields.Int(required=True),
        "system": fields.Str(required=True),
        "function": fields.Str(required=True),
        "email": fields.Email(required=True),
        "push_address": fields.Str(required=True),
        "uid": fields.Int(required=True),
        "enabled": fields.Bool(required=True),
    }

    @Auth("browse")
    @use_kwargs(AsyncPagination.web_args, location="query")
    async def get(self, page, size):
        query = EciticPush.select(
            EciticPush.id,
            EciticPush.system,
            EciticPush.function,
            EciticPush.email,
            EciticPush.push_address,
            EciticPush.enabled,
            EciticPush.created_utc,
            EciticTemplate.id.alias("template_id"),
            EciticTemplate.name.alias("template_name"),
            NewAdminUser.name.alias("uname"),
        )
        query = query.join(EciticTemplate, on=EciticPush.template == EciticTemplate.id)
        query = query.join(NewAdminUser, on=EciticPush.uid == NewAdminUser.id)
        query = query.order_by(EciticPush.id.desc())
        data = await AsyncPagination(query.dicts(), page, size).data()
        return self.data(data)

    @Auth("browse")
    @use_kwargs(post_param, location="json")
    async def post(self, **kwargs):
        template = await EciticPush.create(**kwargs)
        return self.data(template.to_dict())


@plugin.route(r"/push/configs/(\d+)")
class UDPushConfigsHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(CRPushConfigsHandler.post_param, location="json")
    async def put(self, config_id, **kwargs):
        await EciticPush.update_by_pk(config_id, **kwargs)
        return self.data({})

    @Auth("browse")
    async def delete(self, config_id):
        if config := await EciticPush.find_by_id(config_id):
            await config.soft_delete()
        return self.data({})


@plugin.route(r"/product-types")
class ProductTypeHandler(BaseHandler):
    @Auth("browse")
    async def get(self):
        data = get_config("citics.product_types") or []
        return self.data(data)


@plugin.route(r"/projects/search")
class ProjectsHandler(BaseHandler):
    param = {
        "pid": fields.Int(load_default=None),
        "name": fields.Str(load_default=None),
        "product_type": fields.Str(load_default=None),
        "product_name": fields.Str(load_default=None),
        "product_num": fields.Str(load_default=None),
    }

    @Auth("browse")
    @use_kwargs(AsyncPagination.web_args, location="query")
    @use_kwargs(param, location="query")
    async def get(self, pid, name, product_type, product_name, product_num, page, size):
        query = NewFileProject.select(
            NewFileProject.id,
            NewFileProject.name,
            NewFileProject.meta,
            NewFileProject.rtree_id,
            NewAdminUser.name.alias("user_name"),
        )
        query = query.join(NewAdminUser, on=(NewFileProject.uid == NewAdminUser.id))
        cond = speedy.peewee_plus.orm.TRUE
        cond &= ~NewFileProject.visible
        if pid:
            cond &= NewFileProject.id == pid
        if name:
            cond &= NewFileProject.name.contains(name)
        if product_type:
            cond &= NewFileProject.meta["product_type"] == product_type
        if product_name:
            cond &= NewFileProject.meta["product_name"].ilike(f"%{product_name}%")
        if product_num:
            cond &= NewFileProject.meta["product_num"].ilike(f"%{product_num}%")

        query = query.order_by(NewFileProject.id.desc())
        data = await AsyncPagination(query.where(cond).dicts(), page, size).data()
        return self.data(data)


@plugin.route(r"/tree/0/file")
class UploadFileHandler(PermCheckHandler):
    product_type_map = {
        "1": "私募基金",
        "3": "资管计划",
    }

    file_args = {
        "file_metas": fields.List(
            fields.Raw(), data_key="file", required=True, error_messages={"required": "not found upload document"}
        ),
    }
    form_args = {
        "molds": fields.List(fields.Int(), required=True),
        "templates": fields.List(fields.Int(), required=True),
        "version": fields.Str(load_default=None),
        "staff_id": fields.Str(required=True),
        "group_name": fields.Str(
            required=True, validate=field_validate.OneOf(get_config("citics.business_groups") or [])
        ),
        "project_name": fields.Str(required=True),
        "product_name": fields.Str(load_default=None),
        "product_num": fields.Str(load_default=None),
        "product_type": fields.Str(load_default=None, validate=field_validate.OneOf(product_type_map)),
        "batch_no": fields.Str(load_default=None),
        "stat_after_push": fields.Int(load_default=1, validate=field_validate.OneOf([0, 1])),
    }

    @Auth("browse")
    @use_kwargs(form_args, location="form")
    @use_kwargs(file_args, location="files")
    async def post(
        self, file_metas, molds, templates, version, project_name, group_name, staff_id, stat_after_push, **kwargs
    ):
        stat_after_push = bool(stat_after_push)
        user = await pw_db.first(NewAdminUser.select(NewAdminUser.id).where(NewAdminUser.ext_id == staff_id))
        if not user:
            raise CustomError(f"can't find the user {staff_id=}")
        uid = user.id
        if project := await NewFileProject.find_by_kwargs(name=project_name, visible=True):
            raise CustomError(f"项目名称已在文档智能提取系统中存在, {project.id=}")

        if not (project := await NewFileProject.find_by_kwargs(name=project_name, visible=False)):
            meta = self.project_meta_convert(kwargs)
            await self.params_check(molds, templates, meta["product_type"])
            project = await NewFileProjectService.create(name=project_name, uid=uid, visible=False, meta=meta)

        tree = await NewFileTree.find_by_id(project.rtree_id)
        if not tree:
            raise CustomError(_("can't find the tree"))

        await self.check_project_permission(project.id, project=project)
        ret = await self.upload_file(
            project, tree, molds, file_metas, uid, templates, version, group_name, stat_after_push
        )
        return self.data(ret)

    @staticmethod
    async def upload_file(project, tree, molds, file_metas, uid, templates, version, group_name, stat_after_push=True):
        ret = []
        file_group_by_ext = defaultdict(list)
        for file_meta in file_metas:
            ext = os.path.splitext(file_meta["filename"])[-1].lower()
            if ext not in supported_exts:
                raise CustomError("Unsupported file type detected")
            file_group_by_ext[ext].append(file_meta)

        for ext, files in file_group_by_ext.items():
            for index, file_meta in enumerate(files):
                file = await EciticTGFileService.create_file(
                    file_meta["filename"],
                    file_meta["body"],
                    molds,
                    project.id,
                    tree.id,
                    uid,
                    task_type=TaskType.AUDIT.value,
                    templates=templates,
                    version=version,
                    group_name=group_name,
                    stat_after_push=stat_after_push,
                )

                if index == len(file_metas) - 1:
                    # 中信托管部目前无多schema, 故可直接取molds[0]
                    await refresh_ecitic_new_file(project.id, ext, molds[0], version)

                await process_file(file)
                ret.append(file.to_dict())
        return ret

    @classmethod
    def project_meta_convert(cls, meta):
        for key, value in meta.items():
            if key in ["product_name", "product_num", "product_type"] and not value:
                raise CustomError(f'Missing key "{key}"')
            if key == "product_type":
                meta[key] = cls.product_type_map[value]

        return meta

    @classmethod
    async def params_check(cls, mold_ids, template_ids, product_type):
        product_type_molds = {
            "资管计划": ["资管合同", "资管合同_补充协议"],
            "私募基金": ["私募基金合同", "私募基金合同_补充协议"],
        }
        valid_molds = product_type_molds[product_type]
        mold_query = NewMold.select(NewMold.id, NewMold.name).where(NewMold.id << mold_ids)
        molds = await pw_db.execute(mold_query)
        if len(molds) != len(mold_ids):
            raise CustomError("molds存在无效id")
        for mold in molds:
            if mold.name not in valid_molds:
                raise CustomError("模型与项目类型不符")

        template_query = EciticTemplate.select(EciticTemplate.id, EciticTemplate.mold).where(
            EciticTemplate.id << template_ids
        )
        templates = await pw_db.execute(template_query)
        if len(templates) != len(template_ids):
            raise CustomError("templates存在无效id")
        for template in templates:
            if template.mold not in mold_ids:
                raise CustomError("模版与模型不符")


@plugin.route(r"/tree/(?P<tree_id>\d+)/file")
class FileHandler(PermCheckHandler):
    file_args = {
        "file_metas": fields.List(
            fields.Raw(), data_key="file", required=True, error_messages={"required": "not found upload document"}
        ),
    }
    form_args = {
        "molds": fields.List(fields.Int(), load_default=[]),
        "templates": fields.List(fields.Int(), load_default=[]),
        "version": fields.Str(load_default=None),
        "group_name": fields.Str(
            required=True, validate=field_validate.OneOf(get_config("citics.business_groups") or [])
        ),
    }

    @Auth("browse")
    @use_kwargs(form_args, location="form")
    @use_kwargs(file_args, location="files")
    async def post(self, tree_id, file_metas, molds, templates, version, group_name):
        tree = await NewFileTree.find_by_id(tree_id)
        if not tree:
            raise CustomError(_("can`t find the tree"))
        project = await NewFileProject.find_by_id(tree.pid)
        if not project:
            raise CustomError(_("can`t find the project"))
        await self.check_project_permission(project.id, project=project)
        ret = await UploadFileHandler.upload_file(
            project, tree, molds, file_metas, self.current_user.id, templates, version, group_name
        )
        return self.data(ret)


@plugin.route(r"/files/(\d+)")
class FileHandlerOrigin(PermCheckHandler):
    args = {
        "name": fields.String(required=True),
        "molds": fields.List(fields.Int(), required=True),
        "templates": fields.List(fields.Int(), required=True),
        "version": fields.String(required=True),
        "group_name": fields.String(required=True),
        "need_stat": fields.Bool(load_default=None, validate=field_validate.OneOf([False])),
    }

    @Auth("browse")
    async def get(self, fid):
        await self.check_file_permission(fid)
        query = EciticFile.select(EciticFile, EciticFileInfo, NewQuestion.id.alias("qid")).join(EciticFileInfo)
        query = query.join(NewQuestion, on=(NewQuestion.fid == EciticFile.id))

        file = await pw_db.first(query.where(EciticFile.id == fid).dicts())
        if not file:
            raise CustomError(_("not found file"))

        tree = await NewFileTree.find_by_id(file["tree_id"])
        file["crumbs"] = await get_crumbs(tree.id)

        return self.data(file)

    @use_kwargs(args, location="json")
    # 数据链路存在异步任务，不能用事务
    async def put(self, fid, name, molds, templates, version, group_name, need_stat):
        fid = int(fid)
        file = await EciticFile.find_by_id(fid, EciticFileInfo.select())
        if not file:
            raise CustomError(_("not found file"))

        old_mold = file.molds[0] if file.molds else None
        old_version = file.file_info.version

        update_paras = {}
        if name != file.name:
            if not get_config("web.allow_same_name_file_in_project", True):
                same_name_file = await NewFile.find_by_kwargs(name=name, pid=file.pid)
                if same_name_file:
                    raise CustomError(_("该项目下已存在同名的文件"))
            update_paras["name"] = name
        await file.update_(**update_paras)

        info_update_paras = {"templates": templates, "version": version, "group_name": group_name}
        if need_stat is False:
            info_update_paras["need_stat"] = False
        await pw_db.execute(EciticFileInfo.update(**info_update_paras).where(EciticFileInfo.file == file.id))
        await NewFileService.update_molds(file, molds)
        await process_file(file)

        new_mold = file.molds[0] if file.molds else None
        new_version = version
        await refresh_ecitic_new_file(file.pid, file.ext, new_mold, new_version, old_mold, old_version)

        await NewHistory.save_operation_history(
            file.id,
            self.current_user.id,
            HistoryAction.MODIFY_FILE.value,
            self.current_user.name,
            meta=file.to_dict(exclude=(EciticFile.project,), extra_attrs=("pid",)),
        )
        return self.data({})


@plugin.route(r"/question/(?P<qid>\d+)/diff")
class DiffHandler(PermCheckHandler):
    args = {
        "standard_qid": fields.Int(required=True),
    }

    @Auth("browse")
    @use_kwargs(args, location="query")
    async def post(self, qid, standard_qid):
        compare_record, _, _ = await ecitic_tg_diff(qid, standard_qid, uid=self.current_user.id)
        return self.data(compare_record.to_dict())


@plugin.route(r"/compares/(?P<compare_id>\d+)")
class GetCompareHandler(PermCheckHandler):
    @Auth("browse")
    async def get(self, compare_id):
        data = await EciticCompareRecord.find_by_id(compare_id)
        if data:
            return self.data(data.to_dict())
        raise CustomError(_("can`t find the compare record"), resp_status_code=404)


@plugin.route(r"/compare_records/(?P<compare_id>\d+)/results")
class CompareRecordResultsHandler(BaseHandler):
    async def get(self, compare_id):
        StdQuestion = NewQuestion.alias("StdQuestion")
        query = (
            EciticCompareRecordResultRef.select(
                EciticCompareResult,
                NewQuestion.fid,
                StdQuestion.fid.alias("std_fid"),
                NewQuestion.id.alias("qid"),
                StdQuestion.id.alias("std_qid"),
            )
            .join(EciticCompareResult)
            .join(EciticCompareRecord, on=(EciticCompareRecordResultRef.compare_record_id == EciticCompareRecord.id))
            .join(NewQuestion, on=(NewQuestion.id == EciticCompareRecord.qid))
            .join(StdQuestion, on=(StdQuestion.id == EciticCompareRecord.std_qid))
            .where(EciticCompareRecordResultRef.compare_record_id == compare_id)
        )
        ret = await pw_db.execute(query.dicts())
        return self.data({"items": list(ret)})


@plugin.route(r"/mold")
class MoldHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(AsyncPagination.web_args, location="query")
    async def get(self, page, size):
        names = get_config("citics.mold_list") or []
        query = NewMold.select()
        cond = NewMold.name.in_(names)
        data = await AsyncPagination(query.where(cond), page, size).data()
        return self.data(data)


@plugin.route(r"/projects/edit")
class TGProjectEditHandler(BaseHandler):
    args = {"project_name": fields.Str(required=True), "new_name": fields.Str()}

    @Auth("browse")
    @use_kwargs(args, location="query")
    async def put(self, project_name, new_name):
        if project := await NewFileProject.find_by_kwargs(name=new_name):
            raise CustomError(f"项目名称{new_name}已存在, {project.id=}")

        project = await NewFileProject.find_by_kwargs(name=project_name, visible=False)
        if not project:
            raise CustomError(_("can't find the project"))
        await project.update_(name=new_name)
        project_tree = await NewFileTree.find_by_id(project.rtree_id)
        await project_tree.update_(name=project.name)
        return self.data(project.to_dict())


@plugin.route(r"/push/records")
class PushHistoryHandler(BaseHandler):
    args = {
        "push_id": fields.Int(load_default=None),
        "project": fields.Str(load_default=None),
        "file": fields.Str(load_default=None),
        "task_type": fields.Int(load_default=None),
        "push_type": fields.Int(load_default=None),
        "status": fields.Int(load_default=None),
    }

    @Auth("browse")
    @use_kwargs(AsyncPagination.web_args, location="query")
    @use_kwargs(args, location="query")
    async def get(self, push_id, project, file, task_type, push_type, status, page, size):
        query = EciticPushRecord.select()
        query = query.join(NewFile, on=(NewFile.id == EciticPushRecord.fid))
        query = query.join(NewFileProject, on=(NewFileProject.id == NewFile.pid)).order_by(EciticPushRecord.id.desc())

        cond = EciticPushRecord.visible
        cond &= EciticPushRecord.task_type != EciticTgTaskType.TO_COUNT
        if push_id:
            cond &= EciticPushRecord.id == push_id
        if project:
            cond &= NewFileProject.name.ilike(f"%{project}%")
        if file:
            cond &= NewFile.name.ilike(f"%{file}%")
        if task_type:
            cond &= EciticPushRecord.task_type == task_type
        if push_type:
            cond &= EciticPushRecord.push_type == push_type
        if status is not None:
            cond &= EciticPushRecord.status == status
        data = await AsyncPagination(query.where(cond).dicts(), page, size).data()
        return self.data(data)


@plugin.route(r"/push/records/(?P<rid>\d+)")
class UDPushHistoriesHandler(BaseHandler):
    @Auth("browse")
    async def get(self, rid):
        record = await EciticPushRecord.find_by_id(rid)
        if not record:
            return self.error(_("Item Not Found"))
        return self.data(record.to_dict())

    @Auth("browse")
    async def put(self, rid):
        history = await EciticPushRecord.find_by_id(rid)
        if not history:
            return self.error(_("Item Not Found"))
        await pw_db.update(history, visible=False)
        return self.data({})

    @use_kwargs({"re_push": fields.Bool(required=True)}, location="json")
    @Auth("browse")
    async def post(self, rid, re_push):
        record = await EciticPushRecord.find_by_id(rid)
        if not record:
            return self.error(_("Item Not Found"))
        if re_push:
            file = await NewFile.find_by_id(record.fid)
            project = await NewFileProject.find_by_id(file.pid)

            try:
                new_records = await ecitic_tg_push(
                    project.name,
                    file,
                    self.current_user.id,
                    [record.data],
                    record.task_type,
                    EciticTgTriggerType.MANUAL,
                    record.compare_record,
                )

            except Exception as exp:
                logger.exception(exp)
                return self.error(_("Push Failed"))
            if new_records[0].status == 0:
                return self.error(_("Push Failed"))
        return self.data({})


@plugin.route(r"/model_statistics")
class ModelStatisticsHandler(BaseHandler):
    @Auth("browse")
    async def get(self):
        if not get_config("web.model_manage"):
            return False, self.error(message=_("don't support model_manage"), status_code=400)

        ret = []

        model_version_cte_fields = [
            NewModelVersion.id,
            NewModelVersion.mold,
            NewModelVersion.created_utc,
        ]

        mold_list = get_config("citics.mold_list")
        for mold_name in mold_list:
            mold = await NewMold.find_by_kwargs(name=mold_name)
            schema = Schema(mold.data)
            mold_fields = ["-".join(x[1:]) for x in schema.iter_schema_attr()]
            fids_group_by_field = {x: set() for x in mold_fields}  # 仅统计修改过的答案的fid

            cond = speedy.peewee_plus.orm.and_(
                NewModelVersion.enable == ModelEnableStatus.ENABLE.value, NewModelVersion.mold == mold.id
            )
            cte = NewModelVersion.select(*model_version_cte_fields).where(cond).cte("cte")

            file_query = (
                EciticFile.select(EciticFile.id.distinct())
                .join(NewQuestion, on=(NewQuestion.fid == EciticFile.id))
                .join(ModelAnswer, on=(NewQuestion.id == ModelAnswer.qid))
                .join(cte, on=(ModelAnswer.vid == cte.c.id))
                .with_cte(cte)
            )
            stat_file_ids = await pw_db.scalars(file_query)
            if not stat_file_ids:
                continue

            fields = (NewAnswerData.key, NewAnswerData.created_utc, NewAnswerData.record, NewQuestion.fid)
            query = (
                NewAnswerData.select(*fields)
                .join(NewQuestion, on=(NewQuestion.id == NewAnswerData.qid))
                .join(cte, on=(NewQuestion.mold == cte.c.mold))
                .where(
                    NewAnswerData.created_utc > cte.c.created_utc,
                    NewAnswerData.record.is_null(False),
                )
                .with_cte(cte)
            )

            answers = await pw_db.execute(query.namedtuples())

            for answer in answers:
                fids_group_by_field[get_key_path(answer.key)].add(answer.fid)

            result = []
            for name, fids in fids_group_by_field.items():
                result.append(
                    {
                        "name": name,
                        "rate": 1 - len(fids) / len(stat_file_ids),
                        "edited_fids": list(fids),
                    }
                )

            ret.append(
                {
                    "name": mold_name,
                    "data": {
                        "result": result,
                        "stat_fids": stat_file_ids,
                    },
                }
            )
        return self.data(ret)


@plugin.route(r"/projects/files")
class ProjectsFilesHandler(BaseHandler):
    param = {
        "pid": fields.Int(load_default=None),
        "fid": fields.Int(load_default=None),
        "name": fields.Str(load_default=None),
        "product_name": fields.Str(load_default=None),
        "product_type": fields.Str(load_default=None),
        "product_num": fields.Str(load_default=None),
        "only_stat": fields.Bool(load_default=False),
        "task_type": fields.Int(load_default=None),
    }

    @Auth("browse")
    @use_kwargs(AsyncPagination.web_args, location="query")
    @use_kwargs(param, location="query")
    async def get(self, pid, fid, name, product_name, product_type, product_num, only_stat, page, size, task_type):
        push_record_stmt = EciticPushRecord.select(
            EciticPushRecord.fid,
            EciticPushRecord.push_type,
            peewee.fn.Row_Number()
            .over(
                partition_by=[EciticPushRecord.fid],
                order_by=[EciticPushRecord.created_utc.desc()],
            )
            .alias("rank"),
        )
        if task_type is not None:
            cte = push_record_stmt.where(EciticPushRecord.task_type == task_type).cte("cte")
        else:
            cte = push_record_stmt.cte("cte")
        query = NewFile.select(
            NewFile.id,
            NewFile.name,
            NewFile.pdf_parse_status,
            NewFile.molds,
            NewFile.created_utc,
            EciticFileInfo,
            NewAdminUser.name.alias("user_name"),
            NewFileProject.meta.alias("project_meta"),
            NewFileProject.rtree_id,
            NewFileProject.id.alias("pid"),
            NewQuestion.ai_status,
            NewQuestion.id.alias("qid"),
            cte.c.push_type,
        )

        query = query.join(NewFileProject, on=(NewFile.pid == NewFileProject.id))
        query = query.join(EciticFileInfo, on=(NewFile.id == EciticFileInfo.file))
        query = query.join(NewAdminUser, on=(NewFile.uid == NewAdminUser.id))
        query = query.left_outer_join(cte, on=(NewFile.id == cte.c.fid))
        query = query.join(NewQuestion, on=(NewQuestion.fid == NewFile.id))
        cond = ~NewFileProject.visible
        if only_stat:
            cond &= speedy.peewee_plus.orm.and_(cte.c.rank == 1, EciticFileInfo.need_stat)
        else:
            cond &= speedy.peewee_plus.orm.or_(cte.c.rank == 1, cte.c.rank.is_null())

        if pid:
            cond &= NewFileProject.id == pid
        if fid:
            cond &= NewFile.id == fid
        if name:
            cond &= NewFile.name.contains(name)
        if product_name:
            cond &= NewFileProject.meta["product_name"].ilike(f"%{product_name}%")
        if product_type:
            cond &= NewFileProject.meta["product_type"] == product_type
        if product_num:
            cond &= NewFileProject.meta["product_num"].ilike(f"%{product_num}%")
        query = query.order_by(NewFile.id.desc()).where(cond).with_cte(cte)
        data = await AsyncPagination(query.dicts(), page, size).data()
        return self.data(data)


@plugin.route(r"/files/(?P<fid>\d+)/compare_records")
class FilesCompareRecordsHandler(BaseHandler):
    @Auth("browse")
    async def get(self, fid):
        question = await pw_db.first(NewQuestion.select().where(NewQuestion.fid == fid))
        if not question:
            return self.error("Question does not exist.", http.HTTPStatus.NOT_FOUND)
        compare_records = list(
            await pw_db.execute(
                EciticCompareRecord.select()
                .distinct(EciticCompareRecord.qid, EciticCompareRecord.std_qid)
                .where((EciticCompareRecord.qid == question.id) | (EciticCompareRecord.std_qid == question.id))
                .order_by(EciticCompareRecord.qid, EciticCompareRecord.std_qid, EciticCompareRecord.id.desc())
            )
        )
        question_ids = list({record.qid for record in compare_records} | {record.std_qid for record in compare_records})
        file_info = {
            file["qid"]: file
            for file in await pw_db.execute(
                EciticFile.select(EciticFile.id, EciticFile.name, EciticFileInfo.version, NewQuestion.id.alias("qid"))
                .join(EciticFileInfo)
                .join(NewQuestion, on=(EciticFile.id == NewQuestion.fid))
                .where(NewQuestion.id.in_(question_ids))
                .dicts()
            )
        }
        external_source = {
            record["compare_record"]: record
            for record in await pw_db.execute(
                EciticPushRecord.select(EciticPushRecord.compare_record, EciticPushRecord.push_type)
                .distinct(EciticPushRecord.compare_record)
                .where(
                    EciticPushRecord.compare_record.in_([record.id for record in compare_records]),
                    EciticPushRecord.task_type == EciticTgTaskType.COMPARE,
                )
                .order_by(EciticPushRecord.compare_record, EciticPushRecord.id.desc())
                .dicts()
            )
        }
        data = []
        for record in compare_records:
            data.append(
                {
                    "compare_id": record.id,
                    "std_qid": record.std_qid,
                    "qid": record.qid,
                    "external_source": record.external_source,
                    "push_type": external_source.get(record.id, {}).get("push_type"),
                    "std_file_info": file_info.get(record.std_qid),
                    "diff_file_info": file_info.get(record.qid),
                }
            )

        return self.data(data)


@plugin.route(r"/projects/(?P<pid>\d+)/pushed/fields")
class ProjectsPushedHandler(BaseHandler):
    @Auth("browse")
    async def get(self, pid):
        user = self.current_user
        if user.is_admin:
            cond = speedy.peewee_plus.orm.TRUE
        else:
            cond = EciticFileInfo.group_name.in_(user.data.get("group_name", "").split(","))
        subquery = (
            EciticPushRecord.select(peewee.Cast(EciticPushRecord.data["template_id"], "INTEGER"))
            .join(NewFile, on=(EciticPushRecord.fid == NewFile.id))
            .join(EciticFileInfo, on=(EciticPushRecord.fid == EciticFileInfo.file))
            .where(NewFile.pid == pid, cond)
            .distinct()
        )
        query = EciticTemplate.select(EciticTemplate.fields).where(EciticTemplate.id.in_(subquery))
        template_fields = await pw_db.scalars(query)
        sorted_fields = sorted(set(chain(*template_fields)))
        return self.data({"template_fields": sorted_fields})


@plugin.route(r"/projects/(?P<pid>\d+)/templates/field")
class TemplatesHandler(BaseHandler):
    param = {
        "field": fields.Str(required=True),
    }

    @Auth("browse")
    @use_kwargs(param, location="query")
    async def get(self, pid, field):
        template_ids = await pw_db.scalars(
            EciticTemplate.select(EciticTemplate.id).where(EciticTemplate.fields.contains(field))
        )
        if not template_ids:
            raise CustomError(_("No matching templates"), resp_status_code=404)
        user = self.current_user
        if user.is_admin:
            cond = speedy.peewee_plus.orm.TRUE
        else:
            cond = EciticFileInfo.group_name.in_(user.data.get("group_name", "").split(","))
        record_cte = EciticPushRecord.select(
            EciticPushRecord.fid,
            peewee.fn.Row_Number()
            .over(
                partition_by=[EciticPushRecord.fid],
                order_by=[EciticPushRecord.id.desc()],
            )
            .alias("rank"),
        ).cte("cte")
        query = (
            NewQuestion.select(NewQuestion.id, NewQuestion.mold, NewQuestion.fid)
            .join(NewFile, on=(NewFile.id == NewQuestion.fid))
            .join(EciticFileInfo, on=(EciticFileInfo.file == NewQuestion.fid))
            .order_by(EciticFileInfo.version.desc(nulls="LAST"), EciticFileInfo.id.desc())
            .left_outer_join(record_cte, on=(NewQuestion.fid == record_cte.c.fid))
            .where(
                NewFile.pid == pid,
                record_cte.c.rank == 1,
                cond,
                EciticFileInfo.templates.contains_any(template_ids),
                EciticFileInfo.need_stat,
            )
            .with_cte(record_cte)
        )
        question = await pw_db.first(query)
        merge_answers = []
        version = None
        if question:
            answer, mold = await get_master_question_answer(question)
            if not is_empty_answer(answer, "userAnswer"):
                merge_answers.append(answer)
                file_info = await pw_db.first(EciticFileInfo.select().where(EciticFileInfo.file == question.fid))
                version = file_info.version
        field_answers = set()
        for answer in merge_answers:
            answers = SimpleJSONConverter(answer).convert()
            for key, conv_answer in answers.items():
                if "-".join(split_path(key)) == field and conv_answer:
                    if isinstance(conv_answer, list):
                        for ans in conv_answer:
                            field_answers.add(ans["拆分"] or ans["原文"])
                    else:
                        field_answers.add(conv_answer)
                    break
        ret = {"field_answers": sorted(field_answers), "version": version}
        return self.data(ret)


@plugin.route(r"/files")
class PageSearchHandler(BaseHandler):
    args = {
        "project_id": fields.Int(required=True),
        "filename": fields.String(load_default=""),
        "fileid": fields.Int(load_default=0),
    }

    @Auth("browse")
    @use_kwargs(args, location="query")
    @use_kwargs(AsyncPagination.web_args, location="query")
    async def get(self, project_id, filename, fileid, page, size):
        if not len([x for x in (filename, fileid) if x]) == 1:
            raise CustomError(_("The input search criteria is invalid"))

        if filename:
            filename = filename.replace("=", "==").replace("%", "=%").replace("_", "=_")

        query = (
            EciticFile.select(
                EciticFile,
                EciticFileInfo,
            )
            .join(EciticFileInfo)
            .join(NewFileProject, on=(EciticFile.pid == NewFileProject.id))
        )

        cond = ~NewFileProject.visible

        if project_id:
            cond &= NewFileProject.id == project_id
        if fileid:
            cond &= EciticFile.id == fileid
        if filename:
            cond &= EciticFile.name.contains(filename)
        query = query.order_by(EciticFile.id.desc()).where(cond)
        data = await AsyncPagination(query.dicts(), page, size).data()
        return self.data(data)


@plugin.route(r"/trees/(\d+)")
class TreeHandler(PermCheckHandler):
    @Auth("browse")
    @use_kwargs(AsyncPagination.web_args, location="query")
    async def get(self, tid, page, size):
        tree = await NewFileTree.find_by_id(tid)
        if not tree:
            return self.error(_("not found tree"))
        res = tree.to_dict()
        trees = await NewFileTree.list_by_tree(int(tid))
        start = (page - 1) * size
        end = page * size
        res_tree = []
        for sub_tree in trees[start:end]:
            user_name = sub_tree.user.name if hasattr(sub_tree, "user") else None  # NOTE: Users may be deleted
            sub_tree = sub_tree.to_dict()
            sub_tree["user_name"] = user_name
            res_tree.append(sub_tree)
        res["trees"] = res_tree

        all_files_count = await pw_db.count(NewFile.select().where(NewFile.tree_id == tid, NewFile.deleted_utc == 0))

        need_file_count = size - len(res["trees"])
        if need_file_count:
            file_end = end - len(trees)
            file_offset = max(file_end - size + len(res["trees"]), 0)
            res["files"] = await ecitic_get_files_and_questions_by_tree(tid, file_offset, need_file_count)
        else:
            res["files"] = []

        res["page"] = page
        res["total"] = all_files_count + len(trees)
        res["crumbs"] = await get_crumbs(tree.id)

        project = await NewFileProject.find_by_id(res["pid"])
        res["project_public"] = project.public

        return self.data(res)


@plugin.route(r"/compare_records")
class CompareRecordsHandler(PermCheckHandler):
    args = {
        "rid": fields.Int(load_default=0, data_key="id"),
        "fid": fields.Int(load_default=0),
        "start": fields.Int(load_default=0, validate=validate_timestamp),
        "end": fields.Int(load_default=0, validate=validate_timestamp),
    }

    @Auth("browse")
    @use_kwargs(args, location="query")
    async def get(self, rid, fid, start, end):
        StdQuestion = NewQuestion.alias()
        only_fields = [EciticCompareRecord.id, NewQuestion.fid.alias("fid"), StdQuestion.fid.alias("std_fid")]

        query = (
            EciticCompareRecord.select(*only_fields)
            .join(NewQuestion, on=(EciticCompareRecord.qid == NewQuestion.id))
            .join(StdQuestion, on=(EciticCompareRecord.std_qid == StdQuestion.id))
        )
        cond = speedy.peewee_plus.orm.TRUE

        if rid:
            if fid or start or end:
                raise CustomError(
                    _("The parameter 'id' and other parameters cannot be passed simultaneously"),
                    resp_status_code=http.HTTPStatus.BAD_REQUEST,
                )
            cond &= EciticCompareRecord.id == rid
            data = await pw_db.first(query.where(cond).dicts())
            if not data:
                return self.error(_("Item not found"), http.HTTPStatus.NOT_FOUND)
            return self.data({"items": [data]})

        if fid:
            question = await pw_db.first(NewQuestion.select().where(NewQuestion.fid == fid))
            if not question:
                return self.error(_("The question does not exists."), http.HTTPStatus.NOT_FOUND)
            cond &= (EciticCompareRecord.qid == question.id) | (EciticCompareRecord.std_qid == question.id)
        if start:
            cond &= EciticCompareRecord.created_utc >= start
        if end:
            cond &= EciticCompareRecord.created_utc <= end

        items = list(await pw_db.execute(query.where(cond).dicts()))
        return self.data({"items": items})


@plugin.route(r"/files/(\d+)/audit/results")
class AuditResultHandler(PermCheckHandler):
    @Auth("inspect")
    async def get(self, fid):
        only_fields = (
            NewAuditResult.fid,
            NewAuditResult.qid,
            NewAuditResult.name,
            NewAuditResult.schema_id,
            NewAuditResult.suggestion,
            NewAuditResult.reasons,
            NewAuditResult.schema_results,
            NewAuditResult.is_compliance,
        )
        query = NewAuditResult.select(*only_fields).where(
            NewAuditResult.fid == fid, NewAuditResult.answer_type == AuditAnswerType.final_answer
        )
        items = await pw_db.execute(query.dicts())
        return self.data({"items": list(items)})


class AdditionalAnswerSchema(MMSchema):
    data = fields.Dict(required=True)

    @validates("data")
    def validate_data(self, data: dict, data_key: str) -> bool:
        for value in data.values():
            if not isinstance(value, list):
                logger.error(f"Invalid data: {value}")
                raise MMValidationError("invalid data structure")

            if all(isinstance(x, str) for x in value):
                continue
            elif all(isinstance(x, dict) for x in value):
                for item in value:
                    self.validate_data(item, data_key)
            else:
                logger.error(f"Invalid data: {value}")
                raise MMValidationError("invalid data structure")
        return True


@plugin.route(r"/files/(\d+)/additional_answer")
class AdditionalAnswerHandler(PermCheckHandler):
    @Auth("browse")
    @use_kwargs(AdditionalAnswerSchema, location="json")
    async def post(self, fid, data):
        file = await NewFile.find_by_id(fid)
        if not file:
            logger.error(f"File not found for {fid}.")
            return self.error(_("Item Not Found"), status_code=http.HTTPStatus.NOT_FOUND)
        question = await NewQuestion.find_by_kwargs(fid=fid)
        if not question:
            logger.error(f"Question not found for {fid}.")
            return self.error(_("Item Not Found"), status_code=http.HTTPStatus.NOT_FOUND)
        async with pw_db.atomic():
            await pw_db.execute(
                NewSpecialAnswer.update(deleted_utc=generate_timestamp()).where(
                    NewSpecialAnswer.qid == question.id,
                    NewSpecialAnswer.answer_type == SpecialAnswerType.JSON_ANSWER,
                    NewSpecialAnswer.deleted_utc == 0,
                )
            )
            await NewSpecialAnswer.create(qid=question.id, answer_type=SpecialAnswerType.JSON_ANSWER, data=data)
            await pw_db.execute(
                EciticFileInfo.update(external_source=EciticExternalSource.GANYI).where(EciticFileInfo.file == file.id)
            )

        return self.data({})

    @Auth("browse")
    async def get(self, fid):
        file = await NewFile.find_by_id(fid)
        if not file:
            logger.error(f"File not found for {fid}.")
            return self.error(_("Item Not Found"), status_code=http.HTTPStatus.NOT_FOUND)
        question = await NewQuestion.find_by_kwargs(fid=fid)
        if not question:
            logger.error(f"Question not found for {fid}.")
            return self.error(_("Item Not Found"), status_code=http.HTTPStatus.NOT_FOUND)

        ret = await EciticExternalAnswerConverter.convert(question)

        return self.data(ret)
