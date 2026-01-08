import asyncio
import logging
import os
import re
import sys
from pathlib import Path

from peewee import fn

from remarkable.config import project_root
from remarkable.db import IS_GAUSSDB, pw_db
from remarkable.models.model_version import NewModelVersion
from remarkable.models.new_file import NewFile
from remarkable.pw_models.model import NewFileProject, NewFileTree, NewMold
from remarkable.pw_models.question import NewQuestion

logger = logging.getLogger(__name__)


def array_replace(arr, old, new):
    if IS_GAUSSDB:
        arr = fn.ARRAY_TO_STRING(arr, ",")
        arr = fn.REGEXP_REPLACE(arr, rf"^{old},", rf"{new},")
        arr = fn.REGEXP_REPLACE(arr, rf",{old}$", rf",{new}")
        return fn.STRING_TO_ARRAY(arr, ",")
    return fn.ARRAY_REPLACE(arr, old, new)


def _model_data_dir(model_id: int) -> Path:
    return Path(f"{project_root}/data/training_cache/{model_id}")


async def _update_id_seq(table: str):
    for (real_name,) in await pw_db.execute("SELECT c.relname FROM pg_class c WHERE c.relkind = 'S'"):
        if re.search(r"^{}_id.*".format(table), real_name):
            await pw_db.execute(f"SELECT setval('{real_name}', (SELECT MAX(id) FROM {table})+1)")
            logger.info(f"`{real_name}` seq id updated")


async def main(path: str):
    for from_id, to_id in read_id_pairs(path):
        try:
            await _update_db(from_id, to_id)
        except Exception as e:
            logger.error(f"Schema id变更失败: {from_id} => {to_id}, {e}")
            continue
        logger.info("数据库变更成功，开始迁移模型数据...")
        try:
            _move_model_data(from_id, to_id)
        except Exception as e:
            logger.error(f"模型数据迁移失败: {from_id} => {to_id}, {e}")
        else:
            logger.info(f"模型数据迁移成功: {from_id} => {to_id}")


def _move_model_data(from_id, to_id):
    from_dir = _model_data_dir(from_id)
    to_dir = _model_data_dir(to_id)
    assert from_dir.exists(), f"模型数据目录不存在: {from_dir}"
    assert not to_dir.exists(), f"模型数据目录已存在: {to_dir}，跳过"
    to_dir.parent.mkdir(parents=True, exist_ok=True)
    from_dir.rename(to_dir)


async def _update_db(from_id, to_id):
    logger.info(f"开始变更Schema id: {from_id} => {to_id}")
    async with pw_db.atomic():
        # mold = await pw_db.first(NewMold.select(include_deleted=True).where(NewMold.id == to_id))
        # assert mold is None, f"目标 mold {to_id} 已存在，无法替换"
        await pw_db.execute(NewMold.update(id=to_id).where(NewMold.id == from_id))
        await pw_db.execute(NewMold.update(master=to_id).where(NewMold.master == from_id))
        logger.info("更新`mold`表成功")
        await pw_db.execute(
            NewFile.update(molds=array_replace(NewFile.molds, from_id, to_id)).where(NewFile.molds.contains(from_id))
        )
        logger.info("更新`file`表成功")
        await pw_db.execute(
            NewFileProject.update(default_molds=array_replace(NewFileProject.default_molds, from_id, to_id)).where(
                NewFileProject.default_molds.contains(from_id)
            )
        )
        logger.info("更新`file_project`表成功")
        await pw_db.execute(
            NewFileTree.update(default_molds=array_replace(NewFileTree.default_molds, from_id, to_id)).where(
                NewFileTree.default_molds.contains(from_id)
            )
        )
        logger.info("更新`file_tree`表成功")
        await pw_db.execute(NewModelVersion.update(mold=to_id).where(NewModelVersion.mold == from_id))
        logger.info("更新`model_version`表成功")
        await pw_db.execute(NewQuestion.update(mold=to_id).where(NewQuestion.mold == from_id))
        logger.info("更新`question`表成功")

        for table in ("cgs_audit_status", "cgs_result", "cgs_rule"):
            await pw_db.execute(f"UPDATE {table} SET schema_id = {to_id} WHERE schema_id = {from_id}")

        for table in ("training_data", "rule_item", "rule_class", "extract_method", "accuracy_record"):
            await pw_db.execute(f"UPDATE {table} SET mold = {to_id} WHERE mold = {from_id}")

    for table in (
        "file",
        "file_project",
        "file_tree",
        "model_version",
        "question",
        "cgs_audit_status",
        "cgs_result",
        "cgs_rule",
        "training_data",
        "rule_item",
        "rule_class",
        "extract_method",
        "accuracy_record",
    ):
        await _update_id_seq(table)


def read_id_pairs(path=None) -> list[tuple[int, int]]:
    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/3427
    from_to_map = {
        191: 194,
        189: 192,
        188: 191,
    }
    if path and os.path.exists(path):
        with open(path) as fp:
            for line in fp:
                pairs = [int(i) for i in line.strip().split() if i and i.isdigit()]
                if len(pairs) != 2:
                    continue
                from_to_map[pairs[0]] = pairs[1]
    return sorted(from_to_map.items(), key=lambda x: x[-1], reverse=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: PYTHONPATH=. {sys.argv[0]} <id_map_path>")
    asyncio.run(main(sys.argv[1]))
