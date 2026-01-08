import functools
import logging
import os

import billiard.process
from celery import Celery
from celery.schedules import crontab

from remarkable.config import get_config

logger = logging.getLogger(__name__)

billiard.process.BaseProcess.daemon = False
app = Celery(
    get_config("worker.app_name"),
    broker=f"redis://:{(get_config('redis.password') or '')}@{get_config('redis.host')}:{get_config('redis.port')}/{get_config('redis.db')}",
    include=[
        "remarkable.worker.tasks",
        "remarkable.plugins.diff.tasks",
        "remarkable.plugins.chinaamc_yx.tasks",
        "remarkable.plugins.answer_poster.tasks",
        "remarkable.plugins.synchronization.tasks",
        "remarkable.plugins.ecitic_dcm.tasks",
        "remarkable.plugins.cmfchina.tasks",
    ],
)

default_queue = {"queue": get_config("worker.default_queue", "celery")}
training_queue = {"queue": get_config("worker.training_queue", "training")}

schedules = {
    # 定时同步答案到指定数据库
    "run_answer_sync": {
        "task": "remarkable.plugins.answer_poster.tasks.run_answer_sync",
        "schedule": crontab(minute="*/10", hour="*"),
        "args": (),
    },
    # 定时同步外部文档
    "run_file_sync": {
        "task": "remarkable.plugins.synchronization.tasks.run_file_sync",
        "schedule": crontab(minute="*/10", hour="*"),
        "args": (),
    },
    # 定时同步华夏星云系统用户
    "run_chinaamc_yx_user_sync": {
        "task": "remarkable.plugins.chinaamc_yx.tasks.sync_chinaamc_user",
        "schedule": crontab(minute="0", hour="0"),
        "args": (),
    },
    # 定时同步中信证券DCM簿记系统数据
    "run_ecitic_dcm_sync": {
        "task": "remarkable.plugins.ecitic_dcm.tasks.sync_dcmbk_project",
        "schedule": crontab(minute="*/10", hour="7-22/1"),
        "args": (),
    },
    # 定时同步中信证券DCM邮箱数据
    "run_sync_data_from_email": {
        "task": "remarkable.plugins.ecitic_dcm.tasks.sync_data_from_email",
        "schedule": crontab(minute="*/10", hour="7-22/1"),
        "args": (),
    },
    # 定时删除招商基金验证分类的文件
    "run_cmfchina_delete_verify_filed_file": {
        "task": "remarkable.plugins.cmfchina.tasks.delete_verify_filed_file",
        "schedule": crontab(minute="0", hour="4"),
        "args": (),
    },
    # 定时同步招商基金邮箱文件
    "run_cmfchina_sync_file_from_email": {
        "task": "remarkable.plugins.cmfchina.tasks.sync_file_from_email",
        "schedule": crontab(minute="*/10", hour="7-22/1"),
        "args": (),
    },
    # 定时同步招商基金邮箱文件
    "run_gjzq_sync_file_from_email": {
        "task": "remarkable.plugins.cmfchina.tasks.sync_file_from_email",
        "schedule": crontab(minute="*/10", hour="7-22/1"),
        "args": (),
    },
    "run_cmfchina_save_audit_result_statistic": {
        "task": "remarkable.plugins.cmfchina.tasks.save_audit_result_statistic",
        "schedule": crontab(minute="10", hour="2"),
        "args": (),
    },
    # 定时同步招商共享盘
    "run_cmfchina_sync_shared_disk": {
        "task": "remarkable.plugins.cmfchina.tasks.sync_shared_disk",
        "schedule": crontab(minute="*/10", hour="7-22/1"),
        "args": (),
    },
}

beat_schedule = {}
cron_task_switch = get_config("client.cron_task_switch") or {}
for key, switch in cron_task_switch.items():
    if key not in schedules or switch is False:
        continue
    beat_schedule[key] = schedules[key]


app.conf.update(
    timezone="Asia/Shanghai",
    task_always_eager=bool(get_config("worker.task_always_eager")),
    enable_utc=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1,
    task_routes={
        # training_queue
        "remarkable.worker.tasks.update_model": training_queue,
        "remarkable.worker.tasks.update_predict_model": training_queue,
        # default_queue
        "remarkable.worker.tasks.*": default_queue,
        "remarkable.plugins.answer_poster.tasks.*": default_queue,
        "remarkable.plugins.synchronization.tasks.*": default_queue,
    },
    beat_schedule=beat_schedule,
    broker_transport_options={
        "sep": ":",
        "queue_order_strategy": "priority",
        "priority_steps": list(range(10)),
        "visibility_timeout": 360000,
    },
    result_accept_content=["application/json", "json"],
    broker_connection_retry_on_startup=True,  # 重启时重连
)


class FakeAsyncTask:
    def __init__(self, task):
        self._task = task

    def _fake(self, *args, **kwargs):
        return self._task(*args, **kwargs)

    def delay(self, *args, **kwargs):
        return self._fake(*args, **kwargs)

    def apply_async(self, *args, **kwargs):
        return self._fake(*args, **kwargs)


def task_adapter(task):
    if os.environ.get("NON_CELERY"):
        return FakeAsyncTask(task)
    return task


def task_log():
    def decorator(func):
        @functools.wraps(func)
        def __inner(*args, **kwargs):
            try:
                logger.info("start call: %s: params: %s + %s;", func.__name__, args, kwargs)
                func(*args, **kwargs)
            except Exception as exc:
                logger.error("TaskError %s: params: %s + %s; %s", func.__name__, args, kwargs, exc)
                logger.exception(exc)
            else:
                logger.info("succeed call: %s: params: %s + %s;", func.__name__, args, kwargs)

        return __inner

    return decorator


if __name__ == "__main__":
    app.start()
