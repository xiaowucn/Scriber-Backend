import logging
from datetime import datetime, timedelta

from sqlalchemy.engine.url import URL

from remarkable.common.util import loop_wrapper, name2driver
from remarkable.db import init_rdb, peewee_transaction_wrapper
from remarkable.models.new_file import NewFile
from remarkable.plugins.answer_poster.builder import TableBuilder
from remarkable.plugins.answer_poster.poster import AnswerPoster
from remarkable.pw_models.model import NewMold, NewSystemConfig
from remarkable.pw_models.question import NewQuestion
from remarkable.worker.app import app

CONFIG_NAME = "answer_sync_db"


@app.task
@loop_wrapper
@peewee_transaction_wrapper
async def run_answer_sync():
    await answer_sync()


async def answer_sync():
    sync_configs = await NewSystemConfig.list_by_name(CONFIG_NAME)
    if not sync_configs:
        return

    for sync_config in sync_configs:
        if not sync_config.enable:
            continue
        monitor = ScheduleTaskMonitor(
            "answer_sync_%s" % sync_config.index,
            sync_config.data["sync_frequency"],
            {"time": sync_config.data.get("sync_time"), "weekday": sync_config.data.get("sync_weekday")},
        )
        if not monitor.acquire_lock():
            return
        logging.info("start answer sync by schedule")

        dsn_url = URL(
            drivername=name2driver(sync_config.data.get("db_driver")),
            host=sync_config.data.get("db_host"),
            port=sync_config.data.get("db_port"),
            username=sync_config.data.get("db_user"),
            password=sync_config.data.get("db_password"),
            database=sync_config.data.get("db_name"),
        )

        mold = await NewMold.find_by_id(sync_config.data.get("schema_id", 0))
        if not mold:
            logging.error(f"can't find mold {mold}, stop sync answer")
            return
        questions = await NewQuestion.list_by_range(mold=mold.id)
        if not questions:
            continue
        try:
            builder = TableBuilder()
            orm_classes = builder.build(mold.data, dsn_url)
            poster = AnswerPoster(dsn_url, orm_classes)
            for question in questions:
                file = await NewFile.find_by_id(question.fid)
                answer = (
                    question.answer
                    if question.answer and question.answer["userAnswer"]["items"]
                    else question.preset_answer
                )
                if not answer:
                    continue
                if answer["schema"]["version"] != mold.checksum:
                    logging.debug("file %s, answer version is different from mold, pass", question.fid)
                    continue
                question_key = "%s_%s" % (question.fid, question.mold)
                logging.info("sync record %s", question_key)
                poster.post(question_key, file.name, None, question.mold, question.updated_utc, answer)
        except Exception as exp:
            logging.exception(exp)


class ScheduleTaskMonitor:
    schedule_lock_key = "schedule_lock"

    def __init__(self, name, frequency, config):
        logging.info("ScheduleTaskMonitor : %s, %s, %s", name, frequency, config)
        self.name = name
        self.frequency = frequency
        self.config = config
        self.rdb = init_rdb()

    def acquire_lock(self):
        if self.frequency == "daily":
            return self.acquire_lock_daily()
        if self.frequency == "weekly":
            return self.acquire_lock_weekly()
        raise Exception("undefined frequency: %s" % self.frequency)

    def last_run_time_key(self):
        return "task_%s_last_run_time" % self.name

    def last_run_message_key(self):
        return "task_%s_last_run_message" % self.name

    def acquire_lock_daily(self):
        last_run_time = datetime.fromtimestamp(
            int(self.rdb.hget(self.schedule_lock_key, self.last_run_time_key()) or "0")
        )
        run_time = self.config.get("time") or "0:0"
        run_hour, run_minute = [int(c) for c in run_time.split(":")]
        next_run_time = last_run_time + timedelta(
            days=1, hours=run_hour - last_run_time.hour, minutes=run_minute - last_run_time.minute
        )
        now = datetime.now()
        if now < next_run_time:
            logging.debug(f"next run time {next_run_time}")
            return False

        self.rdb.hset(self.schedule_lock_key, self.last_run_time_key(), str(int(now.timestamp())))
        return True

    def acquire_lock_weekly(self):
        last_run_time = datetime.fromtimestamp(
            int(self.rdb.hget(self.schedule_lock_key, self.last_run_time_key()) or "0")
        )
        run_weekday = int(self.config.get("weekday", "0"))
        run_hour, run_minute = [int(c) for c in self.config.get("time", "0:0").split(":")]
        next_run_time = last_run_time + timedelta(
            days=run_weekday - last_run_time.weekday + 7,
            hours=run_hour - last_run_time.hour,
            minutes=run_minute - last_run_time.minute,
        )
        now = datetime.now()
        if now < next_run_time:
            logging.debug(f"next run time {next_run_time}")
            return False

        self.rdb.hset(self.schedule_lock_key, self.last_run_time_key(), str(int(now.timestamp())))
        return True


if __name__ == "__main__":
    run_answer_sync.delay()
