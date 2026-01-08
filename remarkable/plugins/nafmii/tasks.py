import logging

import httpx
from tornado.httputil import HTTPFile
from utensils.util import generate_timestamp

from remarkable.common.enums import NafmiiTaskType
from remarkable.common.nafmii_revise import export_annotation_to_file
from remarkable.common.redis_cache import NAFMII_TASK_LOCK_KEY
from remarkable.common.util import loop_wrapper
from remarkable.config import get_config
from remarkable.db import init_rdb, pw_db
from remarkable.models.nafmii import FileAnswer, NafmiiFileInfo, NafmiiSystem, TaskFlag
from remarkable.models.new_file import NewFile
from remarkable.plugins.nafmii.enums import TaskStatus
from remarkable.plugins.nafmii.pipeline import prepare_nafmii_answer
from remarkable.plugins.nafmii.services import FastDFSClient
from remarkable.predictor.mold_schema import MoldSchema
from remarkable.pw_models.model import MoldWithFK
from remarkable.pw_models.question import QuestionWithFK
from remarkable.worker.app import app

logger = logging.getLogger(__name__)


@app.task
@loop_wrapper
async def run_nafmii_task(fid):
    await nafmii_post_task(fid)
    init_rdb().delete(f"lock:{NAFMII_TASK_LOCK_KEY.format(task_id=fid)}")


async def nafmii_post_task(fid):
    file = await NewFile.get_by_id(fid, prefetch_queries=[NafmiiFileInfo.select(), NafmiiSystem.select()])
    file_info: NafmiiFileInfo = file.file_info[0]

    if file_info.flag == TaskFlag.skip_push:  # 只重新解析的话不需要生成批注文件, 也不需要推送
        return

    binary_data = await export_comment(file.id)

    with FastDFSClient(file_info.sys) as client:
        suffix = ".docx" if file.is_docx else ".pdf"
        file_path = client.save_file(HTTPFile(body=binary_data, filename=f"revise{suffix}"))

    await file_info.update_(revise_file_path=file_path)

    if file_info.sys.id == 0:
        return
    if not (url := get_config("nafmii.api.push")):
        return
    logger.info(f"start to push answer to nafmii {url=}")
    answer = await prepare_nafmii_answer(file)
    try:
        async with httpx.AsyncClient(timeout=10, transport=httpx.AsyncHTTPTransport(verify=False, retries=3)) as client:
            rsp = await client.post(
                url,
                json={"task_id": str(file.id), "task_status": TaskStatus.DONE.value, "afile_id": file_path} | answer,
            )
            if rsp.is_success:
                await file_info.update_(push_answer_at=generate_timestamp())
            else:
                logger.error("failed to push answer to nafmii")
    except Exception as e:
        logger.exception(e)
        await file_info.update_(push_answer_at=-1)
    finally:
        logger.info(f"finish to push answer to nafmii {url=}")


async def export_comment(fid: int) -> bytes:
    file = await NewFile.find_by_id(fid)
    task_types = await pw_db.scalar(NafmiiFileInfo.select(NafmiiFileInfo.task_types).where(NafmiiFileInfo.file == fid))

    mold_schema, items = None, None
    if NafmiiTaskType.T001 in task_types:
        question = await pw_db.prefetch_one(
            QuestionWithFK.select(QuestionWithFK.answer, QuestionWithFK.mold).where(QuestionWithFK.file == file),
            MoldWithFK.select(),
        )
        mold_schema = MoldSchema(question.mold.data)
        items = question.answer["userAnswer"]["items"]

    file_answer = await FileAnswer.find_by_kwargs(fid=fid)

    binary_data = export_annotation_to_file(task_types, file, mold_schema, items, file_answer)

    return binary_data
