"""
导出相关任务
"""

import json
import logging
import os
import zipfile
from datetime import datetime

from remarkable.common.enums import ClientName, ExportStatus
from remarkable.common.storage import localstorage
from remarkable.common.util import loop_wrapper
from remarkable.config import get_config, project_root
from remarkable.db import peewee_transaction_wrapper, pw_db
from remarkable.models.new_file import NewFile
from remarkable.optools.export_answers_for_szse import export_answer_scheduler
from remarkable.pw_models.model import NewMold, NewTrainingData
from remarkable.service.comment import shorten_path_bytes
from remarkable.service.export import CmfChinaExporter, InspectDataExporter
from remarkable.worker.app import app

logger = logging.getLogger(__name__)

__all__ = ["export_train_data", "gen_field_map", "export_inspect_data", "export_original_files", "export_answer_data"]


@app.task
@loop_wrapper
@peewee_transaction_wrapper
async def export_train_data(task_id: int, export_type: str):
    if export_type == "excel" and get_config("client.name") == ClientName.cmfchina:
        # 目前只支持cmfchina
        await export_answer_data_excel(task_id)
    elif get_config("client.export_answer_csv_all_in_one"):
        await export_train_data_gf_fund(task_id)
    else:
        await export_answer_scheduler(task_id)


@app.task
@loop_wrapper
@peewee_transaction_wrapper
async def export_answer_data(p_id: int, file_ids, task_id: int):
    from remarkable.service.answer import export_answer_data_scheduler

    await export_answer_data_scheduler(p_id, file_ids, task_id)


@app.task
@loop_wrapper
@peewee_transaction_wrapper
async def export_inspect_data(task_id: int):
    training_data = await NewTrainingData.find_by_id(task_id)
    exporter = InspectDataExporter(
        task_id,
        mold_id=training_data.mold,
        tree_l=training_data.dirs,
        training_data=training_data,
        files_ids=training_data.files_ids,
        export_action=training_data.task_action,
    )
    try:
        excel_path = await exporter.export()
    except Exception as e:
        logger.exception(e)
        await training_data.update_(status=ExportStatus.FAILED)
        return

    if excel_path:
        await training_data.update_(zip_path=excel_path, status=ExportStatus.FINISH)
    else:
        logger.warning("excel path is empty")
        await training_data.update_(status=ExportStatus.FAILED)


async def export_train_data_gf_fund(task_id: int):
    from remarkable.service.export import GfFundExporter

    training_data = await NewTrainingData.find_by_id(task_id)
    exporter = GfFundExporter(
        task_id,
        mold_id=training_data.mold,
        tree_l=training_data.dirs,
        training_data=training_data,
        files_ids=training_data.files_ids,
        export_action=training_data.task_action,
    )
    try:
        excel_path = await exporter.export()
    except Exception as e:
        logger.exception(e)
        await training_data.update_(status=ExportStatus.FAILED)
        return

    if excel_path:
        await training_data.update_(zip_path=excel_path, status=ExportStatus.FINISH)
    else:
        logger.warning("excel path is empty")
        await training_data.update_(status=ExportStatus.FAILED)


async def export_answer_data_excel(task_id: int):
    training_data = await NewTrainingData.find_by_id(task_id)
    exporter = CmfChinaExporter(
        task_id,
        mold_id=training_data.mold,
        tree_l=training_data.dirs,
        training_data=training_data,
        files_ids=training_data.files_ids,
        export_action=training_data.task_action,
    )
    try:
        excel_path = await exporter.export()
    except Exception as e:
        logger.exception(e)
        await training_data.update_(status=ExportStatus.FAILED)
        return

    if excel_path:
        await training_data.update_(zip_path=excel_path, status=ExportStatus.FINISH)
    else:
        logger.warning("excel path is empty")
        await training_data.update_(status=ExportStatus.FAILED)


@app.task
@loop_wrapper
async def export_original_files(task_id: int):
    training_data = await NewTrainingData.find_by_id(task_id)
    if not training_data.files_ids:
        logging.warning(f"task_id <{training_data.task_id}> files_ids is empty")
    mold_obj = await NewMold.find_by_id(training_data.mold)
    if not mold_obj:
        logging.error("mold error, task_id：%s", task_id)
        await training_data.update_(status=ExportStatus.FAILED)
        return
    zip_path = os.path.join(
        project_root, "data", "export_answer_data", f"{mold_obj.name} {datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
    )
    files = list(await pw_db.execute(NewFile.select().where(NewFile.id.in_(training_data.files_ids))))
    with zipfile.ZipFile(zip_path, "w") as zfp:
        for file in files:
            if localstorage.exists(file.path()):
                name = shorten_path_bytes(f"{file.id}-{file.name}")
                zfp.write(localstorage.mount(file.path()), name, compress_type=zipfile.ZIP_DEFLATED)
    await training_data.update_(zip_path=zip_path, status=ExportStatus.FINISH)


@app.task
@loop_wrapper
async def gen_field_map(mold):
    await gen_field_map_file(mold)


async def gen_field_map_file(mold):
    def _gen_field_map(mold_schema):
        ret = []
        for item in mold_schema.root_schema.children:
            traverse_children(item, ret)
        return ret

    def traverse_children(schema_item, ret):
        if schema_item.children:
            for item in schema_item.children:
                traverse_children(item, ret)
        else:
            ret.append(schema_item.path_key)

    def gen_field_map_key(length):
        ret = []
        chars = [chr(i) for i in range(97, 123)]
        for i in chars:
            for j in chars:
                ret.append(f"/{i}{j}")
                if len(ret) == length:
                    return ret
        return ret

    from remarkable.config import project_root
    from remarkable.predictor.mold_schema import MoldSchema

    mold_obj = await NewMold.find_by_id(mold)
    mold_name = mold_obj.name
    field_map_file_dir = os.path.join(project_root, "data", "szse_field_map")
    if not localstorage.exists(field_map_file_dir):
        os.mkdir(field_map_file_dir)
    field_map_file_path = os.path.join(field_map_file_dir, f"{mold_name}_field_map.txt")
    mold_schema = MoldSchema(mold_obj.data)
    tile_schema_item = _gen_field_map(mold_schema)
    field_key = gen_field_map_key(len(tile_schema_item))
    with open(field_map_file_path, "w") as obj:
        for key, item in zip(field_key, tile_schema_item):
            value = "-".join(json.loads(item)[1:])
            obj.write(f"{key} {value}\n")
        obj.write("/o 无标签")

    logging.info(f"字段映射文件生成, {mold_name}_field_map.txt")
