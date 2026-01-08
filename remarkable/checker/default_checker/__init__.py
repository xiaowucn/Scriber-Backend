import logging

import attr

from remarkable.checker.base_inspector import BaseInspector, InspectContext
from remarkable.common.enums import AuditAnswerType
from remarkable.config import get_config
from remarkable.converter import SimpleJSONConverter
from remarkable.db import pw_db
from remarkable.plugins.cgs.common.utils import (
    append_suggestion,
    format_suggestion,
)
from remarkable.plugins.cgs.schemas.reasons import (
    CustomRuleNoMatchItem,
    IgnoreConditionItem,
)
from remarkable.pw_models.audit_rule import NewAuditResult, NewAuditRule
from remarkable.pw_models.model import NewAuditStatus
from remarkable.schema.cgs.rules import AuditStatusType
from remarkable.service.inspector_server import InspectorServer

logger = logging.getLogger(__name__)


class Inspector(BaseInspector):
    """
    缺省Inspector, 仅检查页面上配置的审核规则
    """

    def __init__(self, file, mold, question):
        super().__init__(file, mold, question)
        self.manager = None
        self.context = None

    @property
    def inspect_name(self):
        return "default-checker"

    @property
    def answer_type(self):
        answer_type = AuditAnswerType.final_answer
        if self.context and self.context.using_preset_answer:
            answer_type = AuditAnswerType.preset_answer

        return answer_type

    def gen_inspect_payload(self):
        if self.manager.answer["userAnswer"]["items"]:
            answers = SimpleJSONConverter(self.manager.answer).convert()
        else:
            answers = None
        return {
            "fid": self.file.id,
            "qid": self.manager.question.id,
            "schema_id": self.mold.id,
            "answers": answers,
            "answer_type": self.answer_type.value,
        }

    async def send_to_server(self, server_url: str):
        data = self.gen_inspect_payload()
        audit_status_data = {
            "fid": self.file.id,
            "schema_id": self.mold.id,
            "status": AuditStatusType.WAITING_CALLBACK.value,
            "answer_type": self.answer_type.value,
        }
        inspector_server = InspectorServer(server_url)
        is_success = await inspector_server.send(data)
        if not is_success:
            audit_status_data["status"] = AuditStatusType.REMOTE_REQUEST_FAILED.value
        await pw_db.create(NewAuditStatus, **audit_status_data)

    async def run_check(self, **kwargs):
        labels = kwargs["labels"]

        # 外部审核
        if server_url := get_config("inspector.external_url"):
            await self.send_to_server(server_url)

        results = []
        answer_type = self.answer_type
        # 检查页面上配置的规则
        rules = await NewAuditRule.list_reviewing_rules(
            self.mold.id, only_review_passed=get_config("feature.rule_need_review")
        )

        for rule in rules:
            if labels and rule.label not in labels:
                continue

            schema_results = self.manager.build_schema_results(rule.schema_fields)
            matched, reasons, suggestion = get_inspect_result(rule, self.manager)
            results.append(
                NewAuditResult(
                    name=rule.name,
                    is_builtin=False,
                    is_compliance_ai=matched,
                    is_compliance=matched,
                    rule_id=rule.id,
                    origin_contents=[rule.origin_content],
                    suggestion=suggestion,
                    suggestion_ai=suggestion,
                    rule_type=rule.rule_type,
                    reasons=[attr.asdict(item) for item in reasons],
                    tip_content=rule.tip_content,
                    fid=self.file.id,
                    qid=self.manager.question.id,
                    is_compliance_tip=rule.is_compliance_tip,
                    is_noncompliance_tip=rule.is_noncompliance_tip,
                    schema_id=self.mold.id,
                    schema_results=schema_results,
                    order_key=NewAuditResult.get_first_position(schema_results, None),
                    label=rule.label,
                    answer_type=answer_type,
                )
            )

        return results

    async def save_results(self, results, labels, is_preset_answer: bool = False):
        async with pw_db.atomic():
            await self._save_results(results, labels, is_preset_answer=is_preset_answer)

    async def _save_results(self, results, labels, is_preset_answer: bool = False):
        if not labels and results:
            await NewAuditResult.reset_results(self.file.id, self.mold.id, is_preset_answer=is_preset_answer)
            await NewAuditResult.bulk_insert([item.to_dict(exclude=[NewAuditResult.id]) for item in results])
        elif results:
            await NewAuditResult.update_results(labels, results)

    async def prepare_data(self, context: InspectContext):
        self.context = context
        self.manager = context.managers.get(self.question.id)


def get_inspect_result(rule, manager):
    reasons = []
    result = rule.validate(manager)

    matched = result.get("result")
    suggestion = None
    if matched is False:
        reasons.append(CustomRuleNoMatchItem(reason_text=result.get("reason"), matched=result["result"]))
        fields = "".join(rule.rule.schema_fields)
        suggestion = append_suggestion(
            suggestion, format_suggestion(result.get("message") or "", manager) or f'请补充"{fields}"'
        )

    elif matched is None:
        reasons.append(IgnoreConditionItem(reason_text=result.get("reason"), matched=True))

    return matched, reasons, suggestion
