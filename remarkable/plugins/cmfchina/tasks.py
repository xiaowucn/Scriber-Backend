import datetime
import logging
from pathlib import Path

from speedy.peewee_plus.orm import and_
from utensils.syncer import sync

from remarkable.common.constants import ADMIN_ID, CmfFiledStatus, CmfInterfacePresetStatus, CommonStatus, PDFParseStatus
from remarkable.common.datetime_util import get_start_end_of_day
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.cmf_china import (
    CmfChinaEmail,
    CmfFiledFileInfo,
    CmfModel,
    CmfModelAuditAccuracy,
    CmfModelFileRef,
    CmfMoldModelRef,
)
from remarkable.models.new_file import NewFile
from remarkable.predictor.cmfchina_predictor.models.Interface_model import predict_answer_by_interface
from remarkable.pw_models.model import MoldWithFK, NewFileProject
from remarkable.service.cmfchina.cmf_sync_file_service import CmfSyncFileService
from remarkable.service.cmfchina.common import CMF_CHINA_VERIFY_FILED_PROJECT_NAME
from remarkable.service.cmfchina.imap_email_receiver import IMAPEmailReceiver
from remarkable.service.comment import is_hidden_file
from remarkable.worker.app import app

logger = logging.getLogger(__name__)


@app.task
@sync
async def reset_filed_file_task(fid):
    from remarkable.service.cmfchina.filed_file_service import CmfFiledFileService

    file = await NewFile.get_by_id(fid)
    if not file:
        logger.error(f"file<{fid}> not existed before reset filed file")
        return
    logger.info(f"reset filed file<{fid}>")
    await pw_db.execute(CmfFiledFileInfo.update(status=CmfFiledStatus.WAIT).where(CmfFiledFileInfo.fid == fid))
    await CmfFiledFileService.filed_file(file)
    if get_config("web.preset_answer"):
        from remarkable.worker.tasks.predict_tasks import preset_answer_by_fid_task

        logger.info(f"web.preset_answer is True, start preset_answer for {file.id}")
        preset_answer_by_fid_task.apply_async(args=[file.id], priority=file.priority)


@app.task
@sync
async def predict_answer_by_interface_task(fid):
    file = await NewFile.get_by_id(fid)
    if not file:
        logger.error(f"file<{fid}> not existed before predict answer by interface model")
        return
    if not file.is_pdf and file.pdf_parse_status != PDFParseStatus.COMPLETE:
        logger.info(f"file<{fid}> parsing not complete")
        return
    model_file_ref = await pw_db.prefetch_one(
        CmfModelFileRef.select().where(CmfModelFileRef.fid == file.id), CmfModel.select()
    )
    if not model_file_ref or not model_file_ref.model:
        logger.error(f"file<{fid}> not associated with model")
        return
    file_path_dict = {file.name: file.pdf_path()}
    model_file_ref.answer = None
    model_file_ref.status = CmfInterfacePresetStatus.DOING
    await pw_db.update(model_file_ref, only=["answer", "status"])
    try:
        data = predict_answer_by_interface(
            model_file_ref.model.address,
            file_path_dict,
            model_file_ref.model.name,
        )
    except Exception as e:
        model_file_ref.status = CmfInterfacePresetStatus.FAIL
        await pw_db.update(model_file_ref, only=["status"])
        logger.error(f"predict answer error: {e}")
        return
    model_file_ref.answer = data
    model_file_ref.status = CmfInterfacePresetStatus.DONE
    await pw_db.update(model_file_ref, only=["answer", "status"])


@app.task
@sync
async def delete_verify_filed_file():
    logger.info("start delete verify filed file")
    query = NewFile.select().join(
        NewFileProject,
        on=and_(
            NewFileProject.id == NewFile.pid,
            NewFileProject.name == CMF_CHINA_VERIFY_FILED_PROJECT_NAME,
            ~NewFileProject.visible,
        ),
    )
    files = await pw_db.execute(query)
    for file in files:
        await file.soft_delete()
    logger.info("end delete verify filed file")


@app.task
@sync
async def sync_file_from_email():
    cmf_emails = await pw_db.execute(CmfChinaEmail.select())
    for cmf_email in cmf_emails:
        logger.info(f"start sync email: host={cmf_email.host}, account={cmf_email.account}")
        with IMAPEmailReceiver(cmf_email.host, cmf_email.account, cmf_email.password) as receiver:
            async for email in receiver.email_iter():
                await CmfSyncFileService.upload_file_from_email(email, ADMIN_ID)

        logger.info(f"end sync email: host={cmf_email.host}, account={cmf_email.account}")


@app.task
@sync
async def save_audit_result_statistic():
    from remarkable.service.cmfchina.service import CmfChinaService

    now = datetime.datetime.now()
    today_start_at, _ = get_start_end_of_day(now)

    query = (
        NewFile.select(NewFile.id, NewFile.created_utc, NewFile.molds)
        .join(NewFileProject, on=and_(NewFileProject.id == NewFile.pid, NewFileProject.visible))
        .where(NewFile.created_utc < today_start_at.timestamp())
        .order_by(NewFile.created_utc)
    )
    files = await pw_db.execute(query.namedtuples())
    query = CmfMoldModelRef.select().where(CmfMoldModelRef.enable == CommonStatus.VALID.value)
    refs = await pw_db.prefetch(query, CmfModel.select(), MoldWithFK.select())
    mold_models = {ref.mold_id: ref.model for ref in refs}
    molds = {ref.mold_id: ref.mold for ref in refs}
    async for model_id, day_start_at, molds_rate in CmfChinaService.aggregate_audit_accuracy(files, mold_models, molds):
        logger.info(f"save audit result statistic: model_id={model_id}, day_start_at={day_start_at}")
        start_at = day_start_at.timestamp()
        query = CmfModelAuditAccuracy.select().where(
            CmfModelAuditAccuracy.model_id == model_id, CmfModelAuditAccuracy.date == start_at
        )
        model_accuracy = await pw_db.first(query)
        if model_accuracy is None:
            await CmfModelAuditAccuracy.create(model_id=model_id, date=start_at, molds_rate=molds_rate)
        else:
            model_accuracy.molds_rate = molds_rate
            await pw_db.update(model_accuracy, only=["molds_rate"])


@app.task
@sync
async def sync_shared_disk():
    paths = get_config("cmfchina.shared_disk_paths", [])
    for path in paths:
        logger.info(f"start syncing shared disk: {path}")
        folder_path = Path(path)
        for f in folder_path.rglob("*"):
            if f.is_file() and not is_hidden_file(f):
                logger.info(f"start syncing file <{f.name}>")
                await CmfSyncFileService.upload_file_from_shared_disk(f, ADMIN_ID)

        logger.info(f"end syncing shared disk: {path}")


if __name__ == "__main__":
    sync_shared_disk()
