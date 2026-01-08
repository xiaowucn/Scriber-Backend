import logging

import attr

from remarkable.checker.default_checker import Inspector as DefaultInspector
from remarkable.checker.default_checker import get_inspect_result
from remarkable.checker.jsfund_checker.schema_checker import check_schema
from remarkable.config import get_config
from remarkable.pw_models.audit_rule import NewAuditResult, NewAuditRule

logger = logging.getLogger(__name__)


class Inspector(DefaultInspector):
    @property
    def inspect_name(self):
        return "jsfund-checker"

    async def run_check(self, **kwargs):
        labels = kwargs["labels"]
        inspect_fields = []
        answer_type = self.answer_type

        results = []
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

        for result_item in check_schema(
            self.file,
            self.mold,
            self.manager,
            self.reader,
            labels,
            inspect_fields,
        ):
            audit_result = NewAuditResult.from_inspect_result(
                self.manager.question.id, result_item, is_template_rule=False
            )
            audit_result.answer_type = answer_type
            results.append(audit_result)

        return results
