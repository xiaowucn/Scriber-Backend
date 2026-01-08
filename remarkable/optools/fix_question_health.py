import logging

from remarkable.common.util import loop_wrapper
from remarkable.config import get_config
from remarkable.db import db, peewee_transaction_wrapper


@loop_wrapper
@peewee_transaction_wrapper
async def fix_health():
    fix_sql = """
        update question
            set health = COALESCE(origin_health, %(default_health)s) - (select count(1) from answer where qid = question.id and type=1 and status=1)
        ;
        """
    status_rsp = await db.raw_sql(fix_sql, "status", **{"default_health": get_config("web.default_question_health", 2)})
    logging.info("fix %s question", db.get_count_in_status_rsp(status_rsp))


if __name__ == "__main__":
    fix_health()
