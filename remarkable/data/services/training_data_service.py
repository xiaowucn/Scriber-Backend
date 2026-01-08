import os

from remarkable.common.constants import HistoryAction
from remarkable.common.enums import ClientName, ExportStatus
from remarkable.common.exceptions import CustomError
from remarkable.common.storage import localstorage
from remarkable.config import get_config
from remarkable.models.query_helper import AsyncPagination
from remarkable.optools.export_answers_for_szse import fetch_all_answers
from remarkable.pw_models.model import NewMold, NewTrainingData
from remarkable.worker.tasks import export_inspect_data, export_original_files, export_train_data


async def get_training_tasks(
    mid, export_type: str = "json", export_action=HistoryAction.CREATE_TRAINING_DATA, status=None, page=1, size=20
):
    if get_config("client.name") == ClientName.cmfchina:
        cond = [NewTrainingData.mold == mid]
    else:
        cond = [
            NewTrainingData.mold == mid,
            NewTrainingData.export_type == export_type,
            NewTrainingData.task_action == export_action,
        ]
    if status:
        cond.append(NewTrainingData.status == status)
    query = NewTrainingData.select().where(*cond).order_by(NewTrainingData.id.desc())
    data = await AsyncPagination(query.dicts(), page=page, size=size).data()
    return data


async def mold_export_task(
    schema_id, export_type, tree_l, files_ids=None, export_action=HistoryAction.CREATE_TRAINING_DATA
) -> NewTrainingData:
    mold = await NewMold.find_by_id(schema_id)
    if not mold:
        raise CustomError(f"schema_id: [ {schema_id} ] does not existed", resp_status_code=400)

    if get_config("data_flow.file_answer.generate"):
        molds = await NewMold.get_related_molds(schema_id)
        if len(molds) > 1:
            master_mold = molds[0]
            if master_mold.id != schema_id:
                raise CustomError(f"请在主schema: {master_mold.name} 上导出")

    # 新增`training_data`记录
    tree_s = set(tree_l)
    if export_action in (HistoryAction.CREATE_TABLE_OF_CONTENT, HistoryAction.ORIGINAL_FILE):
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1683#note_296396
        task_total = files_ids
    else:
        task_total = await fetch_all_answers(mold.id, export_type=export_type, tree_s=tree_s, files_ids=files_ids)
    if not task_total:
        raise CustomError("暂没有可导出的文件", resp_status_code=400)
    params = {
        "mold": schema_id,
        "task_done": 0,
        "task_total": len(task_total),
        "export_type": export_type,
        "dirs": list(tree_s),
        "files_ids": files_ids,
        "task_action": export_action,
        "status": ExportStatus.DOING,
    }
    training_data = await NewTrainingData.create(**params)
    # 异步执行导出
    if export_action == HistoryAction.CREATE_INSPECT_RESULT:
        export_inspect_data.delay(training_data.id)
    if export_action == HistoryAction.ORIGINAL_FILE:
        export_original_files.delay(training_data.id)
    else:
        export_train_data.delay(training_data.id, training_data.export_type)
    return training_data


async def download_training_zip(task_id):
    train_data = await NewTrainingData.find_by_id(task_id)
    if not train_data:
        raise CustomError(f"task_id does not existed: {task_id}")

    if not train_data.zip_path:
        raise CustomError(_("zip file is not ready"))
    data = localstorage.read_file(train_data.zip_path)
    return data, os.path.split(train_data.zip_path)[1]


async def delete_training_task(task_id):
    training_data = await NewTrainingData.find_by_id(task_id)
    if not training_data:
        raise CustomError("Task Not Found", resp_status_code=404)
    await training_data.soft_delete()
