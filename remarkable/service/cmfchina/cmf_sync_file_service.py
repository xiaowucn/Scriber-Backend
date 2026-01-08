import hashlib
import logging
import os
from pathlib import Path

from speedy.peewee_plus.orm import and_
from tornado.httputil import HTTPFile

from remarkable.common.cmfchina import CmfChinaSysFromType
from remarkable.common.constants import FeatureSchema
from remarkable.common.enums import TaskType
from remarkable.common.zip import decompression_files
from remarkable.db import pw_db
from remarkable.models.cmf_china import CmfChinaEmail, CmfChinaEmailFileInfo, CmfSharedDisk
from remarkable.models.new_file import NewFile
from remarkable.pw_models.model import NewFileProject, NewFileTree, NewMold
from remarkable.service.cmfchina.cmf_group import CMFGroupService
from remarkable.service.cmfchina.email_model import CmfEmail
from remarkable.service.cmfchina.service import CmfChinaService
from remarkable.service.cmfchina.validator import CmfSharedDiskFileValidator
from remarkable.service.new_file import NewFileService
from remarkable.worker.tasks import process_file_for_excel

logger = logging.getLogger(__name__)


class CmfSyncFileService:
    @staticmethod
    async def upload_file_from_email(email: CmfEmail, uid: int):
        if await pw_db.exists(
            CmfChinaEmailFileInfo.select().where(
                CmfChinaEmailFileInfo.host == email.host,
                CmfChinaEmailFileInfo.account == email.account,
                CmfChinaEmailFileInfo.email_id == email.email_id,
            )
        ):
            logger.warning(f"Email<{email.host, email.account, email.email_id}> processed")
            return
        tid = None
        if cmf_china_email := await pw_db.first(
            CmfChinaEmail.select().where(
                CmfChinaEmail.host == email.host,
                CmfChinaEmail.account == email.account,
                CmfChinaEmail.pid.is_null(False),
                CmfChinaEmail.mold_id.is_null(False),
            ),
        ):
            project = await NewFileProject.get_by_id(cmf_china_email.pid)
            mold = await NewMold.get_by_id(cmf_china_email.mold_id)
            if project and mold:
                # 设置了项目和场景
                tid = project.rtree_id
                if email.attachments:
                    # 有附件，则上传至邮件主题的文件夹下
                    if not (
                        tree := await NewFileTree.find_by_kwargs(
                            ptree_id=project.rtree_id, pid=project.id, name=email.subject
                        )
                    ):
                        # 没有同名文件夹，创建文件夹
                        tree = await NewFileTree.create(
                            **{
                                "ptree_id": project.rtree_id,
                                "pid": project.id,
                                "name": email.subject,
                                "default_molds": [mold.id],
                                "uid": uid,
                            }
                        )
                    await CMFGroupService.add_group_to_tree_from_rtree(tree.id, project.rtree_id)
                    tid = tree.id
        new_files = []
        async with pw_db.atomic():
            for attachment in [email.content_attachment, *email.attachments]:
                if not attachment.data:
                    continue
                logger.info(
                    f"sync email<{email.host, email.account, email.email_id}> attachment<{attachment.filename}>"
                )
                if tid:
                    # 有设置项目或场景，在tid 下创建文件
                    new_file = await NewFileService.create_file(
                        name=attachment.filename,
                        body=attachment.data,
                        pid=project.id,
                        tree_id=tid,
                        uid=uid,
                        task_type=TaskType.AUDIT.value,
                        molds=[mold.id],
                        priority=2,
                        sysfrom=CmfChinaSysFromType.EMAIL.value,
                    )
                else:
                    # 没有设置项目或场景，走分类
                    new_file, _ = await CmfChinaService.upload_filed_file(
                        HTTPFile(filename=attachment.filename, body=attachment.data),
                        uid,
                        sysfrom=CmfChinaSysFromType.EMAIL.value,
                    )
                await pw_db.create(
                    CmfChinaEmailFileInfo,
                    host=email.host,
                    account=email.account,
                    email_id=email.email_id,
                    sent_at=email.sent_at.timestamp() if email.sent_at else None,
                    from_=email.from_.addresses,
                    to=email.to.addresses,
                    cc=email.cc.addresses,
                    subject=email.subject,
                    fid=new_file.id,
                    is_content=attachment == email.content_attachment,
                )
                new_files.append(new_file)
        for new_file in new_files:
            await process_file_for_excel(new_file)

    @staticmethod
    async def parse_file_from_shared_disk(file_path: Path, file_name: str, body: bytes, uid: int):
        if not body or not file_name:
            return
        try:
            CmfSharedDiskFileValidator.check(HTTPFile(filename=file_name, body=body))
        except Exception:
            logger.warning(f"sync shared disk file<{file_path} -> {file_name}>: suffix or size error")
            return
        hash = hashlib.md5(body).hexdigest()
        if fid := await pw_db.scalar(
            NewFile.select(NewFile.id)
            .where(NewFile.hash == hash)
            .join(NewFileProject, on=and_(NewFileProject.id == NewFile.pid, NewFileProject.visible))
        ):
            logger.warning(f"file<{file_path} -> {file_name}> already exists: file:{fid}")
        else:
            async with pw_db.atomic():
                new_file, cmf_file_info = await CmfChinaService.upload_filed_file(
                    HTTPFile(filename=file_name, body=body), uid, sysfrom=CmfChinaSysFromType.DISK.value
                )
                await pw_db.create(
                    CmfSharedDisk,
                    file_id=new_file.id,
                    path=str(file_path),
                )
            await process_file_for_excel(new_file)
            logger.info(f"end syncing file <{file_name}>:<{new_file.id}>")

    @staticmethod
    async def upload_file_from_shared_disk(file_path: Path, uid: int):
        suffix = os.path.splitext(file_path.name)[1].lower()
        if suffix in FeatureSchema.from_config().supported_zip_suffixes:
            for file in decompression_files(
                file_path=file_path,
                action="cmf_shared_disk",
                support_filetype_suffixes=FeatureSchema.from_config().supported_suffixes,
            ):
                await CmfSyncFileService.parse_file_from_shared_disk(
                    file.archive_file.as_posix(), file.name, file.export_file.read_bytes(), uid
                )

        else:
            with open(file_path, "rb") as obj:
                body = obj.read()
                await CmfSyncFileService.parse_file_from_shared_disk(file_path, file_path.name, body, uid)
