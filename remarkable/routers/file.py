import logging
from http.client import HTTPException
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from starlette.status import HTTP_404_NOT_FOUND

from remarkable.db import pw_db
from remarkable.dependencies import check_any_permissions, get_current_user
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.pw_models.model import NewFileProject
from remarkable.pw_models.question import QuestionWithFK
from remarkable.routers import DEBUG_WEBIF, debug_route
from remarkable.routers.schemas.file import FileAuditStatusSchema
from remarkable.routers.schemas.law import ScenarioIdsSchema
from remarkable.service.file_list_status import fill_files_status

file_router = APIRouter(prefix="/files", tags=["file"])
logger = logging.getLogger(__name__)


@file_router.get("/synced")
async def chatdoc_files(
    form: Annotated[ScenarioIdsSchema, Query(...)],
    user: NewAdminUser = Depends(
        check_any_permissions("manage_law", "customer_rule_participate", "customer_rule_review")
    ),
):
    cond = (NewFile.uid == user.id) | NewFile.pid.in_(
        NewFileProject.select(NewFileProject.id).where(((NewFileProject.uid == user.id) | NewFileProject.public))
    )
    if form.scenario_ids:
        cond &= NewFile.scenario_id.in_(form.scenario_ids)
    query = (
        NewFile.select(NewFile.id, NewFile.name, NewFile.chatdoc_unique)
        .where(NewFile.scenario_id.is_null(False), cond, NewFile.chatdoc_unique.is_null(False))
        .dicts()
    )
    files = await pw_db.execute(query)
    return {"files": list(files)}


@file_router.get(r"/{file_id:int}/audit-status", response_model=FileAuditStatusSchema)
async def get_file_audit_status(file_id, user: NewAdminUser = Depends(get_current_user)):
    file = await NewFile.get_by_id(
        file_id,
        QuestionWithFK.select(
            QuestionWithFK.id, QuestionWithFK.fid, QuestionWithFK.ai_status, QuestionWithFK.updated_utc
        ),
    )
    if not file:
        raise HTTPException(HTTP_404_NOT_FOUND)

    file_status = {
        "id": file.id,
        "questions": file.questions,
        "scenario": file.scenario_id,
        "task_type": file.task_type,
    }
    await fill_files_status([file_status])
    return file_status


if DEBUG_WEBIF:
    from remarkable.service.law_chatdoc import upload_pdf_with_interdoc_to_chatdoc

    @debug_route.get("/{file_id:int}/upload")
    async def sync_file_to_chatdoc(
        file_id,
        user: NewAdminUser = Depends(
            check_any_permissions("manage_prj", "manage_law", "customer_rule_participate", "customer_rule_review")
        ),
    ):
        file = await NewFile.get_by_id(file_id)

        chatdoc_unique = await upload_pdf_with_interdoc_to_chatdoc(file)
        await pw_db.update(file, chatdoc_unique=chatdoc_unique)
        return {"chatdoc_unique": chatdoc_unique}
