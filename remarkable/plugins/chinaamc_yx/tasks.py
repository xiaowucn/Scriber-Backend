import logging

import httpx
from peewee import fn
from pydantic import BaseModel, Field

from remarkable.common.util import loop_wrapper
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.chinaamc_yx import CompareTask, UserInfo
from remarkable.models.new_user import NewAdminUser
from remarkable.service.chinaamc_yx import chapter_diff, compare_task_diff
from remarkable.worker.app import app

logger = logging.getLogger(__name__)


class Person(BaseModel):
    ext_id: str = Field(alias="id")
    name: str
    dept_ids: list[str] = Field(alias="deptid")
    ext_from: str = "chinaamc_yx"
    password: str = ""
    salt: str = ""
    permission: list[dict] = Field(default_factory=lambda: [{"perm": "browse"}])


@app.task
@loop_wrapper
async def run_compare_task(task_id: int):
    task = await CompareTask.get_by_id(task_id)
    await compare_task_diff(task)


@app.task
@loop_wrapper
async def run_chapter_diff_task(task_id: int):
    task = await CompareTask.get_by_id(task_id)
    await chapter_diff(task)


@app.task
@loop_wrapper
async def sync_chinaamc_user():
    logger.info("start sync chinaamc user")
    option = get_config("chinaamc_yx.sync.user")
    if not option:
        logger.info("sync chinaamc user disabled")
        return
    rsp = await httpx.AsyncClient().get(f"{option['url']}", params={"token": option["token"], "sysCode": "scriber"})
    assert rsp.status_code == 200
    body = rsp.json()
    exist_ext_ids = set(
        await pw_db.scalars(
            NewAdminUser.select(NewAdminUser.ext_id).where(
                NewAdminUser.ext_from == "chinaamc_yx",
                fn.EXISTS(UserInfo.select().where(UserInfo.user == NewAdminUser.id)),
            )
        )
    )
    persons = [Person.model_validate(item) for item in body["data"]["person"]]
    api_ext_ids = {person.ext_id for person in persons}
    del_ext_ids = exist_ext_ids - api_ext_ids
    new_persons = [item for item in persons if item.ext_id not in exist_ext_ids]
    async with pw_db.atomic():
        async with pw_db.atomic():
            del_user_ids = await pw_db.scalars(
                NewAdminUser.select(NewAdminUser.id).where(NewAdminUser.ext_id.in_(del_ext_ids))
            )
            await pw_db.execute(NewAdminUser.delete().where(NewAdminUser.id.in_(del_user_ids)))
            await pw_db.execute(UserInfo.delete().where(UserInfo.user.in_(del_user_ids)))
            await NewAdminUser.bulk_insert([item.model_dump(exclude={"dept_ids"}) for item in new_persons])

        new_users = await pw_db.execute(
            NewAdminUser.select(NewAdminUser.id, NewAdminUser.ext_id)
            .where(
                NewAdminUser.ext_id.in_([item.ext_id for item in new_persons]),
                NewAdminUser.ext_from == "chinaamc_yx",
            )
            .namedtuples()
        )
        user_by_ext_id = {item.ext_id: item.id for item in new_users}
        new_user_infos = [{"uid": user_by_ext_id[item.ext_id], "dept_ids": item.dept_ids} for item in new_persons]
        await UserInfo.bulk_insert(new_user_infos)
    logger.info("end sync chinaamc user, create %d, delete %d", len(new_persons), len(del_user_ids))


if __name__ == "__main__":
    run_compare_task(208)
