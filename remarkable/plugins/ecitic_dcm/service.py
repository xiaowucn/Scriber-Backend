import base64
import hashlib
import logging
from collections import defaultdict

import speedy
from peewee import JOIN, fn
from utensils.crypto import aes_decrypt, aes_encrypt

from remarkable.answer.reader import AnswerReader
from remarkable.common.constants import DcmStatus, JSONConverterStyle
from remarkable.common.storage import localstorage
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.ecitic_dcm import (
    DcmBondLimit,
    DcmBondOrder,
    DcmFileInfo,
    DcmProject,
    DcmProjectFileProjectRef,
    DcmQuestionOrderRef,
    DcmUnderWriteRate,
)
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.models.query_helper import AsyncPagination
from remarkable.pw_models.model import NewFileProject, NewMold
from remarkable.pw_models.question import NewQuestion
from remarkable.service.dcm_email import Email
from remarkable.service.new_file import NewFileService

logger = logging.getLogger(__name__)


class DcmBondOrderService:
    @classmethod
    async def get_pagination_bond_orders(
        cls, ref_order_ids, page, size, project_id=None, investor_name=None, bond_shortname=None, only_has_ref=False
    ):
        query = cls.get_bond_orders_query(ref_order_ids, project_id, investor_name, bond_shortname, only_has_ref)
        data = await AsyncPagination(query, page=page, size=size).data()

        return data

    @classmethod
    async def get_bond_orders(
        cls, ref_order_ids, project_id=None, investor_name=None, bond_shortname=None, only_has_ref=False
    ):
        query = cls.get_bond_orders_query(ref_order_ids, project_id, investor_name, bond_shortname, only_has_ref)
        data = await pw_db.execute(query)

        return list(data)

    @staticmethod
    def get_bond_orders_query(
        ref_order_ids, project_id=None, investor_name=None, bond_shortname=None, only_has_ref=False
    ):
        has_ref = DcmBondOrder.id.in_(ref_order_ids)
        query = DcmBondOrder.select(
            DcmBondOrder,
            DcmBondLimit.limit_id,
            DcmBondLimit.scale,
            has_ref.alias("has_ref"),
        ).join(DcmBondLimit, on=(DcmBondOrder.limit_id == DcmBondLimit.limit_id), join_type=JOIN.LEFT_OUTER)

        cond = speedy.peewee_plus.orm.TRUE
        if project_id:
            cond &= DcmBondOrder.project_id == project_id
        if investor_name:
            cond &= DcmBondOrder.investor_name.contains(investor_name)
        if bond_shortname:
            cond &= DcmBondOrder.bond_shortname.contains(bond_shortname)
        if only_has_ref:
            cond &= has_ref

        query = query.where(cond).order_by(has_ref.desc(), DcmBondOrder.project_id, DcmBondOrder.order_no).dicts()
        return query

    @staticmethod
    async def update_relationship_by_investor_name(fid, qid, investor_name):
        """
        根据investor_name(订单人)更新与簿记数据的关联关系
        :param fid:
        :param qid:
        :param investor_name:
        :return:
        """
        async with pw_db.atomic():
            exist_order_query = DcmQuestionOrderRef.select(DcmQuestionOrderRef.order_id).where(
                DcmQuestionOrderRef.question_id == qid
            )
            exist_order_ids = await pw_db.scalars(exist_order_query)

            dcm_project = await DcmProjectService.get_project_by_fid(fid)

            cond = DcmBondOrder.investor_name == investor_name
            cond &= DcmBondOrder.project_id == dcm_project.project_id
            order_query = DcmBondOrder.select(DcmBondOrder.id).where(cond)
            order_ids = await pw_db.scalars(order_query)

            orders_to_add = set(order_ids) - set(exist_order_ids)
            insert_params = [{"question_id": qid, "order_id": order_id} for order_id in orders_to_add]

            await DcmQuestionOrderRef.bulk_insert(insert_params)

    @staticmethod
    async def get_by_file_ids(file_ids):
        bond_order_query = (
            DcmBondOrder.select(
                NewFile.id.alias("file_id"),
                NewFile.pid.alias("project_id"),
                DcmFileInfo.email_sent_at,
                NewQuestion.answer,
                fn.JSONB_AGG(
                    fn.JSONB_BUILD_OBJECT(
                        "orderapply_id",
                        DcmBondOrder.orderapply_id,
                        "project_id",
                        DcmBondOrder.project_id,
                        "project_name",
                        DcmBondOrder.project_name,
                        "product_id",
                        DcmBondOrder.product_id,
                        "bond_shortname",
                        DcmBondOrder.bond_shortname,
                        "order_no",
                        DcmBondOrder.order_no,
                        "investor_name",
                        DcmBondOrder.investor_name,
                        "interest_rate",
                        DcmBondOrder.interest_rate,
                        "base_money",
                        DcmBondOrder.base_money,
                        "apply_scale",
                        DcmBondOrder.apply_scale,
                        "base_limit",
                        DcmBondOrder.base_limit,
                        "scale_limit",
                        DcmBondOrder.scale_limit,
                        "total_amt",
                        DcmBondOrder.total_amt,
                        "apply_money",
                        DcmBondOrder.apply_money,
                        "limit_id",
                        DcmBondLimit.limit_id,
                        "scale",
                        DcmBondLimit.scale,
                    )
                ).alias("bond_orders"),
            )
            .join(DcmQuestionOrderRef, on=(DcmQuestionOrderRef.order_id == DcmBondOrder.id))
            .join(NewQuestion, on=(NewQuestion.id == DcmQuestionOrderRef.question_id))
            .join(NewFile, on=(NewFile.id == NewQuestion.fid))
            .join(DcmFileInfo, on=(NewFile.id == DcmFileInfo.file_id))
            .join(DcmBondLimit, on=(DcmBondOrder.limit_id == DcmBondLimit.limit_id), join_type=JOIN.LEFT_OUTER)
        )

        cond = NewFile.id.in_(file_ids)
        bond_order_query = bond_order_query.where(cond).group_by(NewFile.id, DcmFileInfo.id, NewQuestion.id)
        data = await pw_db.execute(bond_order_query.dicts())

        return list(data)


class DcmProjectService:
    @staticmethod
    async def get_project_by_fid(fid):
        dcm_project = await pw_db.first(
            DcmProject.select()
            .join(DcmProjectFileProjectRef, on=(DcmProject.id == DcmProjectFileProjectRef.dcm_project_id))
            .join(NewFileProject, on=(NewFileProject.id == DcmProjectFileProjectRef.file_project_id))
            .join(NewFile, on=(NewFileProject.id == NewFile.pid))
            .where(NewFile.id == fid)
        )

        return dcm_project

    @staticmethod
    async def update_by_file_project_id(file_project_id, **update_params):
        await pw_db.execute(
            DcmProject.update(**update_params)
            .from_(DcmProjectFileProjectRef)
            .where(
                (DcmProject.id == DcmProjectFileProjectRef.dcm_project_id)
                & (DcmProjectFileProjectRef.file_project_id == file_project_id)
            )
        )

    @staticmethod
    async def get_file_project_by_dcm_project_id(dcm_project_id):
        return await pw_db.first(
            NewFileProject.select()
            .join(DcmProjectFileProjectRef, on=(NewFileProject.id == DcmProjectFileProjectRef.file_project_id))
            .where(DcmProjectFileProjectRef.dcm_project_id == dcm_project_id)
        )

    @staticmethod
    async def calc_project_fill_status(file, fill_status):
        query = (
            DcmFileInfo.select(DcmFileInfo.fill_status)
            .join(NewFile, on=(DcmFileInfo.file_id == NewFile.id))
            .join(NewFileProject, on=(NewFile.pid == NewFileProject.id))
            .where(NewFileProject.id == file.pid, NewFile.id != file.id)
        )
        fill_status_list = await pw_db.scalars(query)
        fill_status_list = list(fill_status_list)
        fill_status_list.append(fill_status)

        if not fill_status_list:
            return DcmStatus.TODO.value

        if DcmStatus.FAILED.value in fill_status_list:
            return DcmStatus.FAILED.value
        elif DcmStatus.TODO.value in fill_status_list:
            return DcmStatus.TODO.value
        elif DcmStatus.READY.value in fill_status_list:
            return DcmStatus.READY.value
        elif DcmStatus.DOING.value in fill_status_list:
            return DcmStatus.DOING.value

        return DcmStatus.DONE.value


class DcmFileService(NewFileService):
    @classmethod
    async def create(
        cls,
        mail: Email,
        image_bytes: bytes,
        name: str,
        body: bytes,
        molds: list[int],
        pid: int,
        tree_id: int,
        uid: int,
    ):
        new_file_hash = hashlib.md5(body).hexdigest()
        email_sent_at = int(mail.sent_at.timestamp())
        same_file = await pw_db.exists(
            NewFile.select()
            .join(DcmFileInfo, on=(NewFile.id == DcmFileInfo.file_id))
            .where(
                (NewFile.hash == new_file_hash)
                & (DcmFileInfo.email_sent_at == email_sent_at)
                & (DcmFileInfo.email_from == mail.from_)
                & (DcmFileInfo.email_to == mail.to)
                & (DcmFileInfo.email_content == mail.body)
            )
        )
        if same_file:
            logger.info(f"duplicate file:{name}, email_from:{mail.from_},{mail.sent_at}")
            return

        async with pw_db.atomic():
            file = await NewFileService.create_file(
                name=name,
                body=body,
                molds=molds,
                pid=pid,
                tree_id=tree_id,
                uid=uid,
            )

            file_info = await DcmFileInfo.create(
                file_id=file.id,
                email_sent_at=email_sent_at,
                email_from=mail.from_,
                email_to=mail.to,
                email_screenshot=hashlib.md5(image_bytes).hexdigest(),
                email_content=mail.body,
            )
            localstorage.write_file(file_info.email_screenshot_path(), image_bytes)

            return file

    @staticmethod
    async def update_fill_status_ready(file_project_id):
        await pw_db.execute(
            DcmFileInfo.update(fill_status=DcmStatus.READY.value)
            .from_(NewFile, NewFileProject)
            .where(
                DcmFileInfo.file_id == NewFile.id,
                NewFile.pid == NewFileProject.id,
                NewFileProject.id == file_project_id,
                DcmFileInfo.fill_status.not_in([DcmStatus.READY.value, DcmStatus.DOING.value, DcmStatus.DONE.value]),
            )
        )


class DcmUnderWriteRateService:
    @staticmethod
    async def get_by_file_ids(file_ids):
        query = (
            DcmUnderWriteRate.select(
                NewFile.id.alias("file_id"),
                fn.JSONB_AGG(
                    fn.JSONB_BUILD_OBJECT(
                        "underwritegroup_id",
                        DcmUnderWriteRate.underwritegroup_id,
                        "underwrite_name",
                        DcmUnderWriteRate.underwrite_name,
                        "underwrite_role_code",
                        DcmUnderWriteRate.underwrite_role_code,
                        "entr_name",
                        DcmUnderWriteRate.entr_name,
                        "underwrite_balance_ratio",
                        DcmUnderWriteRate.underwrite_balance_ratio,
                    )
                ).alias("under_write_rates"),
            )
            .join(DcmBondOrder, on=(DcmUnderWriteRate.order_id == DcmBondOrder.order_id))
            .join(DcmQuestionOrderRef, on=(DcmQuestionOrderRef.order_id == DcmBondOrder.id))
            .join(NewQuestion, on=(NewQuestion.id == DcmQuestionOrderRef.question_id))
            .join(NewFile, on=(NewFile.id == NewQuestion.fid))
            .where(NewFile.id.in_(file_ids))
            .group_by(NewFile.id)
        )

        data = await pw_db.execute(query.dicts())
        return list(data)


class DcmFileTreeService:
    @classmethod
    async def get_files_and_questions_by_tree(cls, tid, offset, need_file_count, **kwargs):
        cond = cls.get_cond(tid, **kwargs)

        query = (
            NewFile.select(
                NewFile,
                DcmFileInfo.email_sent_at,
                DcmFileInfo.investor_name,
                DcmFileInfo.browse_status,
                DcmFileInfo.edit_status,
                DcmFileInfo.fill_status,
                NewAdminUser.name.alias("user_name"),
            )
            .left_outer_join(DcmFileInfo, on=(NewFile.id == DcmFileInfo.file_id))
            .left_outer_join(NewAdminUser, on=(NewFile.uid == NewAdminUser.id))
            .where(cond)
            .order_by(NewFile.id.desc())
            .dicts()
        )
        query = query.offset(offset).limit(need_file_count)
        files = list(await pw_db.execute(query))
        file_ids = [file["id"] for file in files]
        question_query = (
            NewQuestion.select(
                NewQuestion.id,
                NewQuestion.fid,
                NewQuestion.mold,
                NewQuestion.ai_status,
                NewQuestion.health,
                NewQuestion.updated_utc,
                NewQuestion.fill_in_user,
                NewQuestion.data_updated_utc,
                NewQuestion.updated_utc,
                NewQuestion.fill_in_status,
                NewQuestion.progress,
                NewQuestion.status,
                NewQuestion.health,
                NewQuestion.ai_status,
                NewQuestion.name,
                NewQuestion.num,
                NewQuestion.mark_uids,
                NewQuestion.mark_users,
                fn.COALESCE(NewQuestion.origin_health, 1).alias("origin_health"),
                NewMold.name.alias("mold_name"),
            )
            .join(NewMold, on=(NewQuestion.mold == NewMold.id))
            .where(NewQuestion.fid.in_(file_ids))
            .order_by(NewQuestion.fid.desc(), NewQuestion.mold)
            .dicts()
        )
        question_by_fid = defaultdict(list)
        for question in await pw_db.execute(question_query):
            question_by_fid[question["fid"]].append(question)

        for file in files:
            file["questions"] = question_by_fid[file["id"]]

        return files

    @staticmethod
    def get_cond(tid, **kwargs):
        cond = NewFile.tree_id == tid
        if fill_status := kwargs["fill_status"]:
            cond &= DcmFileInfo.fill_status == fill_status
        if edit_status := kwargs["edit_status"]:
            cond &= DcmFileInfo.edit_status == edit_status
        if browse_status := kwargs["browse_status"]:
            cond &= DcmFileInfo.browse_status == browse_status
        if investor_name := kwargs["investor_name"]:
            cond &= DcmFileInfo.investor_name.contains(investor_name)
        if file_name := kwargs["file_name"]:
            cond &= NewFile.name.contains(file_name)

        return cond

    @classmethod
    async def get_all_files_count(cls, tid, **kwargs):
        cond = DcmFileTreeService.get_cond(tid, **kwargs)
        query = (
            NewFile.select(NewFile.id).left_outer_join(DcmFileInfo, on=(NewFile.id == DcmFileInfo.file_id)).where(cond)
        )
        return await pw_db.count(query)


class EmailPasswordCryptor:
    @staticmethod
    def encrypt(password):
        return base64.b64encode(aes_encrypt(password.encode(), get_config("citics_dcm.secret_key"), fill=True)).decode(
            "utf-8"
        )

    @staticmethod
    def decrypt(password):
        return aes_decrypt(base64.decodebytes(password.encode()), get_config("citics_dcm.secret_key"), True).decode(
            "utf-8"
        )


async def get_fill_data(file_ids):
    """
    获取用于集中簿记建档系统自动填写的数据
    :param file_ids:
    :return:
    """
    data = defaultdict(dict)
    bond_orders = await DcmBondOrderService.get_by_file_ids(file_ids)
    under_write_rates = await DcmUnderWriteRateService.get_by_file_ids(file_ids)

    for item in bond_orders:
        data[item["file_id"]] = {
            "file_id": item["file_id"],
            "email_sent_at": item["email_sent_at"],
            "project_id": item["project_id"],
            "bond_answer": AnswerReader(item["answer"]).to_json(JSONConverterStyle.PLAIN_TEXT),
            "bond_orders": item["bond_orders"],
        }

    for item in under_write_rates:
        data[item["file_id"]]["under_write_rates"] = item["under_write_rates"]

    return list(data.values())
