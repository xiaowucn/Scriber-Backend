"""
处理api调用之后的一些后续操作
"""

from remarkable.common.constants import DcmStatus, HistoryAction
from remarkable.config import get_config
from remarkable.db import pw_db


async def dcm_post_pipe_after_api(fid, qid, action, **kwargs):
    from remarkable.models.ecitic_dcm import DcmFileInfo

    if action == HistoryAction.OPEN_PDF.value:
        await pw_db.execute(DcmFileInfo.update(browse_status=DcmStatus.DONE).where(DcmFileInfo.file_id == fid))
    elif action in (HistoryAction.SUBMIT_ANSWER.value, HistoryAction.DCM_ORDER_REF_MODIFY.value):
        await pw_db.execute(DcmFileInfo.update(edit_status=DcmStatus.DONE).where(DcmFileInfo.file_id == fid))


async def post_pipe_after_api(fid, qid, action, **kwargs):
    client = get_config("client.name")
    if client == "ecitic_dcm":
        await dcm_post_pipe_after_api(fid, qid, action, **kwargs)
