from collections import defaultdict

from remarkable.common.enums import AuditAnswerType
from remarkable.common.util import get_key_path
from remarkable.db import pw_db
from remarkable.pw_models.audit_rule import NewAuditResult


async def get_updated_rule_labels(fid, schema_id, updated, ignore_edited=True):
    cond = (
        (NewAuditResult.fid == fid)
        & (NewAuditResult.schema_id == schema_id)
        & (NewAuditResult.answer_type == AuditAnswerType.final_answer)
    )
    if ignore_edited:
        cond &= ~NewAuditResult.is_edited

    results = await pw_db.execute(NewAuditResult.select().where(cond))
    field_mapping = defaultdict(list)
    for result in results:
        for field in result.schema_fields:
            field_mapping[field].append([result.label, result.id])

    rule_labels = {}
    for item in updated:
        field = get_key_path(item)
        if field in field_mapping:
            for label, result_id in field_mapping[field]:
                rule_labels[label] = result_id
    return rule_labels
