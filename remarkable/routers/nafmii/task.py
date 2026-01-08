import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile, status
from peewee import Cast, fn
from speedy.peewee_plus.orm import or_
from starlette.requests import Request
from tornado.httputil import HTTPFile

from remarkable.common.constants import AIStatus, HistoryAction, PDFParseStatus
from remarkable.common.enums import NafmiiEventStatus, NafmiiEventType, NafmiiTaskType
from remarkable.common.redis_cache import NAFMII_TASK_LOCK_KEY
from remarkable.common.util import arun_singleton_task, generate_timestamp
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.dependencies import check_user_permission, get_current_user, get_nafmii_event
from remarkable.models.nafmii import NafmiiFileInfo, TaskFlag
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.plugins.nafmii.enums import DSFileType
from remarkable.plugins.nafmii.services import NafmiiFileService, SearchFileSchema
from remarkable.pw_models.model import NewFileProject, NewFileTree, NewHistory
from remarkable.pw_models.question import NewQuestion
from remarkable.routers.nafmii.dependency import get_menu, get_project
from remarkable.routers.nafmii.schema import CreateTaskSchema, PredictFileSchema, SummarySchema
from remarkable.worker.tasks import convert_or_parse_file, process_file

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    r"/tasks", description="识别任务界面上传文件", dependencies=[Depends(check_user_permission("manage_task"))]
)
async def create_task(
    file: UploadFile,
    form: Annotated[CreateTaskSchema, Form(...)],
    user: Annotated[NewAdminUser, Depends(get_current_user)],
    request: Request,
):
    project = await get_project(form.file_type)
    post_file = HTTPFile(filename=file.filename or "", body=await file.read())
    async with pw_db.atomic():
        new_file = await NafmiiFileService.create_file(
            post_file,
            project,
            project.rtree_id,
            mold_id=project.default_molds[0] if project.default_molds else None,
            task_types=form.task_types,
            uid=user.id,
            source="本地上传",
            keywords=form.keywords,
        )

        await NewHistory.save_operation_history(
            None,
            user.id,
            HistoryAction.NAFMII_DEFAULT.value,
            user.name,
            meta=None,
            nafmii=get_nafmii_event(
                request=request,
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.ADD.value,
                menu="识别任务管理",
                subject="识别任务",
                content=f"上传文件《{new_file.name}》成功",
            ),
        )
    await process_file(new_file)


@router.get(r"/tasks", description="搜索识别任务文件", dependencies=[Depends(check_user_permission("manage_task"))])
async def search_files(
    schema: Annotated[SearchFileSchema, Query(...)],
    user: Annotated[NewAdminUser, Depends(get_current_user)],
    request: Request,
) -> dict:
    """搜索识别任务文件接口"""
    # 调用服务进行搜索
    res = await NafmiiFileService.search_all(schema, user=user, mark_user=user)

    # 检查是否是自动触发
    if request.headers.get("x-trigger-source") == "auto":
        return res

    # 记录操作历史
    if schema.task_id or schema.filename or schema.file_type:
        subject = "识别任务管理列表"
        content = "查询识别任务管理列表成功"
    else:
        subject = "识别任务管理列表页"
        content = "查看识别任务管理列表页成功"

    await NewHistory.save_operation_history(
        None,
        user.id,
        HistoryAction.NAFMII_DEFAULT.value,
        user.name,
        meta=None,
        nafmii=get_nafmii_event(
            request=request,
            status=NafmiiEventStatus.SUCCEED.value,
            type=NafmiiEventType.VIEW.value,
            menu="识别任务管理",
            subject=subject,
            content=content,
        ),
    )

    return res


@router.get(r"/summary", description="识别任务概览", dependencies=[Depends(check_user_permission("manage_task"))])
async def get_summary(user: Annotated[NewAdminUser, Depends(get_current_user)]) -> SummarySchema:
    query = NewFile.select().where(NewFile.uid == user.id)
    total = await pw_db.count(query)
    succeed = await pw_db.count(
        query.where(
            NewFile.pdf_parse_status == PDFParseStatus.COMPLETE,
            or_(
                fn.EXISTS(
                    NewQuestion.select().where(
                        NewQuestion.fid == NewFile.id,
                        NewQuestion.ai_status == AIStatus.FINISH,
                        fn.JSON_CONTAINS(NewFile.molds, Cast(NewQuestion.mold, "JSON"), "$"),
                    )
                ),
                ~fn.EXISTS(
                    NewQuestion.select().where(
                        NewQuestion.fid == NewFile.id,
                        fn.JSON_CONTAINS(NewFile.molds, Cast(NewQuestion.mold, "JSON"), "$"),
                    )
                ),
            ),
        )
    )
    predicting = await pw_db.count(
        query.where(
            NewFile.pdf_parse_status == PDFParseStatus.COMPLETE,
            fn.EXISTS(
                NewQuestion.select().where(
                    NewQuestion.fid == NewFile.id,
                    NewQuestion.ai_status == AIStatus.DOING,
                    fn.JSON_CONTAINS(NewFile.molds, Cast(NewQuestion.mold, "JSON"), "$"),
                )
            ),
        )
    )

    return {
        "total_file": total,
        "predicting": predicting,
        "predicted": succeed,
    }


@router.get(r"/file-types", description="识别任务文件类型")
def get_file_types() -> list[str]:
    data = list(get_config("nafmii.file_types") or [])
    if DSFileType.DS_D004.value in data:
        data.remove(DSFileType.DS_D004.value)
    return data


@router.post(
    r"/files/execute",
    description="文件批量预测/审核",
    dependencies=[Depends(check_user_permission("manage_all", "manage_task"))],
)
async def execute_files(
    schema: PredictFileSchema,
    user: Annotated[NewAdminUser, Depends(get_current_user)],
    menu: Annotated[str, Depends(get_menu)],
    request: Request,
) -> None:
    """文件批量预测/审核接口"""
    if not (schema.dirs or schema.fids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid input parameters.")

    fids = schema.fids.copy()
    fids.extend(await NewFileTree.get_fids(*schema.dirs))

    lock_expired: int = get_config("web.run_lock_expired", 600)  # type: ignore

    for fid in sorted(fids, reverse=True):
        get_lock, _ = await arun_singleton_task(
            _execute_single_file,
            fid,
            schema.merge_strategy,
            schema.flag,
            lock_expired=lock_expired,
            lock_key=NAFMII_TASK_LOCK_KEY.format(task_id=fid),
        )

        if not get_lock:
            await NewHistory.save_operation_history(
                None,
                user.id,
                HistoryAction.NAFMII_DEFAULT.value,
                str(user.name),
                meta=None,
                nafmii=get_nafmii_event(
                    request=request,
                    status=NafmiiEventStatus.FAILED.value,
                    type=NafmiiEventType.MODIFY.value,
                    menu=menu,
                    subject="识别任务",
                    content=f"重新识别{fid}失败",
                ),
            )
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="操作过于频繁")

    await NewHistory.save_operation_history(
        None,
        user.id,
        HistoryAction.NAFMII_DEFAULT.value,
        str(user.name),
        meta=None,
        nafmii=get_nafmii_event(
            request=request,
            status=NafmiiEventStatus.SUCCEED.value,
            type=NafmiiEventType.MODIFY.value,
            menu=menu,
            subject="识别任务",
            content=f"重新识别{fids[0]}成功",
        ),
    )


async def _execute_single_file(fid: int, merge_strategy: str, flag: TaskFlag):
    """执行单个文件的预测任务"""

    file = await NewFile.get_by_id(fid)
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    # todo: 暂不考虑批注文件不一致的问题, 后续可能调整为本地和文件服务都存储一份
    # await pw_db.execute(NafmiiFileInfo.update(revise_file_path=None, flag=flag).where(NafmiiFileInfo.file_id == fid))
    await pw_db.execute(NafmiiFileInfo.update(flag=flag).where(NafmiiFileInfo.file_id == fid))
    if flag == TaskFlag.only_push:
        if file.pdf_parse_status != PDFParseStatus.COMPLETE:  # 如果是重新推送，且解析状态不是解析成功
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="文件解析异常，请重新识别或联系运维人员处理"
            )
        if await pw_db.exists(
            NewQuestion.select().where(NewQuestion.fid == fid, NewQuestion.ai_status != AIStatus.FINISH)
        ):  # 如果是重新推送，且预测状态不是解析成功
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="文件预测异常，请重新识别或联系运维人员处理"
            )

        from remarkable.plugins.nafmii.tasks import run_nafmii_task

        run_nafmii_task.delay(file.id)
        return
    else:
        await pw_db.execute(
            NewQuestion.update(updated_utc=generate_timestamp(), ai_status=AIStatus.TODO).where(NewQuestion.fid == fid)
        )
        await pw_db.execute(
            NewFile.update(updated_utc=generate_timestamp(), pdf_parse_status=PDFParseStatus.PENDING).where(
                NewFile.id == fid, NewFile.pdf_parse_status != PDFParseStatus.COMPLETE
            )
        )

    logger.info(f"{file.id=}, {file.name=} preset nafmii answer")

    if file.pdf_parse_status != PDFParseStatus.COMPLETE:
        convert_or_parse_file(file)
        return

    from remarkable.hooks.nafmii import NafmiiInsightHook

    await NafmiiInsightHook(file).__call__()

    task_types = await pw_db.scalar(
        NafmiiFileInfo.select(NafmiiFileInfo.task_types).where(NafmiiFileInfo.file_id == fid)
    )

    if task_types and NafmiiTaskType.T001 in task_types:
        from remarkable.worker.tasks.predict_tasks import preset_answer_by_fid_task

        preset_answer_by_fid_task.delay(fid, force_predict=True, file_answer_merge_strategy=merge_strategy)


@router.get(
    r"/projects/{pid:int}/files",
    description="搜索识别任务文件",
    dependencies=[Depends(check_user_permission("manage_all"))],
)
async def search_files_with_project(
    pid: int,
    schema: Annotated[SearchFileSchema, Query(...)],
    user: Annotated[NewAdminUser, Depends(get_current_user)],
    request: Request,
):
    """搜索识别任务文件接口（带项目ID）"""
    project = await NewFileProject.find_by_id(pid)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")

    res = await NafmiiFileService.search_all(schema, mark_user=user, project=project)

    if request.headers.get("x-trigger-source") == "auto":
        return res

    if any([schema.task_id, schema.task_types, schema.filename]):
        subject = "识别任务列表"
        content = "查询识别任务列表成功"
    else:
        subject = "识别任务列表页面"
        content = "查看识别任务列表成功"

    await NewHistory.save_operation_history(
        None,
        user.id,
        HistoryAction.NAFMII_DEFAULT.value,
        user.name,
        meta=None,
        nafmii=get_nafmii_event(
            request=request,
            status=NafmiiEventStatus.SUCCEED.value,
            type=NafmiiEventType.VIEW.value,
            menu="识别文件管理",
            subject=subject,
            content=content,
        ),
    )
    return res
