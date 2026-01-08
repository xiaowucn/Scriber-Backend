import logging
import os
import shutil
import tempfile
import uuid
from dataclasses import asdict
from typing import Literal

import celery
import msgspec
import requests
from pdfparser.pdftools.convert_scanned_pdf import ScannedPDFRestore
from utensils.hash import md5sum
from utensils.syncer import sync

from remarkable import config
from remarkable.common.constants import LLMStatus, PDFFlag, PDFParseStatus
from remarkable.common.enums import ClientName, TaskType
from remarkable.common.exceptions import CustomError, PdfinsightError, PushError
from remarkable.common.redis_cache import QUESTION_POST_PIPE_KEY
from remarkable.common.storage import localstorage
from remarkable.common.util import (
    loop_wrapper,
    read_zip_first_file,
    release_parse_file_lock,
    run_singleton_task,
)
from remarkable.config import get_config
from remarkable.converter.utils import generate_cache_for_diff
from remarkable.db import init_rdb, peewee_transaction_wrapper, pw_db
from remarkable.hooks import InsightFinishHook, InsightStartHook
from remarkable.models.new_file import NewFile
from remarkable.plugins.cgs.services.comment import remove_docx_blank_comments
from remarkable.plugins.fileapi.common import get_pdf_pages
from remarkable.plugins.fileapi.worker import create_docx, create_pdf, create_pdf_cache
from remarkable.pw_models.embedding import Embedding
from remarkable.pw_models.model import NewFileProject, NewMold, NewTimeRecord
from remarkable.pw_models.question import NewQuestion
from remarkable.security import authtoken
from remarkable.service.chatgpt import OpenAIClient
from remarkable.service.embedding import Document, InterdocHelper
from remarkable.service.new_file import NewFileService
from remarkable.service.new_question import NewQuestionService, run_extract_answer
from remarkable.service.studio import (
    get_extract_result,
)
from remarkable.worker.app import app
from remarkable.worker.tasks.predict_tasks import judge_file

logger = logging.getLogger(__name__)


@app.task
@loop_wrapper
async def cache_pdf_file(file_id: int, force=False, by_pdfinsight=None):
    file = await NewFile.find_by_id(file_id)
    if not file or not file.pdf:
        logger.error(f"file not exists: {file_id}")
        return

    await cache_pdf_file_process(file, force=force, by_pdfinsight=by_pdfinsight)


async def cache_pdf_file_process(file, force=False, by_pdfinsight=None):
    try:
        # create cache data to speed up text_in_box api
        await create_pdf_cache(file, force=force, by_pdfinsight=by_pdfinsight)
        await NewTimeRecord.update_record(file.id, "pdf_parse_stamp")
    except Exception as exp:
        logger.exception(exp)


@app.task
@loop_wrapper
@peewee_transaction_wrapper
async def convert_to_pdf(fid, ocr=False, garbled=False):
    logger.info(f"convert_to_pdf for fid: {fid}")
    file = await NewFile.find_by_id(fid)
    try:
        await create_pdf(file)
    except Exception as exp:
        logger.exception(exp)
        file.pdf_flag = PDFFlag.FAILED_CONVERT.value
        await file.update_(pdf_flag=file.pdf_flag, pdf_parse_status=PDFParseStatus.FAIL)
        release_parse_file_lock(file.hash)
        raise

    file.pdf_flag = PDFFlag.CONVERTED.value
    pdf_data = localstorage.read_file(file.pdf_path())
    page = get_pdf_pages(pdf_data)
    await file.update_(pdf_flag=file.pdf_flag, pdf=file.pdf, page=page, meta_info=file.meta_info)
    return {
        "id": file.id,
        "name": file.pdf_name,
        "hash": file.hash,
        "path": file.raw_pdf_path() or file.pdf_path(),
        "ocr": ocr,
        "garbled": garbled,
    }


async def convert_to_docx(file):
    try:
        docx_hash = create_docx(file)
    except Exception as exp:
        logger.exception(exp)
        return None
    await file.update_(docx=docx_hash)
    return docx_hash


@app.task
@loop_wrapper
async def convert_to_docx_task(fid):
    file = await NewFile.find_by_id(fid)
    await convert_to_docx(file)


@app.task
@loop_wrapper
async def remove_docx_blank_comments_task(fid):
    async with pw_db.atomic():
        file = await NewFile.get_by_id(fid, for_update=True)
        file.pdf_parse_status = PDFParseStatus.CLEAN_FILE_PARSING
        await file.update_(only=["pdf_parse_status"])
        if path := file.docx_path():
            with tempfile.TemporaryDirectory(dir=config.get_config("web.tmp_dir")) as tmp_dir:
                if res := await remove_docx_blank_comments(
                    file.id,
                    localstorage.mount(path),
                    localstorage.mount(file.pdfinsight_path()),
                    tmp_dir,
                ):
                    file.meta_info["clean_file"] = asdict(res.clean_file)
                    logger.info(f"fid:{fid}, clean_files:{res.clean_file}")
        await file.update_(only=["meta_info"])


@app.task
@loop_wrapper
async def scanned_pdf_restore(fid):
    logger.info(f"scanned_pdf_restore for fid: {fid}")
    file = await NewFile.get_by_id(fid)
    try:
        with tempfile.NamedTemporaryFile() as tmp_file:
            pdf_path = file.pdf_path(abs_path=True)
            output_path = tmp_file.name
            ScannedPDFRestore(pdf_path, output_path, pages=None, ocr_name="pai", include_texts=True).convert()

            file.revise_pdf = md5sum(output_path)
            localstorage.create_dir(os.path.dirname(file.revise_pdf_path(abs_path=True)))
            shutil.copy(output_path, file.revise_pdf_path(abs_path=True))

        await pw_db.update(file, only=["revise_pdf"])
    except Exception as exp:
        logger.exception(exp)
        meta_info = file.meta_info or {}
        meta_info["revise_pdf"] = "failed"
        await pw_db.update(file, meta_info=meta_info)


async def embed_file(file: NewFile):
    data = msgspec.json.decode(read_zip_first_file(file.pdfinsight_path(abs_path=True)))
    data = InterdocHelper.process(data)
    doc = Document(data)
    contents = doc.make_contents()

    records = []
    client = OpenAIClient()
    embeddings = client.get_embddings([content["text"] for content in contents])
    for content, embedding in zip(contents, embeddings):
        records.append({**content, "embedding": embedding, "file_id": file.id})
    await Embedding.bulk_insert(
        records,
        on_conflict={
            "action": "update",
            "conflict_target": ("file_id", "index"),
            "preserve": ("file_id", "index", "created_utc"),
        },
    )


async def get_force_ocr(mold_ids: list[int]):
    force_ocr_mold_list = get_config("web.force_ocr_mold_list") or []
    force_ocr = False
    for mold_id in mold_ids:
        mold = await NewMold.find_by_id(mold_id)
        mold_name = mold.name if mold is not None else None
        if mold_id in [i for i in force_ocr_mold_list if isinstance(i, int)] or mold_name in [
            i for i in force_ocr_mold_list if isinstance(i, str)
        ]:
            force_ocr = True
            break

    return force_ocr


async def process_file(
    file,
    force_parse_file=False,
    force_predict=False,
    ocr=None,
    garbled=False,
    force_ocr_pages=None,
    force_as_pdf=False,
    create_cache=False,
):
    """
    非阻塞函数

    非worker task, 仍在web process 中运行, 负责下发worker任务
    """
    if get_config("customer_settings.parse_excel") and (
        project_name := get_config("customer_settings.default_tree_name")
    ):
        from remarkable.worker.tasks.parse_excel_tasks import parse_excel_task

        project = await NewFileProject.find_by_kwargs(name=project_name)
        assert project, f"{project_name=}未找到，请检查配置"
        if project.id == file.pid:
            # 广发基金项目特殊配置：指定项目下的文件走 Excel 解析流程
            return run_singleton_task(parse_excel_task, file.id, project.id, project_name)

    if (
        force_parse_file
        or not file.pdfinsight
        or file.pdf_parse_status
        in (
            PDFParseStatus.PENDING,
            PDFParseStatus.FAIL,
            PDFParseStatus.CANCELLED,
        )
    ):
        logger.info(
            "file: %s, force_parse_file: %s, pdfinsight: %s, pdf_parse_status: %s",
            file.id,
            force_parse_file,
            file.pdfinsight,
            file.pdf_parse_status,
        )
        if force_ocr_pages is None:
            force_ocr_pages = get_config("app.auth.pdfinsight.force_ocr_pages")
        if ocr is None:
            ocr = await get_force_ocr(file.molds)

        get_lock, _ = run_singleton_task(
            convert_or_parse_file,
            file,
            ocr=ocr,
            garbled=garbled,
            lock_key=f"convert_or_parse_file:{file.hash}",
            force_ocr_pages=force_ocr_pages,
            force_as_pdf=force_as_pdf,
        )
        if get_lock:
            await file.update_(
                pdf_parse_status=PDFParseStatus.PARSING
                if get_config("web.parse_pdf", True)
                else PDFParseStatus.COMPLETE
            )

            await InsightStartHook(file).__call__()
        return None

    logger.warning(f"file {file.id} is in status {file.pdf_parse_status}, no need to start_process_file again")
    process_file_predict.delay(file.id, force_predict, create_cache)
    return None


@app.task
@loop_wrapper
async def process_file_predict(fid: int, force_predict: bool = False, create_cache: bool = False):
    logger.info(f"start_process_file_predict for file: {fid}")
    file = await NewFile.find_by_id(fid, include_deleted=True)
    if not file:
        logger.error(f"file {fid} not found")
        return

    await InsightFinishHook(file).__call__()

    if get_config("ai.openai.embedding_model"):
        await embed_file(file)

    # 确保先缓存完再执行预测, 保证解析状态和预测状态一致性
    if create_cache:
        await cache_pdf_file_process(file, force=True)

    if file.molds:
        if get_config("web.preset_answer"):
            from remarkable.worker.tasks.predict_tasks import preset_answer_by_fid_task

            logger.info(f"web.preset_answer is True, start preset_answer for {file.id}")
            preset_answer_by_fid_task.apply_async(
                args=[file.id], kwargs={"force_predict": force_predict}, priority=file.priority
            )
    else:
        # 招商基金模型应用中，不会关联场景，直接走客户模型预测
        if ClientName.cmfchina == config.get_config("client.name") and not file.is_pdf:
            from remarkable.plugins.cmfchina.tasks import predict_answer_by_interface_task

            predict_answer_by_interface_task.delay(file.id)

    if file.task_type == TaskType.PDF2WORD.value:
        convert_to_docx_task.delay(file.id)
    elif file.task_type == TaskType.CLEAN_FILE.value:
        remove_docx_blank_comments_task.delay(file.id)
    elif file.task_type == TaskType.SCANNED_PDF_RESTORE.value:
        scanned_pdf_restore.delay(file.id)
    elif file.task_type == TaskType.JUDGE.value:
        await judge_file(file.id)


async def process_file_for_excel(file: NewFile, force_predict=False):
    logger.info(f"start process_file_for_excel for file: {file.id}")
    if file.is_excel:
        await file.update_(pdf_parse_status=PDFParseStatus.COMPLETE)
        process_file_predict.delay(file.id, force_predict=force_predict)
    else:
        await process_file(file, force_predict=force_predict)
    logger.info(f"end process_file_for_excel for file: {file.id}")


@app.task  # Deprecation: 不在下发新任务, 但需要等待队列中任务都执行后
def predict_answer_task(file_id: int, molds: list[int], priority: int, force_predict: bool, create_cache: bool):
    """确保先缓存完再执行预测, 保证解析状态和预测状态一致性"""
    if create_cache:
        cache_pdf_file(file_id, force=True)

    if (get_config("web.preset_answer")) and molds:
        from remarkable.worker.tasks.predict_tasks import preset_answer_by_fid_task

        logger.info(f"web.preset_answer is True, start preset_answer for {file_id}")
        preset_answer_by_fid_task.apply_async(
            args=[file_id], kwargs={"force_predict": force_predict}, priority=priority
        )


def convert_or_parse_file(file, ocr=False, garbled=False, force_ocr_pages=None, force_as_pdf=False):
    pdf_convert_provider = get_config("web.pdf_convert_provider", "pdfinsight")
    if (
        (pdf_convert_provider == "local" and file.is_word)
        or file.is_image
        or file.is_excel
        or file.is_txt
        or file.is_ppt
    ):
        # pdf_convert_provider==local的情况 目前仅有中信建投一个项目在使用
        process_flow = celery.chain(convert_to_pdf.s(file.id, ocr, garbled), start_parse_pdf.s())
        process_flow()
    else:
        file_data = {
            "id": file.id,
            "name": file.name,
            "hash": file.hash,
            "path": file.path(),
            "ocr": ocr,
            "garbled": garbled,
            "priority": file.priority,
        }
        if force_ocr_pages is not None:
            file_data.update({"force_ocr_pages": force_ocr_pages})
        if force_as_pdf:
            file_data.update({"as_pdf": 1})
        start_parse_pdf.apply_async(args=[file_data], priority=file.priority)


@app.task
@sync
@peewee_transaction_wrapper
async def process_file_extract(fid: int, upload_id: str, mold_id: int, is_success: bool):
    logger.info(f"start_process_file_extract for file: {fid}, mold: {mold_id}, success: {is_success}")
    question = await pw_db.first(
        NewQuestion.select(for_update=True).where(NewQuestion.fid == fid, NewQuestion.mold == mold_id)
    )

    if not question:
        logger.error(f"question not found: fid={fid}, mid={mold_id}")
        return

    if not is_success:
        await question.update_record(llm_status=LLMStatus.FAILED)
        return

    studio_app_id = await pw_db.scalar(NewMold.select(NewMold.studio_app_id).where(NewMold.id == mold_id))
    if studio_app_id is None:
        return

    try:
        result = await get_extract_result(studio_app_id, upload_id)
        await run_extract_answer(fid, upload_id, mold_id, result, question)
    except Exception as e:
        logger.exception("process file extract %s", e)
        await question.update_record(llm_status=LLMStatus.FAILED)


# @app.task
# @loop_wrapper
# @func_transaction
# async def fix_answer_schema(mold=None):
#     from remarkable.devtools.task_op import _fix_answer_schema
#
#     try:
#         await _fix_answer_schema(0, 0, mold)
#     except Exception as exp:
#         logger.exception(exp)
#     logger.info('update answer schema success!!!')


@app.task
def start_parse_pdf(
    file_data: dict[
        Literal["id", "name", "hash", "path", "ocr", "garbled", "force_ocr_pages", "as_pdf", "priority"],
        int | str | bool | None,
    ],
):
    if get_config("web.parse_pdf", True):
        logger.info(f"start preprocess, file: {file_data['id']}")
    else:
        logger.warning(f"web.parse_pdf is False, skip parse_pdf, file: {file_data['id']}")
        return

    app_id = get_config("app.auth.pdfinsight.app_id")
    secret = get_config("app.auth.pdfinsight.secret_key")
    url = get_config("app.auth.pdfinsight.url")
    prediction = get_config("app.auth.pdfinsight.prediction", True)
    title_ai = int(get_config("app.auth.pdfinsight.title_ai", True))
    column = int((get_config("app.auth.pdfinsight.column") or 0))
    outline_version = get_config("app.auth.pdfinsight.outline_version")
    max_ocr_page_idx = get_config("app.auth.pdfinsight.max_ocr_page_idx")
    max_pages = get_config("app.auth.pdfinsight.max_pages")
    docx_as_pdf = get_config("app.auth.pdfinsight.docx_as_pdf")
    doc_as_docx = get_config("app.auth.pdfinsight.doc_as_docx")
    need_origin_docx = get_config("app.auth.pdfinsight.need_origin_docx")
    keep_comment = get_config("app.auth.pdfinsight.keep_comment") or False
    fake_prediction = not prediction
    newline_mode = get_config("app.auth.pdfinsight.newline_mode") or 0
    api = f"{url}/api/v1/preprocess?fid={file_data['id']}"  # fid is for debug
    pdfinsight_api = authtoken.encode_url(api, app_id, secret)
    callback_url = (
        f"{get_config('web.scheme', 'http')}://{get_config('web.domain')}/api/v1/files/"
        f"{file_data['id']}/hash/{file_data['hash']}/preprocess_complete"
    )
    post_data = {
        "app": get_config("app.app_id"),
        "callback": callback_url,
        "key": f"{uuid.uuid4().hex}#{file_data['id']}",
        "priority": file_data.get("priority", 0),
        "app_id": get_config("app.app_id"),
        # 不需要pdfinsight进行模型预测时,fake_prediction = 1,此时文档里的字符都在paragraphs里
        "fake_prediction": int(fake_prediction),
        "title_ai": title_ai,
        "column": column,
        "force_ocr": get_config("app.auth.pdfinsight.force_ocr") or int(file_data["ocr"]),
        "garbled_file_handle": 2 if file_data["garbled"] else 0,
        "newline_mode": newline_mode,
        "report_colorful_exception": 1,  # 传1的话在涂色流程解析异常时会回传错误信息， scriber固定传1， 不需要修改
    }
    if outline_version:
        post_data.update({"outline_version": outline_version})
    if file_data.get("force_ocr_pages"):
        post_data.update({"force_ocr_pages": file_data["force_ocr_pages"]})
    if max_ocr_page_idx:
        post_data.update({"max_ocr_page_idx": max_ocr_page_idx})
    if max_pages:
        post_data.update({"max_pages": max_pages})
    if docx_as_pdf or file_data.get("as_pdf", 0) == 1:
        post_data.update({"as_pdf": 1})
    if doc_as_docx:
        post_data.update({"as_docx": 1})
    if need_origin_docx and any(file_data["name"].lower().endswith(e) for e in (".docx", ".doc")):
        post_data.update({"need_origin_docx": 1})
    if keep_comment:
        post_data.update({"keep_comment": 1})
    if not file_data.get("path"):
        release_parse_file_lock(file_data["hash"])
        raise CustomError(f"not found file fid: {file_data['id']}")

    if get_config("client.name") == "nafmii":
        # 启用文件解析通知， 启用后pdfinsight开始解析时会发送通知给scriber
        post_data.update({"report_status": 1})

    logger.info(post_data)

    file_obj = localstorage.read_file(file_data.get("path"), decrypt=bool(get_config("app.file_encrypt_key")))
    files = {"file": (file_data["name"], file_obj)}
    try:
        ret = requests.post(pdfinsight_api, data=post_data, files=files, timeout=10)
    except Exception as exp:
        raise PushError("pre analysis service request error: {}".format(exp)) from exp
    if ret.status_code != 200:
        release_parse_file_lock(file_data["hash"])
        raise CustomError("preprocess response error: {} \n {}".format(ret.status_code, ret.text))
    if ret.json().get("status", "") == "error":
        raise PdfinsightError(f"pdfinsight parsing failed: \n{ret.text}")


@app.task
@loop_wrapper
async def question_post_pipe_task(qid, fid, file_meta_info, skip_hook: bool = False):
    try:
        await NewQuestionService.post_pipe(qid, fid, file_meta_info, triggered_by_predict=False, skip_hook=skip_hook)
        await NewFileService.post_pipe(fid, triggered_by_predict=False)
    finally:
        init_rdb().delete(f"lock:{QUESTION_POST_PIPE_KEY.format(qid=qid)}")


@app.task
@loop_wrapper
async def gen_cache_for_diff_task(qid):
    await generate_cache_for_diff(qid)


if __name__ == "__main__":
    # remove_docx_blank_comments_task(2479)
    from remarkable.worker.tasks.predict_tasks import preset_answer_by_fid_task

    preset_answer_by_fid_task(1931, True)
