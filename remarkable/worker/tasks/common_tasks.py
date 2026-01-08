import logging
import shutil
from pathlib import Path

from utensils.archive_reader import FileInfo, FileInfoNode, FileInfoTree, detect_archive
from utensils.syncer import sync

from remarkable import config
from remarkable.common.constants import ADMIN_ID, CmfFiledStatus, UNZipStage
from remarkable.common.enums import ClientName, TaskType
from remarkable.common.exceptions import CustomError
from remarkable.common.util import loop_wrapper
from remarkable.config import get_config
from remarkable.db import init_rdb, pw_db
from remarkable.models.cmf_china import CmfFiledFileInfo
from remarkable.models.new_file import NewFile
from remarkable.models.new_group import CMFUserGroupRef
from remarkable.pw_models.model import NewFileTree, NewHistory, NewTimeRecord
from remarkable.service.cmfchina.cmf_group import CMFGroupService
from remarkable.service.cmfchina.common import CMF_CHINA_FILED_FILE_PROJECT_NAME
from remarkable.service.new_file import NewFileService
from remarkable.worker.app import app

__all__ = ["save_event_log", "process_compressed_file"]

logger = logging.getLogger(__name__)


@app.task
@loop_wrapper
async def save_event_log(uid, user_name, action, qid: int | None = None, meta: dict | None = None):
    # TODO: 所有计入历史记录的操作都转为异步调用
    await NewHistory.create(**{"uid": uid, "qid": qid, "action": action, "user_name": user_name, "meta": meta})


@app.task
@sync
async def process_compressed_file(
    uid: int,
    tid: int,
    work_dir: str,
    task_id: str,
    compressed_suffix: list[str],
    support_filetype_suffixes: list[str],
    task_type: str = TaskType.EXTRACT.value,
    need_create_folder: bool = True,
    scenario_id: int | None = None,
    sysfrom: str | None = None,
    molds: list[int] | None = None,
):
    # TODO: 细化`30~100`的进度
    work_dir = Path(work_dir)
    zip_path = work_dir / f"{task_id}{compressed_suffix}"
    tmp_dir = work_dir / task_id
    tmp_dir.mkdir(exist_ok=True)
    rdb = init_rdb()

    stage = f"{UNZipStage.UNPACK}:15:"
    try:
        archive = detect_archive(
            filepath=zip_path,
            support_filetype_suffixes=support_filetype_suffixes,
        )
        files = archive.all_files_info()
        target_files = files
        stage = f"{UNZipStage.IMPORT}:30:"
        archive.export(target_files, export_dir=Path(work_dir))
        tree = FileInfoTree(target_files)
        await import_compressed_file_info(
            uid, tid, files, tree.root.children, task_type, need_create_folder, scenario_id, sysfrom, molds
        )
    except Exception:
        stage = f"{UNZipStage.ERROR}:-1:解压失败，请检查文件是否损坏。"
        logger.exception(f"Failed to process zip file: {zip_path}")
    else:
        stage = f"{UNZipStage.FINISHED}:100:"
        logger.info(f"Successfully processed zip file: {zip_path}")
    finally:
        rdb.set(task_id, stage, keepttl=True)
        shutil.rmtree(work_dir, ignore_errors=True)


# async def import_zip(uid: int, tid: int, zipdir: Path, task_type: str = TaskType.EXTRACT.value):
#     from remarkable.worker.tasks import process_file, process_file_for_excel
#
#     rtree = await NewFileTree.find_by_id(tid)
#     molds = await NewFileTree.find_default_molds(tid)
#
#     def get_all_files(_dir):
#         all_files = []
#         for _, _, files in os.walk(_dir):
#             all_files.extend(files)
#         return all_files
#
#     total_files = get_all_files(zipdir)
#
#     if not config.get_config("web.allow_same_name_file_in_project", True):
#         file = await pw_db.first(
#             NewFile.select(NewFile.name).where(
#                 NewFile.pid == rtree.pid,
#                 NewFile.name.in_(total_files),
#             )
#         )
#         if file:
#             raise CustomError(f"该项目下已存在同名的文件: {file.name}")
#     progress = 30
#
#     async def import_dir(ptree_id, _dir):
#         nonlocal progress
#         root = _dir
#         for entry in os.listdir(_dir):
#             full_path = os.path.join(root, entry)
#             if os.path.isfile(full_path):
#                 filename = entry
#                 if progress < 90:
#                     progress += 1
#                 with open(full_path, "rb") as fp:
#                     data = fp.read()
#
#                 newfile = await NewFileService.create_file(
#                     filename, data, molds, rtree.pid, ptree_id, uid, task_type=task_type
#                 )
#                 if "cmfchina" == get_config("client.name"):
#                     if rtree.name == CMF_CHINA_FILED_FILE_PROJECT_NAME:
#                         await pw_db.create(CmfFiledFileInfo, fid=newfile.id, status=CmfFiledStatus.WAIT)
#                     await process_file_for_excel(newfile)
#                 else:
#                     await process_file(newfile)
#                 await NewTimeRecord.update_record(newfile.id, "upload_stamp")
#                 logger.info(f"{filename=}, {progress=}, {len(total_files)=}")
#             else:
#                 subdir = entry
#                 new_tree = await NewFileTree.find_by_kwargs(pid=rtree.pid, name=subdir, ptree_id=ptree_id)
#                 if new_tree:
#                     raise CustomError(f'该文件夹名称"{subdir}"已被占用，请更换其他名称')
#                 new_tree = await NewFileTree.create(
#                     **{
#                         "ptree_id": ptree_id,
#                         "pid": rtree.pid,
#                         "name": subdir,
#                         "default_molds": molds,
#                         "uid": uid,
#                     }
#                 )
#                 if "cmfchina" == get_config("client.name"):
#                     group_ids = None if uid == ADMIN_ID else await CMFUserGroupRef.get_user_group_ids(uid)
#                     if groups := await CMFGroupService.get_file_tree_groups(ptree_id, group_ids):
#                         groups = await CMFGroupService.get_groups([group.id for group in groups])
#                         for group in groups:
#                             file_tree_ids = set(group["file_tree_ids"] + [new_tree.id])
#                             await CMFGroupService.update(group["id"], file_tree_ids=list(file_tree_ids))
#                 await import_dir(new_tree.id, full_path)
#
#     await import_dir(rtree.id, zipdir)


async def import_compressed_file_info(
    uid: int,
    tid: int,
    file_infos: list[FileInfo],
    file_tree: dict[str, FileInfoNode],
    task_type: str = TaskType.EXTRACT.value,
    need_create_folder: bool = True,
    scenario_id: int | None = None,
    sysfrom: str | None = None,
    molds: list[int] | None = None,
):
    from remarkable.worker.tasks import process_file, process_file_for_excel

    rtree = await NewFileTree.find_by_id(tid)
    molds = molds or await NewFileTree.find_default_molds(tid)

    if not config.get_config("web.allow_same_name_file_in_project", True):
        file = await pw_db.first(
            NewFile.select(NewFile.name).where(
                NewFile.pid == rtree.pid,
                NewFile.name.in_([file_info.name for file_info in file_infos]),
            )
        )
        if file:
            raise CustomError(f"该项目下已存在同名的文件: {file.name}")
    progress = 30

    async def import_dir_file_info(ptree_id: int, _file_tree: dict[str, FileInfoNode], create_folder: bool):
        nonlocal progress
        for file_info in _file_tree.values():
            if file_info.is_dir:
                if create_folder:
                    subdir = file_info.name
                    new_tree = await NewFileTree.find_by_kwargs(pid=rtree.pid, name=subdir, ptree_id=ptree_id)
                    if new_tree:
                        raise CustomError(f'该文件夹名称"{subdir}"已被占用，请更换其他名称')
                    new_tree = await NewFileTree.create(
                        **{
                            "ptree_id": ptree_id,
                            "pid": rtree.pid,
                            "name": subdir,
                            "default_molds": molds,
                            "uid": uid,
                        }
                    )
                    if ClientName.cmfchina == get_config("client.name"):
                        group_ids = None if uid == ADMIN_ID else await CMFUserGroupRef.get_user_group_ids(uid)
                        if groups := await CMFGroupService.get_file_tree_groups(ptree_id, group_ids):
                            groups = await CMFGroupService.get_groups([group.id for group in groups])
                            for group in groups:
                                file_tree_ids = set(group["file_tree_ids"] + [new_tree.id])
                                await CMFGroupService.update(group["id"], file_tree_ids=list(file_tree_ids))
                    tid = new_tree
                else:
                    tid = ptree_id
                await import_dir_file_info(tid, file_info.children, create_folder)
            else:
                if progress < 90:
                    progress += 1
                newfile = await NewFileService.create_file(
                    file_info.name,
                    file_info.file.export_file.read_bytes(),
                    molds,
                    rtree.pid,
                    ptree_id,
                    uid,
                    task_type=task_type,
                    scenario_id=scenario_id,
                    sysfrom=sysfrom,
                )
                if ClientName.cmfchina == get_config("client.name"):
                    if rtree.name == CMF_CHINA_FILED_FILE_PROJECT_NAME:
                        await pw_db.create(CmfFiledFileInfo, fid=newfile.id, status=CmfFiledStatus.WAIT)
                    await process_file_for_excel(newfile)
                else:
                    await process_file(newfile)
                await NewTimeRecord.update_record(newfile.id, "upload_stamp")
                logger.info(f"{file_info.name=}, {progress=}, {len(file_infos)=}")

    await import_dir_file_info(rtree.id, file_tree, need_create_folder)
