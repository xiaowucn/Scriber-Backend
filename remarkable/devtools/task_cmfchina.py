import logging

from invoke import task

from remarkable.devtools import InvokeWrapper

logger = logging.getLogger(__name__)


@task(klass=InvokeWrapper)
async def update_fields(ctx):
    from remarkable.db import pw_db
    from remarkable.pw_models.audit_rule import NewAuditRule

    rules = list(await pw_db.execute(NewAuditRule.select().where(NewAuditRule.fields == [])))
    for rule in rules:
        rule.fields = rule.schema_fields
        await pw_db.update(rule, only=["fields"])


@task()
def sync_email(ctx):
    from remarkable.plugins.cmfchina.tasks import sync_file_from_email

    sync_file_from_email()


@task()
def sync_disk(ctx):
    from remarkable.plugins.cmfchina.tasks import sync_shared_disk

    sync_shared_disk()


@task(klass=InvokeWrapper)
async def delete_check_fields(ctx):
    from remarkable.db import pw_db
    from remarkable.models.cmf_china import CmfUserCheckFields

    await pw_db.execute(CmfUserCheckFields.delete())


@task(klass=InvokeWrapper)
async def sync_answer_data_stat_task(ctx):
    from remarkable.service.cmfchina.util import sync_answer_data_stat

    await sync_answer_data_stat()
