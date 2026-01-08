import logging
import os

from utensils.syncer import sync

from remarkable.common.constants import MoldType, PDFParseStatus
from remarkable.common.storage import localstorage
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.pw_models.model import NewMold
from remarkable.service.studio import (
    add_file_using_studio,
    re_extract_by_studio,
    remove_file_from_studio_app,
    upload_pdf_to_studio,
)
from remarkable.worker.app import app

logger = logging.getLogger(__name__)


@app.task
@sync
async def re_extract_answer_by_studio(fid: int, molds: list[int]):
    file: NewFile = await NewFile.find_by_id(fid)
    if not file:
        logger.error(f"file not exists: {fid}")
        return
    if file.studio_upload_id is not None:
        await re_extract_by_studio(file.id, file.studio_upload_id, molds)
    else:
        upload_file_to_studio_extract.delay(file.id, molds)


@app.task
@sync
async def process_extract_answer_by_studio(
    fid: int, add_molds: list[int], delete_molds: list[int] | None = None, other_molds: list[int] | None = None
):
    file: NewFile = await NewFile.find_by_id(fid)
    if not file:
        logger.error(f"file not exists: {fid}")
        return
    if file.pdf_parse_status != PDFParseStatus.COMPLETE:
        logger.error(f"file pdf parse status not complete: {fid}")
        return
    if file.studio_upload_id is not None:
        if add_molds:
            await add_file_using_studio(file.id, file.studio_upload_id, add_molds)
        if delete_molds:
            await remove_file_from_studio_app(file.id, file.studio_upload_id, delete_molds)
        if other_molds:
            await re_extract_by_studio(file.id, file.studio_upload_id, other_molds)
    else:
        upload_file_to_studio_extract.delay(file.id, add_molds)


@app.task
@sync
async def upload_file_to_studio_extract(fid: int, molds: list[int]):
    file: NewFile = await NewFile.find_by_id(fid)
    if not file:
        logger.error(f"file not exists: {fid}")
        return
    if await pw_db.exists(
        NewMold.select().where(NewMold.id.in_(molds), NewMold.mold_type.in_([MoldType.LLM, MoldType.HYBRID]))
    ):
        # 确保文件名以 .pdf 结尾
        filename = file.name
        if not filename.lower().endswith(".pdf"):
            base_name = os.path.splitext(filename)[0]
            filename = base_name + ".pdf"
        file_meta = {
            "filename": filename,
            "body": localstorage.read_file(file.pdf_path()),
        }
        upload_id = await upload_pdf_to_studio(file_meta)
        await file.update_(studio_upload_id=upload_id)
        await add_file_using_studio(file.id, file.studio_upload_id, molds)
