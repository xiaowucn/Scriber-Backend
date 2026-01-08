import sys
import time

import pandas as pd
import sqlalchemy.exc
from invoke import run, task
from sqlalchemy import create_engine

from remarkable.config import get_config


def _get_dsn_str():
    db_config = get_config("customer_settings.oracle")
    user = db_config.get("user")
    password = db_config.get("password")
    dsn = db_config.get("dsn")
    return f"oracle+cx_oracle://{user}:{password}@{dsn}"


def _sync_execute(query):
    engine = create_engine(_get_dsn_str(), connect_args={"encoding": "UTF-8", "nencoding": "UTF-8", "events": True})
    with engine.begin() as conn:
        return conn.execute(query)


def _alembic_db_task(ctx, name, command):
    tries = 10
    while tries > 0:
        try:
            _sync_execute("select * from v$version")
        except sqlalchemy.exc.OperationalError:
            print(f"{tries}: Database not ready, retrying...")
            tries -= 1
            time.sleep(1)
        else:
            break
    else:
        print(f"{tries}: Database not available, will exit")
        sys.exit(-1)
    cmd = "PYTHONPATH={}:$PYTHONPATH alembic -c misc/gffunds/alembic.ini -n {} -x dburl={} {}"
    run(cmd.format(ctx["project_root"], name, str(_get_dsn_str()), command))


@task
def revision(ctx, msg):
    cmd = 'alembic -c misc/gffunds/alembic.ini -n db revision -m "{}"'
    run(cmd.format(msg))


@task
def upgrade(ctx, to_revision="head"):
    _alembic_db_task(ctx, "db", "upgrade %s" % to_revision)


@task
def downgrade(ctx, to_revision):
    _alembic_db_task(ctx, "db", "downgrade {}".format(to_revision))


@task
def reset(ctx):
    _alembic_db_task(ctx, "db", "downgrade base")


@task
def version(ctx):
    _alembic_db_task(ctx, "db", "current")


@task
def import_fax(ctx, path):
    """import data from excel file"""
    from remarkable.db import pw_db
    from remarkable.service.gffund_fax_process import process_df_fax

    df = pd.read_excel(path, dtype=str)
    with pw_db.allow_sync():
        query = process_df_fax(df)
        query.execute()
    print("====================Successfully imported fax data !!!=====================")
