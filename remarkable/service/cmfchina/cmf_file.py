from operator import and_

import peewee
from peewee import JOIN

from remarkable.common.constants import AIStatus, PDFParseStatus, SearchPDFParseStatus, TimeType
from remarkable.models.cmf_china import CmfFiledFileInfo, CmfModelFileRef
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.pw_models.model import NewFileProject
from remarkable.pw_models.question import NewQuestion
from remarkable.service.new_file import NewFileService


class CmfFileService:
    @classmethod
    def file_query(
        cls,
        tree_ids: list[int] = None,
        mold: int = None,
        pid: int = None,
        fileid: int = None,
        filename: str = None,
        user_name: str = None,
        uid: int = None,
        is_answered: bool = None,
        question_status: int = None,
        is_manager: bool = True,
        time_type: TimeType = TimeType.CREATE.value,
        start_at: int = None,
        end_at: int = None,
        order_by: str = "-id",
        pdf_parse_status: int = None,
        ai_status: int = None,
        mold_ids: list[int] = None,
        search_mid: int = None,
    ):
        cond = NewFileService.query_cond(
            tree_ids,
            mold,
            pid,
            fileid,
            filename,
            uid,
            is_answered,
            question_status,
            is_manager,
            mold_ids,
            search_mid,
        )
        query = NewFile.select(
            NewFile,
            NewAdminUser.name.alias("user_name"),
        ).join(NewFileProject, on=(NewFileProject.id == NewFile.pid))
        if user_name:
            query = query.join(
                NewAdminUser,
                on=and_(NewAdminUser.id == NewFile.uid, NewAdminUser.name.contains(user_name)),
                include_deleted=True,
            )
        else:
            query = query.join(
                NewAdminUser, join_type=JOIN.LEFT_OUTER, on=(NewAdminUser.id == NewFile.uid), include_deleted=True
            )

        if ai_status is not None:
            if ai_status == 0:
                and_cond = and_(
                    NewQuestion.fid == NewFile.id, NewQuestion.ai_status.in_([AIStatus.TODO, AIStatus.UNCORRELATED])
                )
            else:
                and_cond = and_(NewQuestion.fid == NewFile.id, NewQuestion.ai_status == ai_status)
            query = query.join(
                NewQuestion,
                on=and_cond,
                include_deleted=True,
            )
        else:
            query = query.join(
                NewQuestion, join_type=JOIN.LEFT_OUTER, on=(NewQuestion.fid == NewFile.id), include_deleted=True
            )
        if pdf_parse_status is not None:
            if pdf_parse_status == SearchPDFParseStatus.PARSING:
                cond.append(NewFile.pdf_parse_status.in_([SearchPDFParseStatus.PARSING, PDFParseStatus.PARSED]))
            else:
                cond.append(NewFile.pdf_parse_status == pdf_parse_status)
        if time_type == TimeType.CREATE:
            if start_at:
                cond.append(NewFile.created_utc >= start_at)
            if end_at:
                cond.append(NewFile.created_utc < end_at)
        else:
            if start_at:
                cond.append(NewFile.updated_utc >= start_at)
            if end_at:
                cond.append(NewFile.updated_utc < end_at)

        return query.where(*cond).group_by(NewFile.id, NewAdminUser.name).order_by(getattr(NewFile, order_by))

    @classmethod
    def model_file_query(
        cls,
        mold: int = None,
        pid: int = None,
        model_id: int = None,
    ):
        cond = []
        if mold:
            cond.append(NewFile.molds.contains(mold))
        else:
            cond.append(NewFile.molds == [])
        if pid:
            cond.append(NewFile.pid == pid)
        query = (
            NewFile.select(
                NewFile,
                NewAdminUser.name.alias("user_name"),
                CmfModelFileRef.answer.alias("interface_answer"),
                CmfModelFileRef.status.alias("interface_status"),
            )
            .join(NewFileProject, on=(NewFileProject.id == NewFile.pid))
            .join(CmfModelFileRef, on=and_(CmfModelFileRef.fid == NewFile.id, CmfModelFileRef.model == model_id))
            .join(NewAdminUser, join_type=JOIN.LEFT_OUTER, on=(NewAdminUser.id == NewFile.uid), include_deleted=True)
        )
        return query.where(*cond).order_by(NewFile.id.desc())

    @classmethod
    def filed_file_query(
        cls,
        filename: str = None,
        projectname: str = None,
        fid: int = None,
        user_name: str = None,
        pdf_parse_status: int = None,
        ai_status: int = None,
        time_type: TimeType = TimeType.CREATE.value,
        start_at: str = None,
        end_at: str = None,
        order_by: str = "-id",
        sysfrom: str = None,
    ):
        cond = []
        if filename:
            cond.append(NewFile.name.contains(filename))
        if projectname:
            cond.append(NewFileProject.name.contains(projectname))
        if fid:
            cond.append(NewFile.id == fid)
        if pdf_parse_status is not None:
            if pdf_parse_status == SearchPDFParseStatus.PARSING:
                cond.append(NewFile.pdf_parse_status.in_([SearchPDFParseStatus.PARSING, PDFParseStatus.PARSED]))
            else:
                cond.append(NewFile.pdf_parse_status == pdf_parse_status)

        if time_type == TimeType.CREATE:
            if start_at:
                cond.append(NewFile.created_utc >= int(start_at))
            if end_at:
                cond.append(NewFile.created_utc < int(end_at))
        else:
            if start_at:
                cond.append(NewFile.updated_utc >= int(start_at))
            if end_at:
                cond.append(NewFile.updated_utc < int(end_at))
        if sysfrom:
            cond.append(NewFile.sysfrom == sysfrom)
        query = (
            NewFile.select(
                NewFile,
                NewAdminUser.name.alias("user_name"),
                CmfFiledFileInfo.status.alias("filed_status"),
                CmfFiledFileInfo.fail_info.alias("filed_fail_info"),
                peewee.Case(
                    predicate=None,
                    expression_tuples=((NewFileProject.name.contains("_cmf_china_filed_file_"), ""),),
                    default=NewFileProject.name,
                ).alias("project_name"),
            )
            .join(NewFileProject, on=(NewFileProject.id == NewFile.pid))
            .join(CmfFiledFileInfo, on=(CmfFiledFileInfo.fid == NewFile.id))
        )
        if user_name:
            query = query.join(
                NewAdminUser,
                on=and_(NewAdminUser.id == NewFile.uid, NewAdminUser.name.contains(user_name)),
                include_deleted=True,
            )
        else:
            query = query.join(
                NewAdminUser,
                join_type=JOIN.LEFT_OUTER,
                on=(NewAdminUser.id == NewFile.uid),
                include_deleted=True,
            )
        if ai_status is not None:
            if ai_status == 0:
                and_cond = and_(
                    NewQuestion.fid == NewFile.id, NewQuestion.ai_status.in_([AIStatus.TODO, AIStatus.UNCORRELATED])
                )
            else:
                and_cond = and_(NewQuestion.fid == NewFile.id, NewQuestion.ai_status == ai_status)
            query = query.join(
                NewQuestion,
                on=and_cond,
                include_deleted=True,
            )
        return query.where(*cond).order_by(getattr(NewFile, order_by))
