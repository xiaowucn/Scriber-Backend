import logging

from remarkable.common.util import loop_wrapper
from remarkable.plugins.answer_poster.tasks import ScheduleTaskMonitor
from remarkable.plugins.synchronization.utils import Performer
from remarkable.pw_models.model import NewFileTree, NewMold, NewSystemConfig
from remarkable.worker.app import app

config_name = "sync_external_file"


@app.task
@loop_wrapper
async def run_file_sync():
    await file_sync()


async def check_sys_config(sync_config):
    if sync_config.get("sync_frequency") not in ("daily", "weekly"):
        logging.info(f"wrong sync_frequency {sync_config.get('sync_frequency')}")
        return False

    tree_id = int(sync_config["tree_id"][-1]) if sync_config.get("tree_id") else 0
    tree = await NewFileTree.find_by_id(tree_id)
    if not tree:
        logging.info("tree_id [%s] don't exist", sync_config.get("tree_id"))
        return False

    mold = await NewMold.find_by_id(sync_config.get("schema_id", 0))
    if not mold:
        logging.info("schema [%s] don't exist", sync_config.get("schema_id", 0))
        return False

    return True


async def file_sync():
    config_objs = await NewSystemConfig.list_by_name(config_name)
    logging.info(f">>>>>>>> run task sync_external_file {len(config_objs)}")
    if not config_objs:
        return

    for config_obj in config_objs:
        if not config_obj.enable:
            continue
        sync_config = config_obj.data
        # sync_config = {
        #     'db_driver': 'postgresql',  # 数据库版本
        #     'db_host': '52.82.37.227',  # 服务地址
        #     'db_port': '8201',  # 端口
        #     'db_user': "postgres",  # 用户名
        #     'db_password': 'szse_shang',  # 密码
        #     'db_name': 'scriber',  # 库名
        #     'db_table': 'file_sync',  # 表名
        #     'db_table_pk': 'f001v',  # 主键字段
        #     'db_table_link': 'f009v',  # 链接字段
        #     'tree_id': [648, ],  # 上传项目路径
        #     'schema_id': 152,
        #     'sync_frequency': 'daily',  # 同步频率，可取 daily / weekly
        #     'sync_time': "14:05",  # 同步执行时间，按此格式
        #     'sync_weekday': "",  # 可选，按周定时可选星期几，可取 0~6 对应 周一~周日
        # }

        if not await check_sys_config(sync_config):
            return

        monitor = ScheduleTaskMonitor(
            "%s_%s" % (config_obj.name, config_obj.index),
            sync_config.get("sync_frequency"),
            {
                "time": sync_config.get("sync_time"),
                "weekday": sync_config.get("sync_weekday"),
            },
        )
        if not monitor.acquire_lock():
            logging.info("sync_external_file locked")
            return
        else:
            logging.info("start sync file")

        sync_obj = Performer(sync_config)
        await sync_obj.download()
        await sync_obj.upload()
