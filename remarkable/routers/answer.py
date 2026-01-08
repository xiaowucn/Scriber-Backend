import io
import logging
import os
import urllib.parse
from itertools import groupby
from typing import Annotated
from zipfile import ZipFile

from fastapi import APIRouter, Depends, HTTPException, Query
from speedy.pai_response import file_response
from starlette.status import HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND

from remarkable.answer.reader import AnswerReader
from remarkable.common.enums import ExportStatus
from remarkable.db import pw_db
from remarkable.dependencies import check_user_permission, get_current_user
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.models.query_helper import AsyncPagination
from remarkable.pw_models.answer_data import AnswerDataExport, NewAnswerData
from remarkable.pw_models.model import NewFileProject, NewFileTree, NewMold
from remarkable.pw_models.question import NewQuestion
from remarkable.routers.schemas import PaginateResSchema
from remarkable.routers.schemas.answer import (
    AnswerData,
    AnswerDataExportDbSchema,
    AnswerDataRes,
    BatchExportAnswerSchema,
    ExtractStatusSchema,
    SearchAnswerDataExportSchema,
)
from remarkable.service.answer import build_answer_data, edit_answer_data, fetch_all_answer_data, get_unique_data_items
from remarkable.worker.tasks import export_answer_data
from remarkable.worker.tasks.question_tasks import process_file_extract

answer_router = APIRouter(prefix="", tags=["answer"])
logger = logging.getLogger(__name__)


@answer_router.post(
    r"/files/{fid:int}/answer-data",
    description="提交要素答案",
)
async def update_answer_data(
    data: AnswerData,
    fid: int,
    user: NewAdminUser = Depends(check_user_permission("inspect")),
) -> AnswerDataRes:
    file = await NewFile.get_by_id(fid)
    if not file:
        raise HTTPException(HTTP_404_NOT_FOUND, "文件不存在")
    async with pw_db.atomic():
        res = await edit_answer_data(file, data.add, data.update, data.delete, user.id)
        ids = [add.get("id") for add in res.get("add", []) if add.get("id")]
        ids.extend([data.id for data in data.update + data.delete])
    return res


@answer_router.get(
    r"/files/{fid:int}/answer-data",
    description="获取要素答案",
    dependencies=[Depends(check_user_permission("inspect"))],
)
async def get_answer_data(fid: int) -> list:
    file = await NewFile.get_by_id(fid)
    if not file:
        raise HTTPException(HTTP_404_NOT_FOUND, "文件不存在")
    res = await build_answer_data(file)
    return res


@answer_router.post(
    r"/files/extract-complete", dependencies=[Depends(get_current_user)], status_code=HTTP_204_NO_CONTENT
)
async def extract_complete(data: ExtractStatusSchema):
    logger.info(f"extract-complete for file: {data.payload.doc_id}, mold: {data.payload.app_id}")
    file = await NewFile.get_by_cond(NewFile.studio_upload_id == data.payload.doc_id)
    if not file:
        logger.error(f"file {data.payload.doc_id} not found")
        return
    mold = await NewMold.get_by_cond(NewMold.studio_app_id == data.payload.app_id)
    if not mold:
        logger.error(f"schema {data.payload.app_id} not found")
        return
    process_file_extract.delay(file.id, file.studio_upload_id, mold.id, data.payload.success)


@answer_router.get(r"/files/{fid:int}/answer-result", dependencies=[Depends(check_user_permission("inspect"))])
async def gen_answer_data(fid: int):
    file = await NewFile.get_by_id(fid)
    if not file:
        raise HTTPException(HTTP_404_NOT_FOUND, "文件不存在")
    answer_datas = await pw_db.execute(
        NewAnswerData.select(
            NewAnswerData, NewMold.id.alias("mold_id"), NewMold.name.alias("mold_name"), NewMold.data.alias("mold_data")
        )
        .join(NewQuestion, on=NewAnswerData.qid == NewQuestion.id)
        .join(NewMold, on=NewQuestion.mold == NewMold.id)
        .where(NewQuestion.fid == fid)
        .order_by(NewQuestion.mold, NewAnswerData.qid)
    )

    if not answer_datas:
        raise HTTPException(HTTP_404_NOT_FOUND, "没有找到相关的答案数据")

    grouped_data = {}
    for qid, group in groupby(answer_datas, key=lambda x: x.qid):
        grouped_data[qid] = list(group)

    answer_readers = []
    for data_list in grouped_data.values():
        user_answer_items = []
        for data in data_list:
            unique_items = get_unique_data_items(data.data)
            user_answer_items.append(
                {
                    "key": data.key,
                    "score": data.score,
                    "data": unique_items,
                    "schema": data.schema,
                    "value": data.value,
                }
            )

        answer = {"schema": data_list[0].newquestion.newmold.mold_data, "userAnswer": {"items": user_answer_items}}
        answer_readers.append(AnswerReader(answer))

    if len(answer_readers) == 1:
        res = answer_readers[0].to_csv()
        filename = f"{urllib.parse.quote(file.name)}.csv"
    else:
        filename = f"{urllib.parse.quote(file.name)}.zip"
        res = io.BytesIO()
        with ZipFile(res, "w") as res_fp:
            for answer_reader in answer_readers:
                data = answer_reader.to_csv()
                res_fp.writestr(f"{answer_reader.mold_name}.csv", data)
    return file_response(
        content=res,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
        allow_etag=False,
    )


@answer_router.post(
    r"/projects/{p_id:int}/export-answer-data",
    description="批量导出答案数据",
    dependencies=[Depends(check_user_permission("inspect"))],
    response_model=AnswerDataExportDbSchema,
)
async def batch_export_answer_data(p_id: int, data: BatchExportAnswerSchema):
    project = await NewFileProject.find_by_id(p_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    file_ids = data.file_ids

    if data.tree_ids:
        file_ids += await NewFileTree.get_fids(*data.tree_ids)

    answer_datas = await fetch_all_answer_data(p_id=p_id, files_ids=file_ids)

    if not answer_datas:
        raise HTTPException(400, "暂没有可导出的答案")

    params = {
        "pid": p_id,
        "task_done": 0,
        "task_total": len(answer_datas),
        "files_ids": file_ids,
        "status": ExportStatus.DOING,
    }
    export_data = await AnswerDataExport.create(**params)

    export_answer_data.delay(p_id, file_ids, export_data.id)

    return export_data


@answer_router.get(
    "/projects/{p_id:int}/export-answer-data",
    description="导出答案数据任务列表",
    dependencies=[Depends(check_user_permission("inspect"))],
    response_model=PaginateResSchema[AnswerDataExportDbSchema],
)
async def get_export_answer_data_list(p_id: int, data: Annotated[SearchAnswerDataExportSchema, Query(...)]):
    project = await NewFileProject.find_by_id(p_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    cond = AnswerDataExport.pid == p_id
    if data.status:
        cond &= AnswerDataExport.status == data.status
    query = AnswerDataExport.select().where(cond).order_by(AnswerDataExport.id.desc())
    data = await AsyncPagination(query, page=data.page, size=data.size).data()
    return data


@answer_router.delete(
    "/projects/{p_id:int}/export-answer-data/{task_id:int}",
    description="删除导出答案数据任务",
    dependencies=[Depends(check_user_permission("inspect"))],
)
async def delete_export_answer_data(p_id: int, task_id: int):
    project = await NewFileProject.find_by_id(p_id)
    if not project:
        raise HTTPException(404, "项目不存在")
    export_data = await AnswerDataExport.find_by_id(task_id)
    if not export_data:
        raise HTTPException(404, "导出任务不存在")
    await export_data.soft_delete()
    return {}


@answer_router.get(
    "/projects/{p_id:int}/download-answer-data/{task_id:int}",
    description="下载导出答案",
    dependencies=[Depends(check_user_permission("inspect"))],
)
async def download_answer_data(p_id: int, task_id: int):
    project = await NewFileProject.find_by_id(p_id)
    if not project:
        raise HTTPException(404, "项目不存在")
    export_data = await AnswerDataExport.find_by_id(task_id)
    if not export_data:
        raise HTTPException(404, "导出任务不存在")
    if export_data.status != ExportStatus.FINISH:
        raise HTTPException(400, "导出任务未完成")
    return file_response(
        content=export_data.zip_path,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={urllib.parse.quote(os.path.split(export_data.zip_path)[1])}"
        },
        allow_etag=False,
    )
