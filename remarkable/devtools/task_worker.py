import csv
import datetime
import logging
from subprocess import Popen

from invoke import task
from utensils.syncer import sync

logger = logging.getLogger(__name__)


@task
def all_in_one(ctx):
    from remarkable.config import get_config
    from remarkable.devtools import proc_check

    project_root = ctx["project_root"]
    level = get_config("logging.level") or "debug"
    proc1 = Popen(
        f"celery -A remarkable.worker.app worker -B -n 'norm-%n@%h' -l {level} -c 2 -Q celery",
        shell=True,
        cwd=project_root,
    )
    proc2 = Popen(
        f"celery -A remarkable.worker.app worker -n 'training-%n@%h' -l {level} -c 1 -Q training",
        shell=True,
        cwd=project_root,
    )

    proc_check(proc1)
    proc_check(proc2)


@task
@sync
async def create_user(ctx, name, passwd):
    """创建用户或者更新已有用户密码"""

    from remarkable.common.constants import FeatureSchema
    from remarkable.db import pw_db
    from remarkable.models.new_user import NewAdminUser
    from remarkable.user.handlers import gen_password, gen_salt

    user = await NewAdminUser.find_by_kwargs(name=name)
    salt = gen_salt()
    if user:
        logger.info(f"User: {name} already exists, id: {user.id}, will update password and salt")
        user.salt = salt
        user.password = gen_password(passwd, user.salt)
        await pw_db.update(user, only=["salt", "password"])
    else:
        user = await NewAdminUser.create(
            name=name,
            salt=salt,
            password=gen_password(passwd, salt),
            permission=FeatureSchema.base_perms_to_db(),
        )
        logger.info(f"User: {name} created, id: {user.id}")


@task
@sync
async def migrate_users(ctx, path):
    """迁移用户账号（用于迁移子系统帐号到用户OA系统）"""
    from remarkable.db import pw_db
    from remarkable.models.new_user import NewAdminUser

    count = 0
    with open(path, newline="") as fp:
        csv_reader = csv.reader(fp)
        for idx, (old, new, *_) in enumerate(csv_reader, 1):  # noqa
            old, new = old.strip(), new.strip()
            if "admin" in (old, new):
                logger.warning(f"Skip admin user: {old} -> {new}")
                continue
            if user := await pw_db.first(
                NewAdminUser.select().where(
                    NewAdminUser.name == old,
                    NewAdminUser.name != new,
                    NewAdminUser.ext_id.is_null(),  # 未绑定外部账号
                )
            ):
                user.name = new
                await pw_db.update(user, only=["name"])
                logger.info(f"User: {old=} -> {new=} updated")
                count += 1
            else:
                logger.warning(f"User: does not exist or already migrated: {old=}, {new=}")
    logger.info(f"Summary: {count} users migrated, {idx - count} users skipped")


@task
def find_inactive_users(ctx, days=30):
    """列出不活跃用户"""
    from remarkable.common.util import loop_wrapper
    from remarkable.models.new_user import NewAdminUser

    @loop_wrapper
    async def _run():
        delta = datetime.datetime.now() - datetime.timedelta(days=days)
        lines = [("ID", "NAME", "LAST LOGIN", "COUNT")]
        count = 0
        for user in await NewAdminUser.find_by_kwargs(delegate="all"):
            last_login_at = datetime.datetime.fromtimestamp(user.login_utc)
            if last_login_at < delta:
                lines.append((user.id, user.name, last_login_at, user.login_count))
                count += 1

        if count:
            print(f"The inactive users({count}) in {days} days are as follows:")
            for line in lines:
                print("%4s\t%12s\t%20s\t%5s" % line)
        else:
            print("No inactive users found")

    _run()
