# CYC: build-with-nuitka
import asyncio
import http
import json
import logging
import os
from json import JSONDecodeError
from pathlib import PurePath

import peewee
from pdfparser.imgtools.ocraug.faded_h_stroke import defaultdict
from pydantic import ValidationError
from speedy.peewee_plus.orm import or_
from tornado.httputil import HTTPFile
from webargs import fields

from remarkable.base_handler import Auth, BaseHandler, PermCheckHandler
from remarkable.common import field_validate
from remarkable.common.apispec_decorators import use_args, use_kwargs
from remarkable.common.cmfchina import CmfChinaSysFromType
from remarkable.common.constants import (
    CommonStatus,
    HistoryAction,
    MoldType,
    PDFParseStatus,
    PublicStatus,
    RuleReviewStatus,
    TimeType,
)
from remarkable.common.enums import ReviewedType, TaskType
from remarkable.common.exceptions import CGSException, CustomError
from remarkable.common.util import custom_decode, run_singleton_task
from remarkable.config import get_config
from remarkable.data.services.training_data_service import mold_export_task
from remarkable.db import pw_db
from remarkable.models.cmf_china import (
    CmfChinaEmail,
    CmfFiledFileInfo,
    CmfFileReviewed,
    CmfModel,
    CmfModelFileRef,
    CmfMoldFieldRef,
    CmfMoldModelRef,
    CmfUserCheckFields,
)
from remarkable.models.new_file import NewFile
from remarkable.models.new_group import CMFGroup, CMFGroupRef, CMFUserGroupRef
from remarkable.models.query_helper import PaginationSchema
from remarkable.plugins import HTTPFileValidator, Plugin
from remarkable.plugins.cmfchina.cmf_tree import CmfFileTreeService
from remarkable.plugins.cmfchina.schemas import (
    EditEmailSchema,
    EditGroupSchema,
    EmailSchema,
    ExportSchema,
    FiledFileSearchSchema,
    FiledVerifySchema,
    FileSearchSchema,
    GroupSchema,
    ModelAccuracySchema,
    ModelCallSchema,
    ModelFileSearchSchema,
    ModelManSchema,
    ModelPostSchema,
    NameSearchSchema,
    PanoramaSearchSchema,
    ProjectSearch,
    RulesSchema,
    SchemaSearchSchema,
    SearchEmailSchema,
    SearchSchema,
    TreeSchema,
)
from remarkable.plugins.cmfchina.tasks import (
    predict_answer_by_interface_task,
    reset_filed_file_task,
    save_audit_result_statistic,
)
from remarkable.plugins.fileapi.common import NoneOfWrapper
from remarkable.plugins.fileapi.upload_zip_file_handler import UploadZipFileBaseHandler
from remarkable.predictor.mold_schema import MoldSchema
from remarkable.pw_models.audit_rule import NewAuditResult, NewAuditRule
from remarkable.pw_models.model import MoldWithFK, NewFileProject, NewFileTree, NewHistory, NewMold, NewMoldField
from remarkable.pw_models.question import NewQuestion
from remarkable.schema.cgs.rules import RuleSchema, rules_schema
from remarkable.service.cmfchina.cmf_group import CMFGroupService
from remarkable.service.cmfchina.common import (
    CMF_CHINA_FILED_FILE_PROJECT_NAME,
    CMF_CHINA_MODEL_VERIFY_PROJECT_NAME,
    CMF_CHINA_VERIFY_FILED_PROJECT_NAME,
)
from remarkable.service.cmfchina.export_mold import CmfImportMoldModel, ExportMoldConvert
from remarkable.service.cmfchina.filed_file_service import CmfFiledFileService
from remarkable.service.cmfchina.imap_email_receiver import IMAPEmailReceiver
from remarkable.service.cmfchina.service import (
    CmfChinaService,
)
from remarkable.service.cmfchina.validator import (
    CmfPostFileValidator,
    CmfZipFileValidator,
    validate_file_length,
    validate_zip_file_length,
)
from remarkable.service.new_file import NewFileService
from remarkable.service.new_file_project import NewFileProjectService
from remarkable.service.new_file_tree import NewFileTreeService
from remarkable.service.new_mold import NewMoldService
from remarkable.service.new_question import NewQuestionService
from remarkable.worker.tasks import process_extract_answer_by_studio, process_file, process_file_for_excel

plugin = Plugin(PurePath(__file__).parent.name)
logger = logging.getLogger(__name__)


project_args = {
    "name": fields.String(required=True, validate=field_validate.Length(min=1)),
    "default_molds": fields.List(fields.Int(), load_default=[]),
    "group_ids": fields.List(fields.Int(), load_default=[]),
    "is_public": fields.Int(load_default=PublicStatus.PUBLIC.value),
}

mold_data_schema = fields.Nested(
    {
        "schemas": fields.List(
            fields.Dict(validate=lambda x: isinstance(x.get("name"), str) and isinstance(x.get("schema"), dict))
        ),
        "schema_types": fields.List(fields.Dict(), load_default=[]),
    }
)


class CMFChinaHandler(BaseHandler):
    def _handle_request_exception(self, e: BaseException) -> None:
        if isinstance(e, CGSException):
            self.error(message=e.message, errors=e.to_dict())
            self.finish()
            return None
        return super()._handle_request_exception(e)


@plugin.route(r"/projects")
class ProjectsHandler(CMFChinaHandler):
    @Auth("browse")
    @use_kwargs(ProjectSearch, location="query")
    async def get(self, name, iid, user_name, start_at, end_at, mid, order_by, page, size):
        file_tree_ids = None
        if not self.current_user.is_admin:
            file_tree_ids = await CMFGroupService.get_user_group_file_trees(self.current_user.id)
            items = await NewFileTreeService.get_all_parent_trees(file_tree_ids)
            file_tree_ids = [item.id for item in items]
        data = await CmfChinaService.get_pagination_projects(
            name, iid, user_name, mid, start_at, end_at, order_by, page, size, file_tree_ids=file_tree_ids
        )
        return self.data(data)

    @Auth("browse")
    @use_kwargs(project_args, location="json")
    async def post(self, name, default_molds, group_ids, is_public):
        exists = await NewFileProject.find_by_kwargs(name=name)
        if exists:
            raise CustomError(_("project name is existed"), resp_status_code=http.HTTPStatus.BAD_REQUEST)

        groups = await CMFGroupService.get_groups(group_ids)
        async with pw_db.atomic():
            project = await NewFileProjectService.create(
                name, default_molds, uid=self.current_user.id, is_public=is_public
            )

            for group in groups:
                file_tree_ids = set(group["file_tree_ids"] + [project.rtree_id])
                await CMFGroupService.update(group["id"], file_tree_ids=list(file_tree_ids))

            await NewHistory.save_operation_history(
                project.id,
                self.current_user.id,
                HistoryAction.CREATE_PROJECT.value,
                self.current_user.name,
                meta=project.to_dict(),
            )

        self.data(project.to_dict())


@plugin.route(r"/projects/(\d+)")
class ProjectHandler(PermCheckHandler):
    put_schema = {
        "name": fields.String(required=True, validate=field_validate.Length(min=1)),
        "default_molds": fields.List(fields.Int(), load_default=[]),
        "group_ids": fields.List(fields.Int()),
    }

    @Auth(["browse"])
    async def get(self, pid):
        project = await NewFileProject.find_by_id(pid)
        if not project:
            return self.error(_("not found project"), resp_status_code=http.HTTPStatus.NOT_FOUND)
        await self.check_project_permission(pid, project=project)

        group_ids = (
            None if self.current_user.is_admin else await CMFUserGroupRef.get_user_group_ids(self.current_user.id)
        )
        groups = await CMFGroupService.get_file_tree_groups(project.rtree_id, group_ids)
        data = project.to_dict()
        data["groups"] = [x.to_dict() for x in groups]

        if not self.current_user.is_admin:
            mold_ids = await CMFGroupService.get_user_group_molds(self.current_user.id)
            data["default_molds"] = [x for x in data["default_molds"] if x in mold_ids]

        return self.data(data)

    @Auth(["browse"])
    @use_args(put_schema, location="json")
    async def put(self, pid, params):
        project = await NewFileProject.find_by_id(pid)
        if not project:
            raise CustomError(_("not found project"))
        await self.check_project_permission(pid, project=project, mode="write")

        group_ids = params.pop("group_ids")
        user_group_ids = None
        if not self.current_user.is_admin:
            user_group_ids = await CMFUserGroupRef.get_user_group_ids(self.current_user.id)
            mold_ids = await CMFGroupService.get_user_group_molds(self.current_user.id)
            not_accessible_mold_ids = [x for x in project.default_molds if x not in mold_ids]
            params["default_molds"] = params["default_molds"] + not_accessible_mold_ids

        exist_file_tree_groups = await CMFGroupService.get_file_tree_groups(project.rtree_id, user_group_ids)
        exist_file_tree_group_ids = [x.id for x in exist_file_tree_groups]
        async with pw_db.atomic():
            project = await NewFileProjectService.update(project, params, self.process_files)
            await CMFGroupRef.update_refs_for_group(exist_file_tree_group_ids, group_ids, file_tree_id=project.rtree_id)

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


@plugin.route(r"/projects/(\d+)/files")
class ProjectFileSearchHandler(CMFChinaHandler):
    @Auth("browse")
    @use_kwargs(FileSearchSchema, location="query")
    async def get(
        self,
        pid,
        name,
        iid,
        user_name,
        start_at,
        end_at,
        order_by,
        _type,
        pdf_parse_status,
        ai_status,
        search_mid,
        page,
        size,
    ):
        if not await NewFileProject.get_by_id(pid):
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        tree_ids, mold_ids = None, None
        if not self.current_user.is_admin:
            tree_ids = await CMFGroupService.get_user_group_file_trees(self.current_user.id)
            mold_ids = await CMFGroupService.get_user_group_molds(self.current_user.id)
            if search_mid and search_mid not in mold_ids:
                return self.data({"page": page, "size": size, "total": 0, "items": []})
        data = await CmfChinaService.get_pagination_pro_files(
            name,
            iid,
            user_name,
            start_at,
            end_at,
            order_by,
            _type,
            pdf_parse_status,
            ai_status,
            pid,
            page,
            size,
            tree_ids,
            mold_ids,
            search_mid,
        )
        return self.data(data)


@plugin.route(r"/trees/(\d+)")
class TreeHandler(PermCheckHandler):
    tree_param = {
        "name": fields.Str(validate=NoneOfWrapper([""])),  # 禁止空的项目名
        "default_molds": fields.List(fields.Int()),
        "group_ids": fields.List(fields.Int()),
    }

    @Auth("browse")
    @use_kwargs(TreeSchema, location="query")
    async def get(self, tid, order_by, page, size, search_fid, search_mid):
        tid = int(tid)
        if not (tree := await NewFileTree.get_by_id(tid)):
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        permissions_tree_ids, permissions_mold_ids = None, None
        if not self.current_user.is_admin:
            permissions_tree_ids = await CMFGroupService.get_user_group_file_trees(self.current_user.id)
            permissions_mold_ids = await CMFGroupService.get_user_group_molds(self.current_user.id)
            if search_mid and search_mid not in permissions_mold_ids:
                return self.data({"page": page, "size": size, "total": 0, "items": []})
        res = await CmfFileTreeService.get_trees(
            tree,
            order_by,
            page,
            size,
            permissions_tree_ids=permissions_tree_ids,
            permissions_mold_ids=permissions_mold_ids,
            search_fid=search_fid,
            search_mid=search_mid,
        )
        return self.data(res)

    @Auth("browse")
    @use_args(tree_param, location="json")
    async def put(self, tid, params):
        tree = await NewFileTree.find_by_id(tid)
        if not tree:
            raise CustomError(_("not found tree"))
        await self.check_tree_permission(tid, tree=tree, mode="write")

        group_ids = params.pop("group_ids")
        user_group_ids = None
        if not self.current_user.is_admin:
            user_group_ids = await CMFUserGroupRef.get_user_group_ids(self.current_user.id)
            mold_ids = await CMFGroupService.get_user_group_molds(self.current_user.id)
            not_accessible_mold_ids = [x for x in tree.default_molds if x not in mold_ids]
            params["default_molds"] = params["default_molds"] + not_accessible_mold_ids

        exist_file_tree_groups = await CMFGroupService.get_file_tree_groups(tree.id, user_group_ids)
        exist_file_tree_group_ids = [x.id for x in exist_file_tree_groups]
        async with pw_db.atomic():
            tree = await NewFileTreeService.update(tree, params)
            await CMFGroupRef.update_refs_for_group(exist_file_tree_group_ids, group_ids, file_tree_id=tree.id)

            await NewHistory.save_operation_history(
                tree.id,
                self.current_user.id,
                HistoryAction.MODIFY_TREE.value,
                self.current_user.name,
                meta=tree.to_dict(),
            )

        return self.data(tree.to_dict())


@plugin.route(r"/trees/(\d+)/info")
class TreeInfoHandler(BaseHandler):
    @Auth("browse")
    async def get(
        self,
        tid,
    ):
        tid = int(tid)
        if not (tree := await NewFileTree.get_by_id(tid)):
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)

        group_ids = (
            None if self.current_user.is_admin else await CMFUserGroupRef.get_user_group_ids(self.current_user.id)
        )
        groups = await CMFGroupService.get_file_tree_groups(tree.id, group_ids)
        data = tree.to_dict()
        data["groups"] = [x.to_dict() for x in groups]
        if not self.current_user.is_admin:
            mold_ids = await CMFGroupService.get_user_group_molds(self.current_user.id)
            data["default_molds"] = [x for x in data["default_molds"] if x in mold_ids]

        return self.data(data)


@plugin.route(r"/trees/(\d+)/file")
class UploadFileHandler(CMFChinaHandler):
    @Auth("browse")
    @use_kwargs(
        {
            "sysfrom": fields.Str(
                load_default=CmfChinaSysFromType.LOCAL.value,
                validate=field_validate.OneOf(CmfChinaSysFromType.member_values()),
            ),
        },
        location="form",
    )
    @use_kwargs(
        {
            "files": fields.List(
                fields.Raw(required=True, validate=CmfPostFileValidator.check),
                validate=validate_file_length,
                data_key="file",
            )
        },
        location="files",
    )
    async def post(self, tid: int, sysfrom: str, files: list[HTTPFile]):
        if not (tree := await NewFileTree.get_by_id(tid)):
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        if not (project := await NewFileProject.find_by_id(tree.pid)):
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        file = await NewFileService.create_file(
            name=files[0].filename,
            body=files[0].body,
            pid=project.id,
            tree_id=tid,
            uid=self.current_user.id,
            task_type=TaskType.AUDIT.value,
            sysfrom=sysfrom,
            molds=tree.default_molds or [],
        )
        await process_file_for_excel(file)
        return self.data(file.to_dict(recurse=False))


@plugin.route(r"/trees/(\d+)/sse")
class UploadFileSSEHandler(UploadZipFileBaseHandler):
    @Auth("browse")
    @use_kwargs(
        {
            "event_id": fields.Str(load_default=None),
            "sysfrom": fields.Str(
                load_default=CmfChinaSysFromType.LOCAL.value,
                validate=field_validate.OneOf(CmfChinaSysFromType.member_values()),
            ),
        },
        location="form",
    )
    @use_kwargs(
        {
            "files": fields.List(
                fields.Raw(validate=CmfZipFileValidator.check),
                validate=validate_zip_file_length,
                data_key="file",
                load_default=[],
            )
        },
        location="files",
    )
    async def post(self, tid: str, event_id: str | None, sysfrom: str, files: list[HTTPFile]):
        tid = int(tid)
        tree = await NewFileTree.find_by_id(tid)
        if not tree:
            return self.error(_("not found tree"), status_code=http.HTTPStatus.NOT_FOUND)
        file = files[0] if files else None
        await self.upload_compressed_file(
            tid=tree.id, task_type=TaskType.AUDIT.value, event_id=event_id, file=file, sysfrom=sysfrom
        )


@plugin.route(r"/schemas")
class SchemaSearchHandler(CMFChinaHandler):
    # 获取所有场景
    @Auth("browse")
    @use_kwargs(SchemaSearchSchema, location="query")
    async def get(self, name, iid, user_name, start_at, end_at, order_by, _type, alias, page, size):
        mold_ids = None
        if not self.current_user.is_admin:
            mold_ids = await CMFGroupService.get_user_group_molds(self.current_user.id)
        data = await CmfChinaService.get_pagination_schema(
            name, iid, user_name, start_at, end_at, order_by, _type, alias, page, size, mold_ids=mold_ids
        )
        return self.data(data)


@plugin.route(r"/schemas/(\d+)/models")
class SchemaModelHandler(CMFChinaHandler):
    # 获取场景所有模型
    @Auth("browse")
    @use_kwargs(PaginationSchema, location="query")
    async def get(self, mold_id, page, size):
        if not (mold := await MoldWithFK.find_by_id(mold_id)):
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        data = await CmfChinaService.get_pagination_mold_models(mold, page, size)
        return self.data(data)


@plugin.route(r"/schemas/(\d+)/models/(\d+)")
class SchemaModelCorrelationHandler(CMFChinaHandler):
    # 场景-模型 关联
    @Auth("browse")
    @use_kwargs({"relation": fields.Bool(load_default=True)}, location="json")
    async def put(self, mold_id, model_id, relation):
        if not (mold := await MoldWithFK.find_by_id(mold_id)):
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        if not (model := await CmfModel.find_by_id(model_id)):
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        async with pw_db.atomic():
            if relation:
                try:
                    await pw_db.create(CmfMoldModelRef, mold=mold, model=model)
                except peewee.IntegrityError:
                    return self.error("模型已关联，请勿重复关联", status_code=http.HTTPStatus.BAD_REQUEST)
            else:
                if mold_model_ref := await CmfMoldModelRef.find_by_kwargs(mold=mold, model=model):
                    await pw_db.delete(mold_model_ref)

    @Auth("browse")
    @use_kwargs(ModelManSchema, location="query")
    async def post(self, mold_id, model_id, enable, preset):
        # 启用模型 + 停用模型
        mold_model_ref = await pw_db.prefetch_one(
            CmfMoldModelRef.select().where(CmfMoldModelRef.model_id == model_id, CmfMoldModelRef.mold_id == mold_id),
            MoldWithFK.select(),
            CmfModel.select(),
        )
        if not mold_model_ref:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        if enable:
            # 启用
            await mold_model_ref.enable_model()
            if preset:
                get_lock, lock = await CmfChinaService.rerun_preset_answers(mold_id, model_id)
                if not get_lock:
                    return self.error(_("The model is predicting, please try again later"))
        else:
            # 停用
            mold_model_ref.enable = CommonStatus.INVALID.value
            await pw_db.update(mold_model_ref)
        return self.data({})


@plugin.route(r"/models")
class ModelHandler(CMFChinaHandler):
    @Auth("browse")
    @use_kwargs(SearchSchema, location="query")
    async def get(self, name, iid, user_name, start_at, end_at, order_by, page, size):
        data = await CmfChinaService.get_pagination_models(name, iid, user_name, start_at, end_at, order_by, page, size)
        return self.data(data)

    @Auth("browse")
    @use_kwargs(ModelPostSchema, location="json")
    async def post(self, name, address, intro, usage):
        try:
            model = await CmfModel.create(
                name=name, address=address, intro=intro, usage=usage, user=self.current_user.id
            )
            return self.data(model.to_dict(recurse=False))
        except peewee.IntegrityError as exp:
            logger.exception(str(exp))
            return self.error("名称和地址已存在,请勿重复创建", status_code=http.HTTPStatus.BAD_REQUEST)


@plugin.route(r"/models/(\d+)")
class ModelManHandler(CMFChinaHandler):
    @Auth("browse")
    @use_kwargs(ModelPostSchema, location="json")
    async def put(self, model_id, name, address, intro, usage):
        if not (model := await CmfModel.find_by_id(model_id)):
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        model.name = name
        model.address = address
        model.intro = intro
        model.usage = usage
        async with pw_db.atomic():
            try:
                await pw_db.update(model, only=["name", "address", "intro", "usage"])
            except peewee.IntegrityError as exp:
                logger.exception(str(exp))
                return self.error("名称或地址已存在", status_code=http.HTTPStatus.BAD_REQUEST)

        return self.data({})

    @Auth("browse")
    async def delete(self, model_id):
        if not (model := await CmfModel.find_by_id(model_id)):
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        mold_names = await pw_db.scalars(
            MoldWithFK.select(MoldWithFK.name).where(
                peewee.fn.EXISTS(
                    CmfMoldModelRef.select().where(
                        CmfMoldModelRef.model == model, CmfMoldModelRef.enable, CmfMoldModelRef.mold == MoldWithFK.id
                    )
                )
            )
        )
        if mold_names:
            return self.error(
                f"该模型已关联 {','.join(mold_names)} 场景并启用，请先停用此模型",
                status_code=http.HTTPStatus.BAD_REQUEST,
            )
        model_files = await pw_db.execute(CmfModelFileRef.select().where(CmfModelFileRef.model == model))
        files = []
        if model_files:
            fids = [model_file.fid for model_file in model_files]
            files = await pw_db.execute(NewFile.select().where(NewFile.id.in_(fids)))
        async with pw_db.atomic():
            for file in files:
                await file.soft_delete()
            await pw_db.execute(CmfModelFileRef.delete().where(CmfModelFileRef.model == model))
            await pw_db.execute(CmfMoldModelRef.delete().where(CmfMoldModelRef.model == model))
            await pw_db.delete(model)
        return self.data({})


@plugin.route(r"/models/(\d+)/files")
class ModelFileHandler(CMFChinaHandler):
    @Auth("browse")
    @use_kwargs({"mold_id": fields.Int(load_default=None)}, location="form")
    @use_kwargs({"file": fields.Raw(required=True, validate=CmfPostFileValidator.check)}, location="files")
    async def post(self, model_id: int, mold_id: int | None, file: HTTPFile | None):
        model = await CmfModel.find_by_id(model_id)
        if not model:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        mold_ids = await CmfChinaService.get_mold_id_from_model(model)
        if mold_id and mold_id not in mold_ids:
            return self.error("场景不存在", status_code=http.HTTPStatus.NOT_FOUND)
        mold_ids = [mold_id] if mold_id else []
        async with pw_db.atomic():
            project = await NewFileProjectService.create(
                name=CMF_CHINA_MODEL_VERIFY_PROJECT_NAME, uid=self.current_user.id, visible=False
            )
            file_tree = await NewFileTree.find_by_id(project.rtree_id)
            new_file = await NewFileService.create_file(
                name=file.filename,
                body=file.body,
                pid=project.id,
                tree_id=file_tree.id,
                uid=self.current_user.id,
                task_type=TaskType.AUDIT.value,
                molds=mold_ids or [],
            )
            await pw_db.create(CmfModelFileRef, model_id=model_id, fid=new_file.id)
            data = [{"id": new_file.id, "filename": file.filename}]

        # 调用外部接口直接预测
        if new_file.is_pdf and not mold_ids:
            predict_answer_by_interface_task.delay(new_file.id)
        await process_file(new_file)
        return self.data(data)

    @Auth("browse")
    @use_kwargs(ModelFileSearchSchema, location="query")
    async def get(self, model_id, mold_id, page, size):
        # 获取默认工程
        if not (
            pid := await pw_db.scalar(
                NewFileProject.select(NewFileProject.id).where(
                    NewFileProject.name == CMF_CHINA_MODEL_VERIFY_PROJECT_NAME,
                    ~NewFileProject.visible,
                )
            )
        ):
            # 没有时创建
            project = await NewFileProjectService.create(
                name=CMF_CHINA_MODEL_VERIFY_PROJECT_NAME, uid=self.current_user.id, visible=False
            )
            pid = project.id

        data = await CmfChinaService.get_pagination_models_files(model_id, mold_id, pid, page, size)
        return self.data(data)


@plugin.route(r"/models/(\d+)/files/(\d+)")
class ModelFileDeleteHandler(CMFChinaHandler):
    # 删除模型验证文件
    @Auth("browse")
    async def delete(self, model_id, fid):
        if not (model := await CmfModel.find_by_id(model_id)):
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        if not (file := await NewFile.find_by_id(fid)):
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        async with pw_db.atomic():
            await file.soft_delete()
            await pw_db.execute(
                CmfModelFileRef.delete().where(CmfModelFileRef.fid == fid, CmfModelFileRef.model == model)
            )
        return self.data({})


@plugin.route(r"/filed-files")
class FiledFilesHandler(CMFChinaHandler):
    @Auth("browse")
    @use_kwargs(FiledFileSearchSchema, location="query")
    async def get(
        self,
        filename,
        projectname,
        fid,
        user_name,
        pdf_parse_status,
        sysfrom,
        ai_status,
        start_at,
        end_at,
        order_by,
        page,
        size,
    ):
        data = await CmfChinaService.get_pagination_filed_files(
            filename,
            projectname,
            fid,
            user_name,
            pdf_parse_status,
            sysfrom,
            ai_status,
            start_at,
            end_at,
            order_by,
            page,
            size,
        )
        return self.data(data)

    @Auth("browse")
    @use_kwargs(
        {
            "sysfrom": fields.Str(
                load_default=CmfChinaSysFromType.LOCAL.value,
                validate=field_validate.OneOf(CmfChinaSysFromType.member_values()),
            ),
        },
        location="form",
    )
    @use_kwargs(
        {
            "files": fields.List(
                fields.Raw(required=True, validate=CmfPostFileValidator.check),
                validate=validate_file_length,
                data_key="file",
            )
        },
        location="files",
    )
    async def post(self, sysfrom: str, files: list[HTTPFile]):
        async with pw_db.atomic():
            new_file, cmf_file_info = await CmfChinaService.upload_filed_file(files[0], self.current_user.id, sysfrom)
        await process_file_for_excel(new_file)
        return self.data(cmf_file_info.to_dict())

    @Auth("browse")
    @use_kwargs({"fids": fields.List(fields.Int(required=True))}, location="json")
    async def delete(self, fids):
        files = await pw_db.execute(NewFile.select().where(NewFile.id.in_(fids)))
        async with pw_db.atomic():
            for file in files:
                await file.soft_delete()
            await pw_db.execute(CmfFiledFileInfo.delete().where(CmfFiledFileInfo.fid.in_(fids)))


@plugin.route(r"/filed-files/sse")
class FiledFilesSSEHandler(UploadZipFileBaseHandler):
    @Auth("browse")
    @use_kwargs(
        {
            "event_id": fields.Str(load_default=None),
            "sysfrom": fields.Str(
                load_default=CmfChinaSysFromType.LOCAL.value,
                validate=field_validate.OneOf(CmfChinaSysFromType.member_values()),
            ),
        },
        location="form",
    )
    @use_kwargs(
        {
            "files": fields.List(
                fields.Raw(validate=CmfZipFileValidator.check),
                validate=validate_zip_file_length,
                data_key="file",
                load_default=[],
            )
        },
        location="files",
    )
    async def post(self, event_id: str | None, sysfrom: str, files: list[HTTPFile]):
        async with pw_db.atomic():
            project = await NewFileProjectService.create(
                name=CMF_CHINA_FILED_FILE_PROJECT_NAME, uid=self.current_user.id, visible=False
            )
            tree = await NewFileTree.find_by_id(project.rtree_id)
        file = files[0] if files else None
        await self.upload_compressed_file(
            tid=tree.id,
            task_type=TaskType.AUDIT.value,
            event_id=event_id,
            file=file,
            need_create_folder=False,
            sysfrom=sysfrom,
        )


@plugin.route(r"/filed-files/execute")
class ResetFiledFilesHandler(CMFChinaHandler):
    # 重新分类
    @Auth("browse")
    @use_kwargs({"fids": fields.List(fields.Int(required=True))}, location="json")
    async def post(self, fids):
        if not fids:
            return self.error(_("Invalid input parameters."), status_code=http.HTTPStatus.BAD_REQUEST)
        fids = await pw_db.scalars(
            NewFile.select(NewFile.id)
            .join(CmfFiledFileInfo, on=(CmfFiledFileInfo.fid == NewFile.id))
            .where(NewFile.id.in_(fids), NewFile.pdf_parse_status == PDFParseStatus.COMPLETE)
            .order_by(NewFile.id.desc())
        )
        lock_expired = get_config("web.run_lock_expired", 600)
        for fid in fids:
            get_lock, lock = run_singleton_task(reset_filed_file_task, fid, lock_expired=lock_expired)
            if not get_lock:
                raise CustomError(
                    f"操作过于频繁,  请至少间隔{max(1, lock_expired // 60)}分钟",
                    resp_status_code=http.HTTPStatus.TOO_MANY_REQUESTS,
                )
        return self.data({})


@plugin.route(r"/files/(\d+)/status")
class VerifyFiledFileStatusHandler(CMFChinaHandler):
    @Auth("browse")
    async def get(self, fid):
        file = await CmfChinaService.get_verify_filed_file(fid)
        if not file:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        return self.data(file.to_dict())


@plugin.route(r"/files/(\d+)/verify-filed")
class FiledFileHandler(CMFChinaHandler):
    @Auth("browse")
    async def get(self, fid):
        if not (file := await NewFile.find_by_id(fid)):
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        if file.pdf_parse_status != PDFParseStatus.COMPLETE:
            return self.error(message="文档解析中", status_code=http.HTTPStatus.BAD_REQUEST)
        mids = file.molds
        pid = file.pid
        mold_names = await pw_db.scalars(NewMold.select(NewMold.name).where(NewMold.id.in_(mids)))
        project_name = await pw_db.scalar(NewFileProject.select(NewFileProject.name).where(NewFileProject.id == pid))
        if not mold_names or not project_name:
            return self.error("文件关联的项目或场景不存在", status_code=http.HTTPStatus.BAD_REQUEST)
        verify, msg = await CmfFiledFileService.verify_filed(file, mids, pid, mold_names, project_name)
        if not verify:
            return self.error(msg, status_code=http.HTTPStatus.BAD_REQUEST)
        return self.data({"message": msg})


@plugin.route(r"/verify-filed")
class VerifyFiledFileHandler(CMFChinaHandler):
    @Auth("browse")
    @use_kwargs(FiledVerifySchema, location="query")
    async def get(self, fid, pid, mid):
        if not (file := await NewFile.find_by_id(fid)):
            return self.error("文件已过期，请重新上传", status_code=http.HTTPStatus.GONE)
        if file.pdf_parse_status == PDFParseStatus.FAIL:
            return self.error(message="文档解析失败，请重新上传", status_code=http.HTTPStatus.BAD_REQUEST)
        if file.pdf_parse_status != PDFParseStatus.COMPLETE:
            return self.error(message="文档解析中", status_code=http.HTTPStatus.BAD_REQUEST)
        if not (project := await NewFileProject.get_by_id(pid)):
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        if not (mold := await NewMold.get_by_id(mid)):
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        verify, msg = await CmfFiledFileService.verify_filed(file, [mold.id], project.id, [mold.name], project.name)
        if not verify:
            return self.error(msg, status_code=http.HTTPStatus.BAD_REQUEST)
        return self.data({"message": msg})

    @Auth("browse")
    @use_kwargs({"file": fields.Raw(required=False, validate=CmfPostFileValidator.check)}, location="files")
    async def post(self, file: HTTPFile | None):
        async with pw_db.atomic():
            project = await NewFileProjectService.create(
                name=CMF_CHINA_VERIFY_FILED_PROJECT_NAME, uid=self.current_user.id, visible=False
            )
            file_tree = await NewFileTree.find_by_id(project.rtree_id)
            new_file = await NewFileService.create_file(
                name=file.filename,
                body=file.body,
                pid=project.id,
                tree_id=file_tree.id,
                uid=self.current_user.id,
                task_type=TaskType.EXTRACT.value,
                molds=[],
            )
        await process_file(new_file)
        return self.data({"fid": new_file.id})


@plugin.route(r"/filed-code")
class ClassCodeHandler(CMFChinaHandler):
    @Auth("browse")
    @use_kwargs(
        {
            "files": fields.List(
                fields.Raw(required=True),
                validate=validate_file_length,
                data_key="file",
            )
        },
        location="files",
    )
    async def post(self, files: list[HTTPFile]):
        # 上传分类代码py文件
        if os.path.splitext(files[0].filename)[1].lower() != ".py":
            return self.error("仅支持后缀为 .py 的文件", status_code=http.HTTPStatus.BAD_REQUEST)
        await CmfFiledFileService.save_filed_code(files[0])

    @Auth("browse")
    @use_kwargs({"sample": fields.Bool(load_default=True)}, location="query")
    async def get(self, sample):
        # 获取分类代码py文件
        try:
            name, data = await CmfFiledFileService.get_filed_code(sample)
        except FileNotFoundError:
            return self.error("未找到分类代码文件", status_code=http.HTTPStatus.NOT_FOUND)
        return await self.export(data, name)


@plugin.route(r"/files")
class FileSearchHandler(CMFChinaHandler):
    @Auth("browse")
    @use_kwargs(NameSearchSchema, location="query")
    async def get(self, name, page, size):
        files = await CmfChinaService.get_pagination_mold_pro_files(name, page, size)
        return self.data(files)


@plugin.route(r"/molds/(\d+)/check-fields")
class MoldCheckFieldsHandler(CMFChinaHandler):
    """记录/获得用户选择字段"""

    @Auth("browse")
    async def get(self, mid):
        data = await CmfChinaService.get_check_fields(self.current_user.id, mid)
        return self.data(data)

    @Auth("browse")
    @use_kwargs(
        {"check_fields": fields.Dict(keys=fields.Integer(), values=fields.Boolean(), required=True)},
        location="json",
    )
    async def post(self, mid: int, check_fields: dict[int, bool]):
        await CmfUserCheckFields.bulk_update(CmfUserCheckFields.check, CmfUserCheckFields.mold_field_id, check_fields)


@plugin.route(r"/review")
class FileReviewHandler(CMFChinaHandler):
    """文件复核"""

    @Auth("browse")
    @use_kwargs({"fids": fields.List(fields.Int(), required=True)}, location="json")
    async def post(self, fids):
        fids = await pw_db.scalars(NewFile.select(NewFile.id).where(NewFile.id.in_(fids)))
        exist_fids = await pw_db.scalars(
            CmfFileReviewed.update(reviewed_count=CmfFileReviewed.reviewed_count + 1, uid=self.current_user.id)
            .where(CmfFileReviewed.file_id.in_(fids))
            .returning(CmfFileReviewed.file_id)
        )
        new_file_reviewed_list = [{"uid": self.current_user.id, "file_id": fid} for fid in set(fids) - set(exist_fids)]
        await CmfFileReviewed.bulk_insert(new_file_reviewed_list)
        # TODO 给客户推送数据

    @Auth("browse")
    @use_kwargs(ModelCallSchema, location="query")
    async def get(self, model_ids, count_type, start_at, end_at):
        # 文件复核统计
        model_ids = await pw_db.scalars(CmfModel.select(CmfModel.id).where(CmfModel.id.in_(model_ids)))
        if not model_ids:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        data = await CmfChinaService.get_model_review_count(model_ids, count_type, start_at, end_at)
        return self.data(data)


@plugin.route(r"/panorama")
class PanoramaHandler(CMFChinaHandler):
    """获取全景列表"""

    @Auth("browse")
    @use_kwargs(PanoramaSearchSchema, location="json")
    async def post(
        self,
        mid: int,
        pid: int | None,
        fid: int | None,
        file_name: str | None,
        start_at: int | None,
        end_at: int | None,
        reviewed: ReviewedType,
        filter_dict: dict,
        order_by: str,
        _type: TimeType,
        page: int,
        size: int,
    ):
        mold = await NewMold.find_by_id(mid)
        if not mold:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        tree_ids = None
        if not self.current_user.is_admin:
            tree_ids = await CMFGroupService.get_user_group_file_trees(self.current_user.id)
        res = await CmfChinaService.get_panorama(
            mold,
            pid,
            fid,
            file_name,
            start_at,
            end_at,
            reviewed,
            filter_dict,
            order_by,
            _type,
            page,
            size,
            tree_ids,
            False,
        )
        for row in res["items"]:
            row["data"] = {
                "schema": mold.data,
                "answer": {"items": row.pop("answer_data") if row.get("answer_data") else []},
                "audit_results": {"items": row.pop("audit_results") if row.get("audit_results") else []},
            }
        return self.data(res)


@plugin.route(r"/training_data")
class PanoramaExportHandler(CMFChinaHandler):
    @Auth("manage_mold")
    @use_kwargs(ExportSchema, location="json")
    async def post(
        self,
        mid: int,
        pid: int | None,
        fid: int | None,
        file_name: str | None,
        start_at: int | None,
        end_at: int | None,
        reviewed: ReviewedType,
        filter_dict: dict,
        _type: TimeType,
        files_ids: list[int],
        export_type: str,
        export_action: HistoryAction,
    ):
        mold = await NewMold.get_by_id(mid)
        if not mold:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        tree_ids = None
        if not self.current_user.is_admin:
            tree_ids = await CMFGroupService.get_user_group_file_trees(self.current_user.id)
        if not files_ids:
            res = await CmfChinaService.get_panorama(
                mold,
                pid,
                fid,
                file_name,
                start_at,
                end_at,
                reviewed,
                filter_dict,
                "-id",
                _type=_type,
                tree_ids=tree_ids,
                export=True,
            )
            files_ids = [item["id"] for item in res]
        if not files_ids:
            return self.error("暂没有可导出的文件", status_code=http.HTTPStatus.BAD_REQUEST)
        training_data = await mold_export_task(mold.id, export_type, [], files_ids, export_action)
        # 操作记录
        await NewHistory.save_operation_history(
            training_data.id,
            self.current_user.id,
            export_action,
            self.current_user.name,
            {"task_id": training_data.id},
        )
        return self.data(training_data.to_dict())


@plugin.route(r"/model-usage")
class ModelUsageCountHandler(CMFChinaHandler):
    """模型调用统计"""

    @Auth("browse")
    @use_kwargs(ModelCallSchema, location="query")
    async def get(self, model_ids, count_type, start_at, end_at):
        model_ids = await pw_db.scalars(CmfModel.select(CmfModel.id).where(CmfModel.id.in_(model_ids)))
        if not model_ids:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        data = await CmfChinaService.get_model_usage_count(model_ids, count_type, start_at, end_at)
        return self.data(data)


@plugin.route(r"/model-accuracy")
class ModelAccuracyHandler(CMFChinaHandler):
    @Auth("browse")
    @use_kwargs(ModelAccuracySchema, location="query")
    async def get(self, model_ids, count_type, start_at, end_at, run_statistical_task: bool):
        if run_statistical_task:
            save_audit_result_statistic.delay()
        models = await pw_db.execute(CmfModel.select().where(CmfModel.id.in_(model_ids)).order_by(CmfModel.id.desc()))
        if not models:
            return self.data({})

        data = await CmfChinaService.get_model_accuracy(models, count_type, start_at, end_at)
        return self.data(data)


@plugin.route(r"/rules")
class RulesHandler(CMFChinaHandler):
    @Auth("customer_rule_participate")
    @use_kwargs(RulesSchema, location="query")
    async def get(self, page, size, mold_id, name, rule_type, rule_id, user, field):
        mold_ids = None
        if not self.current_user.is_admin:
            mold_ids = await CMFGroupService.get_user_group_molds(self.current_user.id)
        data = await CmfChinaService.get_rules(page, size, mold_id, name, rule_type, rule_id, user, field, mold_ids)
        return self.data(data)

    @Auth("customer_rule_participate")
    @use_kwargs(rules_schema, location="json")
    async def post(self, rules):
        public = get_config("feature.default_audit_rule_public")
        names = [rule_item["name"] for rule_item in rules]
        if len(names) != len(set(names)):
            return self.error("规则名称不能重复", status_code=http.HTTPStatus.BAD_REQUEST)
        if await pw_db.exists(NewAuditRule.select().where(NewAuditRule.name.in_(names))):
            return self.error("规则名称已存在", status_code=http.HTTPStatus.BAD_REQUEST)
        res = []
        async with pw_db.atomic():
            for rule_item in rules:
                rule_item["uid"] = self.current_user.id
                rule_item["user"] = self.current_user.name
                rule_item["handle_uid"] = self.current_user.id
                rule_item["handle_user"] = self.current_user.name
                rule_item["public"] = public
                rule = NewAuditRule(**rule_item)
                rule_item["fields"] = rule.schema_fields
                res.append(rule_item)
            await NewAuditRule.bulk_insert(res)


@plugin.route(r"/rules/(\d+)")
class RuleHandler(CMFChinaHandler):
    @Auth("customer_rule_participate")
    @use_kwargs(RuleSchema, location="json")
    async def post(self, rule_id, **kwargs):
        rule = await NewAuditRule.get_by_id(int(rule_id))
        if not rule:
            return self.error("未找到对应规则", status_code=http.HTTPStatus.NOT_FOUND)

        if await pw_db.exists(
            NewAuditRule.select().where(NewAuditRule.name == kwargs["name"], NewAuditRule.id != rule.id)
        ):
            return self.error("规则名称已存在", status_code=http.HTTPStatus.CONFLICT)

        kwargs["review_status"] = RuleReviewStatus.NOT_REVIEWED
        kwargs["handle_uid"] = self.current_user.id
        kwargs["handle_user"] = self.current_user.name

        for key, value in kwargs.items():
            if value is None:
                continue
            setattr(rule, key, value)
        rule.reset_type()

        if not rule.is_valid:
            return self.error("不合法的规则，请检查后再试", status_code=http.HTTPStatus.BAD_REQUEST)
        rule.fields = rule.schema_fields
        await pw_db.update(rule)

        return self.data(rule.to_dict())


@plugin.route(r"/groups")
class GroupsHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(PaginationSchema, location="query")
    async def get(self, page, size):
        # group_ids = None
        # if not self.current_user.is_admin:
        #     group_ids = await CMFUserGroupRef.get_user_group_ids(self.current_user.id)
        data = await CMFGroupService.get_pagination_groups(page, size)
        all_file_trees = await pw_db.execute(NewFileTree.select(NewFileTree.id, NewFileTree.name))
        file_maps = {tree.id: tree.name for tree in all_file_trees}
        all_molds = await pw_db.execute(NewMold.select(NewMold.id, NewMold.name))
        molds_map = {mold.id: mold.name for mold in all_molds}
        for item in data["items"]:
            file_trees = []
            molds = []
            for file_tree_id in item["file_tree_ids"]:
                file_trees.append(file_maps[file_tree_id])
            for mold_id in item["mold_ids"]:
                molds.append(molds_map[mold_id])
            item["file_trees"] = file_trees
            item["molds"] = molds
        return self.data(data)

    @Auth("browse")
    @use_kwargs(GroupSchema, location="json")
    async def post(self, name, file_tree_ids, mold_ids):
        try:
            await CMFGroupService.create(name, file_tree_ids, mold_ids)
        except peewee.IntegrityError:
            return self.error("业务组名已存在", status_code=http.HTTPStatus.BAD_REQUEST)
        return self.data({})


@plugin.route(r"/groups/(\d+)")
class GroupHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(EditGroupSchema, location="json")
    async def put(self, group_id, name, file_tree_ids, mold_ids):
        group = await CMFGroup.find_by_id(group_id)
        if not group:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        try:
            await CMFGroupService.update(group.id, name, file_tree_ids, mold_ids)
        except peewee.IntegrityError:
            return self.error("业务组名已存在", status_code=http.HTTPStatus.BAD_REQUEST)
        return self.data({})

    @Auth("browse")
    async def delete(self, group_id):
        group = await CMFGroup.find_by_id(group_id)
        if not group:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        await CMFGroupService.delete(group)
        return self.data({})


@plugin.route(r"/catalog")
class CatalogHandler(BaseHandler):
    @Auth("browse")
    async def get(self):
        trees = await NewFileTree.get_all_trees(self.current_user)
        root = trees[0]
        return self.data(root)


@plugin.route(r"/trees/(\d+)/tree")
class CreateTreeHandler(PermCheckHandler):
    tree_args = {
        "name": fields.String(required=True, validate=field_validate.Length(min=1)),
        "default_molds": fields.List(fields.Int(), load_default=[]),
        "group_ids": fields.List(fields.Int(), load_default=[]),
    }

    @Auth(["browse"])
    @use_kwargs(tree_args, location="json")
    async def post(self, tid, name, default_molds, group_ids):
        """创建目录"""
        tree = await NewFileTree.find_by_id(tid)
        if not tree:
            return self.error(_("can't find the tree"), status_code=http.HTTPStatus.BAD_REQUEST)

        await self.check_tree_permission(tid, tree=tree)
        groups = await CMFGroupService.get_groups(group_ids)
        if default_molds:
            if not set(default_molds).issubset({mold_id for group in groups for mold_id in group["mold_ids"]}):
                return self.error("所选场景不在业务组内", status_code=http.HTTPStatus.BAD_REQUEST)

        async with pw_db.atomic():
            new_tree = await NewFileTreeService.create(
                tid=tid,
                uid=self.current_user.id,
                pid=tree.pid,
                name=name,
                default_molds=default_molds,
                inherit_parent_molds=False,
            )
            for group in groups:
                file_tree_ids = set(group["file_tree_ids"] + [new_tree.id])
                await CMFGroupService.update(group["id"], file_tree_ids=list(file_tree_ids))

            await NewHistory.save_operation_history(
                new_tree.id,
                self.current_user.id,
                HistoryAction.CREATE_TREE.value,
                self.current_user.name,
                meta=new_tree.to_dict(),
            )

        return self.data(new_tree.to_dict())


@plugin.route(r"/molds")
class MoldsHandler(BaseHandler):
    post_kwargs = {
        "name": fields.Str(validate=field_validate.Length(min=1, max=128)),
        "data": mold_data_schema,
        "mold_type": fields.Int(
            load_default=MoldType.COMPLEX.value, validate=field_validate.OneOf(choices=MoldType.member_values())
        ),
        "group_ids": fields.List(fields.Int(), load_default=[]),
    }

    @Auth("browse")
    @use_kwargs(post_kwargs, location="json")
    async def post(self, data, name, mold_type, group_ids):
        groups = await CMFGroupService.get_groups(group_ids)

        async with pw_db.atomic():
            mold = await NewMoldService.create(data, name, mold_type, self.current_user.id)
            for group in groups:
                mold_ids = set(group["mold_ids"] + [mold.id])
                await CMFGroupService.update(group["id"], mold_ids=list(mold_ids))

            await NewHistory.save_operation_history(
                mold.id,
                self.current_user.id,
                HistoryAction.CREATE_MOLD.value,
                self.current_user.name,
                meta=data,
            )
        return self.data(mold.to_dict(recurse=False))


@plugin.route(r"/molds/(\d+)")
class MoldHandler(PermCheckHandler):
    args_schema = {
        "name": fields.String(validate=field_validate.Length(min=1, max=128), required=True),
        "data": mold_data_schema,
        "predictors": fields.List(fields.Dict, required=True),
        "checksum": fields.String(),
        "created_utc": fields.Integer(),
        "updated_utc": fields.Integer(),
        "id": fields.Integer(),
        "mold_type": fields.Integer(),
        "meta": fields.Dict(),
        "group_ids": fields.List(fields.Int()),
    }

    @Auth("browse")
    async def get(self, mid):
        mold = await NewMold.find_by_id(mid)
        if mold is None:
            return self.error(message=_("Item Not Found"), status_code=404)
        if get_config("web.model_manage", True) and not mold.predictors:
            from remarkable.predictor.helpers import create_predictor_prophet

            try:
                prophet = await asyncio.get_event_loop().run_in_executor(None, create_predictor_prophet, mold)
                mold.predictors = prophet.predictor_options
            except Exception as exp:
                logger.warning(f"Exception when load mold({mold.id}) predictors: {exp}")

        group_ids = (
            None if self.current_user.is_admin else await CMFUserGroupRef.get_user_group_ids(self.current_user.id)
        )
        groups = await CMFGroupService.get_mold_groups(mold.id, group_ids)
        data = mold.to_dict()
        data["groups"] = [x.to_dict() for x in groups]
        return self.data(data)

    @Auth("browse")
    @use_kwargs(args_schema, location="json")
    async def put(self, mid, **kwargs):
        mold = await NewMold.find_by_id(mid)
        if not mold:
            return self.error(message=_("Item Not Found"), status_code=http.HTTPStatus.NOT_FOUND)
        await self.new_check_mold_permission(mold)

        group_ids = kwargs.pop("group_ids")
        user_group_ids = None
        if not self.current_user.is_admin:
            user_group_ids = await CMFUserGroupRef.get_user_group_ids(self.current_user.id)

        exist_mold_groups = await CMFGroupService.get_mold_groups(mold.id, user_group_ids)
        exist_mold_group_ids = [x.id for x in exist_mold_groups]

        async with pw_db.atomic():
            old_schema = MoldSchema(mold.data)
            mold = await NewMoldService.update(mold, **kwargs)
            # 更新模型字段
            new_schema = MoldSchema(mold.data)
            old_uuids = old_schema.get_all_uuid()
            new_uuids = new_schema.get_all_uuid()
            # 删除字段
            if del_uuids := (old_uuids - new_uuids):
                ids = await pw_db.scalars(
                    NewMoldField.delete()
                    .where(or_(NewMoldField.uuid.in_(del_uuids), NewMoldField.parent.in_(del_uuids)))
                    .returning(NewMoldField.id)
                )
                await pw_db.execute(CmfMoldFieldRef.delete().where(CmfMoldFieldRef.mold_field.in_(ids)))
            # 新增字段
            if add_uuids := (new_uuids - old_uuids):
                new_items = new_schema.get_field_items(mid)
                fix_items = [item for item in new_items if item["uuid"] in add_uuids or item["parent"] in add_uuids]
                ids = list(await NewMoldField.bulk_insert(fix_items, iter_ids=True))
                await CmfMoldFieldRef.bulk_insert([{"mold_field": _id} for _id in ids])
                await pw_db.update(mold, only=["data"])
            await CMFGroupRef.update_refs_for_group(exist_mold_group_ids, group_ids, mold_id=mold.id)

            await NewHistory.save_operation_history(
                mold.id,
                self.current_user.id,
                HistoryAction.MODIFY_MOLD.value,
                self.current_user.name,
                meta=kwargs,
            )
        return self.data(mold.to_dict())

    @Auth("browse")
    @use_kwargs(
        {
            "file": fields.Raw(
                required=True, validate=HTTPFileValidator((".json",), get_config("client.file_size_limit") or 50)
            )
        },
        location="files",
    )
    async def post(self, mold_id: int, file: HTTPFile):
        mold = await NewMold.find_by_id(mold_id)
        if not mold:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        try:
            json_data = json.loads(file.body.decode("utf-8"))
            import_data = CmfImportMoldModel.model_validate(json_data)
        except JSONDecodeError:
            return self.error("数据格式有误，请检查", status_code=http.HTTPStatus.BAD_REQUEST)
        except CustomError as exp:
            return self.error(str(exp), status_code=http.HTTPStatus.BAD_REQUEST)
        except ValidationError as exp:
            logger.exception(str(exp))
            return self.error("数据格式有误，请检查", status_code=http.HTTPStatus.BAD_REQUEST)
        mold_schema = MoldSchema(mold.data)
        if not import_data.alias:
            import_data.alias = mold_schema.root_schema.alias
        params = {}
        if import_data.name:
            params.update({"name": import_data.name})
        else:
            import_data.name = mold.name
        try:
            params.update({"data": ExportMoldConvert.import_to_mold(import_data)})
        except CustomError as exp:
            logger.error(exp)
            return self.error(str(exp), status_code=http.HTTPStatus.BAD_REQUEST)

        mold = await NewMoldService.update(mold, **params)
        await NewMoldService.update_field(mold)

        # 重新预测文件
        if cmf_model := await CmfMoldModelRef.get_enabled_model(mold):
            get_lock, lock = await CmfChinaService.rerun_preset_answers(mold_id, cmf_model.id)
            if not get_lock:
                return self.error(_("The model is predicting, please try again later"))

        return self.data({})


@plugin.route(r"/user/groups")
class UserGroups(BaseHandler):
    @Auth("browse")
    async def get(self):
        group_ids = None
        if not self.current_user.is_admin:
            group_ids = await CMFUserGroupRef.get_user_group_ids(self.current_user.id)
        query = CMFGroupService.get_groups_query(group_ids)
        groups = await pw_db.execute(query)

        all_file_trees = await pw_db.execute(NewFileTree.select(NewFileTree.id, NewFileTree.name))
        file_maps = {tree.id: tree.name for tree in all_file_trees}
        all_molds = await pw_db.execute(NewMold.select(NewMold.id, NewMold.name))
        molds_map = {mold.id: mold.name for mold in all_molds}
        for item in groups:
            file_trees = []
            molds = []
            for file_tree_id in item["file_tree_ids"]:
                file_trees.append(file_maps[file_tree_id])
            for mold_id in item["mold_ids"]:
                molds.append(molds_map[mold_id])
            item["file_trees"] = file_trees
            item["molds"] = molds
        return self.data(list(groups))


@plugin.route(r"/molds/import")
class MoldImportHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(
        {
            "file": fields.Raw(
                required=True, validate=HTTPFileValidator((".json",), get_config("client.file_size_limit") or 50)
            )
        },
        location="files",
    )
    @use_kwargs(
        {
            "group_ids": fields.List(fields.Int()),
        },
        location="form",
    )
    async def post(self, file: HTTPFile, group_ids: list[int]):
        group_ids = await pw_db.scalars(CMFGroup.select(CMFGroup.id).where(CMFGroup.id.in_(group_ids)))
        if not group_ids:
            return self.error("请选择有效分组", status_code=http.HTTPStatus.NOT_FOUND)

        try:
            json_data = json.loads(custom_decode(file.body))
            import_data = CmfImportMoldModel.model_validate(json_data)
        except JSONDecodeError:
            return self.error("数据格式有误，请检查", status_code=http.HTTPStatus.BAD_REQUEST)
        except CustomError as exp:
            return self.error(str(exp), status_code=http.HTTPStatus.BAD_REQUEST)
        except ValidationError as exp:
            logger.exception(str(exp))
            return self.error("数据格式有误，请检查", status_code=http.HTTPStatus.BAD_REQUEST)
        if not import_data.name or not import_data.alias:
            return self.error("场景名称或别名不能为空，请修改后重新导入", status_code=http.HTTPStatus.BAD_REQUEST)
        try:
            data = ExportMoldConvert.import_to_mold(import_data)
        except CustomError as exp:
            logger.error(exp)
            return self.error(str(exp), status_code=http.HTTPStatus.BAD_REQUEST)

        async with pw_db.atomic():
            groups = await CMFGroupService.get_groups(group_ids)
            mold = await NewMoldService.create(data, import_data.name, 0, self.current_user.id)
            await NewMoldService.update_field(mold)
            for group in groups:
                mold_ids = set(group["mold_ids"] + [mold.id])
                await CMFGroupService.update(group["id"], mold_ids=list(mold_ids))
        return self.data(mold.to_dict(recurse=False))


@plugin.route(r"/molds/(\d+)/export")
class MoldExportHandler(BaseHandler):
    @Auth("browse")
    async def get(self, mold_id: int):
        mold = await NewMold.find_by_id(mold_id)
        if not mold:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        mold_schema = MoldSchema(mold.data)
        data = ExportMoldConvert.mold_to_export(mold_schema)
        return await self.export(json.dumps(data, ensure_ascii=False).encode(), f"{mold.name}.json")


@plugin.route(r"/emails")
class EmailHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(SearchEmailSchema, location="query")
    async def get(self, start_at, end_at, order_by, _type, page, size):
        data = await CmfChinaService.get_emails(start_at, end_at, order_by, _type, page, size)
        return self.data(data)

    @Auth("browse")
    @use_kwargs(EmailSchema, location="json")
    async def post(self, host, account, password, mold_id, pid):
        try:
            IMAPEmailReceiver.verify(host, account, password)
        except CustomError as e:
            return self.error(str(e), status_code=http.HTTPStatus.BAD_REQUEST)
        try:
            data = await pw_db.create(
                CmfChinaEmail,
                host=host,
                account=account,
                password=password,
                mold_id=mold_id,
                pid=pid,
                uid=self.current_user.id,
            )
        except peewee.IntegrityError:
            return self.error("邮箱已存在", status_code=http.HTTPStatus.BAD_REQUEST)
        return self.data(data.to_dict())


@plugin.route(r"/emails/(\d+)")
class EditEmailHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(EditEmailSchema, location="json")
    async def put(self, email_id, host, account, password, mold_id, pid):
        email = await CmfChinaEmail.get_by_id(email_id)
        if not email:
            return self.error("邮箱配置不存在", status_code=http.HTTPStatus.NOT_FOUND)
        if mold_id is not None and not await NewMold.get_by_id(mold_id):
            return self.error("场景不存在", status_code=http.HTTPStatus.NOT_FOUND)
        if pid is not None and not await NewFileProject.get_by_id(pid):
            return self.error("项目不存在", status_code=http.HTTPStatus.NOT_FOUND)
        if password is None:
            password = email.password
        try:
            IMAPEmailReceiver.verify(host, account, password)
        except CustomError as e:
            return self.error(str(e), status_code=http.HTTPStatus.BAD_REQUEST)
        try:
            await CmfChinaService.edit_email(email, host, account, password, mold_id, pid)
        except peewee.IntegrityError:
            return self.error("邮箱已存在", status_code=http.HTTPStatus.BAD_REQUEST)
        return self.data(email.to_dict())

    @Auth("browse")
    async def delete(self, email_id):
        await pw_db.execute(CmfChinaEmail.delete().where(CmfChinaEmail.id == email_id))


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
        mold_ids = None
        if not self.current_user.is_admin:
            file_tree_ids = await CMFGroupService.get_user_group_file_trees(self.current_user.id)
            tree_ids = list(set(file_tree_ids) & set(tree_ids))
            mold_ids = await CMFGroupService.get_user_group_molds(self.current_user.id)

        count_obj = await NewFileTreeService.get_ai_status_summary(prj_id, tree_ids, mold_ids)
        mark_summary = await NewQuestionService.get_mark_summary(prj_id, tree_ids, mold_ids)
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


@plugin.route(r"/files/(\d+)/results")
class ResultHandler(CMFChinaHandler):
    @Auth("inspect")
    async def get(self, fid):
        molds = list(
            await pw_db.execute(
                NewMold.select()
                .distinct(NewMold.id)
                .join(NewQuestion, on=(NewQuestion.mold == NewMold.id))
                .join(NewFile, on=(NewQuestion.fid == fid))
            )
        )
        results = await NewAuditResult.get_results(
            fid, [m.id for m in molds], self.current_user.is_admin, self.current_user.id
        )
        result_dict = defaultdict(list)
        for item in results:
            result_dict[item.schema_id].append(item.to_dict())
        res_data = [{"results": result_dict[mold.id], "mold": mold.to_dict()} for mold in molds]

        return self.data(res_data)
