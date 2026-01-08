from remarkable.plugins.cgs.common.utils import (
    append_suggestion,
    format_suggestion,
)
from remarkable.plugins.cgs.schemas.reasons import (
    CustomRuleNoMatchItem,
    FieldNoMatchItem,
    IgnoreConditionItem,
    SchemaFailedItem,
    Template,
)


def apply_fund_checker_result(rule, manager, fund_manager_checker):
    reasons = []
    matched, _reasons, suggestion = fund_manager_checker.check(
        rule.schema_fields, rule.validate_bond_info, rule.validate_company_info
    )
    reasons.extend(_reasons)

    if matched:
        result = rule.validate(manager)

        matched = result.get("result")
        if matched is False:
            reasons.append(CustomRuleNoMatchItem(reason_text=result.get("reason"), matched=result["result"]))
            fields = "".join(rule.schema_fields)
            suggestion = append_suggestion(
                suggestion, format_suggestion(result.get("message") or "", manager) or f'请补充"{fields}"'
            )

        elif matched is None:
            reasons.append(IgnoreConditionItem(reason_text=result.get("reason"), matched=True))

    return matched, reasons, suggestion


class FundManagerInfoChecker:
    def __init__(self, fund_manager_info, company_info):
        self.fund_manager_info = fund_manager_info
        self.company_info = company_info

    @classmethod
    def validate_field(cls, field, info, name):
        if field in info:
            if not info[field].get("answer") or not info[field]["answer"].value:
                return SchemaFailedItem(reason_text=f"{field}为空", suggestion=f"请补充{field}")
            if info[field]["text"] is None:
                return SchemaFailedItem(reason_text=f"{field}未在{name}中找到", suggestion=f"请修改{field}")
            if not info[field].get("matched"):
                if not info[field].get("ignore_check"):
                    answer = info[field]["answer"]
                    diff_results = None
                    if info[field].get("diff"):
                        diff_results = info[field]["diff"]
                    return FieldNoMatchItem(
                        page=answer.page,
                        outlines=answer.outlines,
                        content=answer.value,
                        name=name,
                        diff=diff_results,
                        template=Template(name=name, content=info[field]["text"]),
                    )
        return None

    def check(self, fields, validate_bond_info=False, validate_company_info=False):
        matched = True
        reasons = []

        if not validate_bond_info and not validate_company_info:
            return matched, reasons, None

        for field in fields:
            if validate_company_info:
                if field in self.company_info:
                    reason = self.validate_field(field, self.company_info, "国企信数据")
                    if reason:
                        reasons.append(reason)
                    continue

            if validate_bond_info:
                if field in self.fund_manager_info:
                    reason = self.validate_field(field, self.fund_manager_info, "基金协会数据")
                    if reason:
                        reasons.append(reason)

        suggestion = None
        if reasons:
            matched = all(item.matched for item in reasons)
            suggestion = "\n".join(item.render_suggestion(None, "") for item in reasons)

        return matched, reasons, suggestion
