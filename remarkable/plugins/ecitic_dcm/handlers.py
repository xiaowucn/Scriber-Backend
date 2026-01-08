import http
import io
import json
import logging
from pathlib import Path
from zipfile import ZipFile

from marshmallow.validate import OneOf, Regexp
from peewee import JOIN
from webargs import fields

from remarkable.base_handler import Auth, BaseHandler
from remarkable.common.apispec_decorators import use_kwargs
from remarkable.common.constants import DcmStatus, HistoryAction
from remarkable.common.storage import localstorage
from remarkable.db import pw_db
from remarkable.models.ecitic_dcm import (
    DcmBondOrder,
    DcmFileInfo,
    DcmProject,
    DcmProjectFileProjectRef,
    DcmQuestionOrderRef,
)
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.models.query_helper import AsyncPagination, PaginationSchema
from remarkable.plugins import Plugin
from remarkable.plugins.ecitic_dcm.service import (
    DcmBondOrderService,
    DcmFileService,
    DcmFileTreeService,
    DcmProjectService,
    EmailPasswordCryptor,
    get_fill_data,
)
from remarkable.plugins.ecitic_dcm.tasks import get_today_date
from remarkable.pw_models.model import NewFileProject, NewFileTree
from remarkable.pw_models.question import NewQuestion
from remarkable.service.api_cleaner import post_pipe_after_api
from remarkable.service.new_file_tree import get_crumbs

plugin = Plugin(Path(__file__).parent.name)
logger = logging.getLogger(__name__)


class BondOrdersSchema(PaginationSchema):
    investor_name = fields.Str(load_default="")
    bond_shortname = fields.Str(load_default="")
    only_has_ref = fields.Bool(load_default=False)


@plugin.route(r"/questions/(\d+)/orders")
class QuestionBondRefHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(BondOrdersSchema, location="query")
    async def get(self, question_id, investor_name, bond_shortname, only_has_ref, page, size):
        question = await NewQuestion.get_by_id(question_id)
        if not question:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        order_ids = await pw_db.scalars(
            DcmQuestionOrderRef.select(DcmQuestionOrderRef.order_id).where(
                DcmQuestionOrderRef.question_id == question_id
            )
        )

        dcm_project = await DcmProjectService.get_project_by_fid(question.fid)

        data = await DcmBondOrderService.get_pagination_bond_orders(
            order_ids,
            page,
            size,
            project_id=dcm_project.project_id,
            investor_name=investor_name,
            bond_shortname=bond_shortname,
            only_has_ref=only_has_ref,
        )

        return self.data(data)

    @Auth("browse")
    @use_kwargs({"order_ids": fields.List(fields.Int())}, location="json")
    async def put(self, question_id, order_ids):
        question = await NewQuestion.get_by_id(question_id)
        if not question:
            return self.error(_("Question not found"))
        bond_orders = await pw_db.scalars(DcmBondOrder.select(DcmBondOrder.id).where(DcmBondOrder.id.in_(order_ids)))
        if len(bond_orders) != len(order_ids):
            return self.error(_("Not all ids valid."))

        async with pw_db.atomic():
            query = DcmQuestionOrderRef.select(DcmQuestionOrderRef.order_id).where(
                DcmQuestionOrderRef.question_id == question_id
            )
            exist_order_ids = await pw_db.scalars(query)

            orders_to_add = set(order_ids) - set(exist_order_ids)
            roles_to_rm = set(exist_order_ids) - set(order_ids)

            delete_cond = (DcmQuestionOrderRef.question_id == question_id) & (
                DcmQuestionOrderRef.order_id.in_(roles_to_rm)
            )
            insert_params = [{"question_id": question_id, "order_id": order_id} for order_id in orders_to_add]
            await pw_db.execute(DcmQuestionOrderRef.delete().where(delete_cond))
            await DcmQuestionOrderRef.bulk_insert(insert_params)

            await post_pipe_after_api(question.fid, question_id, HistoryAction.DCM_ORDER_REF_MODIFY.value)

        return self.data({})


class ProjectsSchema(PaginationSchema):
    fill_status = fields.Str(load_default="")


@plugin.route(r"/projects")
class ProjectsHandler(BaseHandler):
    @Auth(["browse"])
    @use_kwargs(ProjectsSchema, location="query")
    async def get(self, fill_status, page, size):
        cond = NewFileProject.visible
        if not self.current_user.is_admin:
            cond &= (NewFileProject.uid == self.current_user.id) | NewFileProject.public

        if fill_status:
            cond &= DcmProject.fill_status == fill_status

        query = (
            NewFileProject.select(
                NewFileProject,
                NewAdminUser.name.alias("user_name"),
                DcmProject.email_host,
                DcmProject.email_address,
                DcmProject.fill_status,
            )
            .join(NewAdminUser, JOIN.LEFT_OUTER, on=(NewFileProject.uid == NewAdminUser.id))
            .join(
                DcmProjectFileProjectRef,
                JOIN.LEFT_OUTER,
                on=(DcmProjectFileProjectRef.file_project_id == NewFileProject.id),
            )
            .join(DcmProject, JOIN.LEFT_OUTER, on=(DcmProjectFileProjectRef.dcm_project_id == DcmProject.id))
            .where(cond)
            .order_by(NewFileProject.id.desc())
            .dicts()
        )
        data = await AsyncPagination(query, page=page, size=size).data()
        return self.data(data)


@plugin.route(r"/projects/(\d+)")
class ProjectHandler(BaseHandler):
    param = {
        "email_address": fields.Str(load_default="", validate=Regexp(r".*@citics.com")),
        "email_password": fields.Str(load_default=""),
        "fill_status": fields.Str(load_default="", validate=OneOf([DcmStatus.READY.value])),
    }

    @Auth("browse")
    @use_kwargs(param, location="json")
    async def put(self, pid: str, email_address: str, email_password: str, fill_status: str):
        project = await NewFileProject.get_by_id(pid)
        if not project:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        update_params = {}
        if email_address:
            update_params["email_address"] = email_address
        if email_password:
            update_params["email_password"] = EmailPasswordCryptor.encrypt(email_password)
        if fill_status:
            update_params["fill_status"] = fill_status

        if update_params:
            await DcmProjectService.update_by_file_project_id(project.id, **update_params)
            if fill_status == DcmStatus.READY.value:
                await DcmFileService.update_fill_status_ready(project.id)

        return self.data(None)


class TreeFilesSchema(PaginationSchema):
    file_name = fields.Str(load_default="")
    investor_name = fields.Str(load_default="")
    fill_status = fields.Str(load_default="")
    edit_status = fields.Str(load_default="")
    browse_status = fields.Str(load_default="")


@plugin.route(r"/trees/(\d+)")
class TreeFilesHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(TreeFilesSchema, location="query")
    async def get(self, tid, page, size, **kwargs):
        tree = await NewFileTree.find_by_id(tid)
        if not tree:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
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

        all_files_count = await DcmFileTreeService.get_all_files_count(tid, **kwargs)

        need_file_count = size - len(res["trees"])
        if need_file_count:
            file_end = end - len(trees)
            file_offset = max(file_end - size + len(res["trees"]), 0)
            res["files"] = await DcmFileTreeService.get_files_and_questions_by_tree(
                tid, file_offset, need_file_count, **kwargs
            )
        else:
            res["files"] = []

        res["page"] = page
        res["total"] = all_files_count + len(trees)
        res["crumbs"] = await get_crumbs(tree.id)

        project = await NewFileProject.find_by_id(res["pid"])
        res["project_public"] = project.public

        return self.data(res)


@plugin.route(r"/files/fill_data")
class FileListHandler(BaseHandler):
    param = {
        "publish_start_date": fields.Str(load_default=get_today_date(), validate=Regexp(r"\d{8}")),
        "fill_status": fields.Str(load_default=DcmStatus.READY.value, validate=OneOf(DcmStatus.member_values())),
    }

    @Auth("browse")
    @use_kwargs(param, location="query")
    async def get(self, publish_start_date, fill_status):
        cond = (DcmFileInfo.fill_status == fill_status) & (DcmProject.publish_start_date == publish_start_date)
        query = (
            NewFile.select()
            .join(DcmFileInfo, on=(NewFile.id == DcmFileInfo.file_id))
            .join(DcmProjectFileProjectRef, on=(DcmProjectFileProjectRef.file_project_id == NewFile.pid))
            .join(DcmProject, on=(DcmProject.id == DcmProjectFileProjectRef.dcm_project_id))
        )
        files = await pw_db.execute(query.where(cond))
        file_ids = []
        for file in files:
            file_ids.append(file.id)
        data = await get_fill_data(file_ids)
        await pw_db.execute(
            DcmFileInfo.update(fill_status=DcmStatus.DOING.value).where(DcmFileInfo.file_id.in_(file_ids))
        )
        return self.data({"items": data})


@plugin.route(r"/files/(\d+)")
class FileHandler(BaseHandler):
    param = {
        "fill_status": fields.Str(
            required=True, validate=OneOf((DcmStatus.READY.value, DcmStatus.DONE.value, DcmStatus.FAILED.value))
        ),
    }

    @Auth("browse")
    @use_kwargs(param, location="json")
    async def put(self, file_id, fill_status):
        file = await NewFile.find_by_id(file_id)
        if not file:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        dcm_file_info = await DcmFileInfo.get_by_file_id(file_id)
        if not dcm_file_info:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)

        update_params = {"fill_status": fill_status}
        project_fill_status = await DcmProjectService.calc_project_fill_status(file, fill_status)
        async with pw_db.atomic():
            await pw_db.execute(DcmFileInfo.update(**update_params).where((DcmFileInfo.file_id == file_id)))
            await DcmProjectService.update_by_file_project_id(file.pid, fill_status=project_fill_status)
        return self.data({})


@plugin.route(r"/files/(\d+)/fill_data")
class FileDataToFill(BaseHandler):
    async def get(self, file_id):
        file = await NewFile.find_by_id(file_id)
        if not file:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)
        dcm_file_info = await DcmFileInfo.get_by_file_id(file_id)
        if not dcm_file_info:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)

        data = await get_fill_data([file.id])
        if not data:
            return self.error(_("data not ready"), status_code=http.HTTPStatus.BAD_REQUEST)

        pdf_file = localstorage.read_file(file.pdf_path()) if file.pdf else None
        email_screenshot = (
            localstorage.read_file(dcm_file_info.email_screenshot_path()) if dcm_file_info.email_screenshot else None
        )

        res = io.BytesIO()
        with ZipFile(res, "w") as res_fp:
            res_fp.writestr("data.json", json.dumps(data[0], ensure_ascii=False).encode("utf-8"))
            # 写文件
            if pdf_file:
                res_fp.writestr("purchase.pdf", pdf_file)
            if email_screenshot:
                res_fp.writestr("email_screenshot.jpeg", email_screenshot)

        return await self.export(res.getvalue(), f"project{file.pid}_fileid{file.id}.zip")
