import re
import sys
import time

import peewee
from invoke import run, task
from utensils.syncer import sync

P_REVISION_FILE = re.compile(r"Generating\s+(/(?!\.py).+\.py)\s+")


def db_dsn(driver="postgresql+psycopg2", cover_password: bool = False):
    from remarkable.config import get_config

    return (
        f"{driver}://"
        f"{get_config('db.user')}:"
        f"{get_config('db.password') if not cover_password else '*****'}@"
        f"{get_config('db.host')}:"
        f"{get_config('db.port')}/"
        f"{get_config('db.dbname')}"
    ), f"-x dbschema={get_config('db.schema')}"


def _alembic_db_task(ctx, name, command):
    from remarkable.config import get_config
    from remarkable.db import pw_db

    tries = 60
    while tries > 0:
        try:
            with pw_db.sync_execute("SELECT version()") as cursor:
                _ = cursor.fetchone()
        except peewee.OperationalError:
            print(f"{tries}: Database not ready, retrying...")
            tries -= 1
            time.sleep(1)
        else:
            break
    else:
        print(f"{tries}: Database not available, will exit")
        sys.exit(-1)
    cmd = "PYTHONPATH={}:$PYTHONPATH alembic -c misc/alembic.ini -n {} -x dburl={} {} {}"

    if get_config("db.type") == "mysql":
        dsn, _ = db_dsn("mysql+pymysql")
        schema = ""
    else:
        dsn, schema = db_dsn()
    return run(cmd.format(ctx["project_root"], name, dsn, schema, command))


@task
def revision(ctx, msg):
    cmd_result = _alembic_db_task(ctx, "db", f'revision -m "{msg}"')
    if cmd_result.ok:
        vision_path = P_REVISION_FILE.search(cmd_result.stdout).group(1)
        run(
            f"which charm && charm {vision_path} || echo '!!!Notify: PyCharm --> Tools --> Create Command Line Launcher'"
        )


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
def cli(ctx, cmd_str):
    """execute some other alembic commands"""
    _alembic_db_task(ctx, "db", cmd_str)


@task
def flush_rdb(ctx):
    from remarkable.db import init_rdb

    init_rdb().flushdb()


@task
@sync
async def sql(ctx):
    import readline  # noqa

    from remarkable.db import pw_db

    while True:
        try:
            _sql = input("SQL > ").strip()
        except KeyboardInterrupt:
            print("\r")
            continue
        except EOFError:
            print("\n退出")
            break

        if _sql.lower() in ("exit", "quit", "\\q"):
            print("再见")
            break
        try:
            result = await pw_db.execute(_sql)
            if not result:
                print("Empty result")
                continue
            for row in result:
                print(row)
        except Exception as e:
            print(f"❌ 执行出错: {e}")
