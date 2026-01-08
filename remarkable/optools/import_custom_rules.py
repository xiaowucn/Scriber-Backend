import re
from collections import defaultdict

from tornado.ioloop import IOLoop

from remarkable.common.constants import RuleMethodType
from remarkable.db import db
from remarkable.pw_models.model import NewMold, NewRuleClass, NewRuleItem
from remarkable.rule.ht.ht_business_rules.accessory_rule import AccessoryRule
from remarkable.rule.ht.ht_business_rules.contract_amount_rule import ContractAmountRule
from remarkable.rule.ht.ht_business_rules.fixed_terms_rule import FixedTermsRule
from remarkable.rule.ht.ht_business_rules.inspector import HT_RULES_CONFIG
from remarkable.rule.ht.ht_business_rules.party_b_employee_rule import PartyBEmployeeRule
from remarkable.rule.ht.ht_business_rules.payment_radio_rule import PaymentRadioRule
from remarkable.rule.ht.ht_business_rules.project_manage_rule import ProjectManageRule
from remarkable.rule.ht.ht_business_rules.result import second_rules
from remarkable.rule.ht.ht_business_rules.subject_rule import SubjectRule
from remarkable.rule.ht.ht_business_rules.tax_rule import TaxRule


async def import_custom_rules():
    await clear_custom_rules()
    for class_name in ("软件开发外包合同", "软件使用许可合同", "硬件采购合同"):
        mold = await NewMold.find_by_name(class_name)
        for rule in HT_RULES_CONFIG[class_name]:
            if isinstance(rule, FixedTermsRule):
                await import_fixed_term(mold.id, rule)
            elif isinstance(rule, ProjectManageRule):
                await import_project_manage_rule(mold.id, rule)
            elif isinstance(rule, SubjectRule):
                await import_subject_rule(mold.id, rule)
            # elif isinstance(rule, PartyBEmployeeRule):
            #     await import_party_b_employee_rule(mold.id, rule)
            elif isinstance(rule, ContractAmountRule):
                await import_contract_amount_rule(mold.id, rule)
            elif isinstance(rule, PaymentRadioRule):
                await import_payment_radio_rule(mold.id, rule)
            elif isinstance(rule, TaxRule):
                await import_tax_rule(mold.id, rule)
            elif isinstance(rule, AccessoryRule):
                await import_accessory_rule(mold.id, rule)
            else:
                pass


async def clear_custom_rules():
    await db.raw_sql("delete from rule_class;")
    await db.raw_sql("delete from rule_item;")


rule_class_cache = defaultdict(dict)


async def get_or_create_rule_class(mid: int, name: str, rule_type: RuleMethodType):
    mold_classes = rule_class_cache[mid]
    if name not in mold_classes:
        mold_classes[name] = await NewRuleClass.create(
            **{
                "name": name,
                "mold": mid,
                "method_type": rule_type.value,
            }
        )
    return mold_classes[name]


async def import_fixed_term(mid: int, program_rule: FixedTermsRule):
    """固定条款"""

    def revise_pattern(pat_str):
        pat_str = re.sub(r"\n\s*", r"\s*", pat_str)
        pat_str = re.sub(r"\\n\?", "", pat_str)
        return pat_str

    rule_class = await get_or_create_rule_class(mid, program_rule.name, RuleMethodType.TERM)
    for key, col in program_rule.cols.items():
        if isinstance(program_rule.patterns[key], list):
            patterns = [revise_pattern(p.pattern) for p in program_rule.patterns[key]]
        else:
            patterns = [revise_pattern(program_rule.patterns[key].pattern)]
        await NewRuleItem.create(
            **{
                "name": "{}需与模板一致".format(col),
                "mold": rule_class.mold,
                "class_name": rule_class.id,
                "method_type": rule_class.method_type,
                "data": {
                    "column": col,
                    "patterns": patterns,
                },
            }
        )


async def import_project_manage_rule(mid: int, program_rule: ProjectManageRule):
    rule_class = await get_or_create_rule_class(mid, program_rule.name, RuleMethodType.TERM)
    for col in program_rule.cols.values():
        await NewRuleItem.create(
            **{
                "name": "{}需与模板一致".format(col),
                "mold": rule_class.mold,
                "class_name": rule_class.id,
                "method_type": rule_class.method_type,
                "data": {
                    "column": col,
                    "patterns": [r"增加工作量比例(<=|=|<|小于|等于|小于等于)\s*?[1-5]\s*?[%％]"],
                },
            }
        )


async def import_subject_rule(mid: int, program_rule: SubjectRule):
    rule_class = await get_or_create_rule_class(mid, program_rule.name, RuleMethodType.TERM)
    for col in program_rule.cols.values():
        await NewRuleItem.create(
            **{
                "name": "{}需与模板一致".format(col),
                "mold": rule_class.mold,
                "class_name": rule_class.id,
                "method_type": rule_class.method_type,
                "data": {
                    "column": col,
                    "patterns": [r".+"],
                },
            }
        )


async def import_party_b_employee_rule(mid: int, program_rule: PartyBEmployeeRule):
    await get_or_create_rule_class(mid, program_rule.name, RuleMethodType.TERM)
    # TODO
    # for key, col in program_rule.cols.items():
    #     rule_item = await NewRuleItem.create({
    #         "name": col,
    #         "mold": rule_class.mold,
    #         "class": rule_class.id,
    #         "method_type": rule_class.method_type,
    #         "data": json.dumps({
    #             "column": col,
    #             "patterns": r".+",
    #         })
    #     })


async def import_contract_amount_rule(mid: int, program_rule: ContractAmountRule):
    rule_class = await get_or_create_rule_class(mid, program_rule.name, RuleMethodType.FORMULA)
    await NewRuleItem.create(
        **{
            "name": program_rule.name,
            "mold": rule_class.mold,
            "class_name": rule_class.id,
            "method_type": rule_class.method_type,
            "data": {
                "formula": "{合同总金额小写}={第一笔付款小写}+{第二笔付款小写}+{第三笔付款小写}+{第四笔付款小写}+{第五笔付款小写}+{第六笔付款小写}",
            },
        }
    )


async def import_payment_radio_rule(mid: int, program_rule: PaymentRadioRule):
    rule_class = await get_or_create_rule_class(mid, program_rule.name, RuleMethodType.FORMULA)
    for num in ("一", "二", "三", "四", "五", "六"):
        await NewRuleItem.create(
            **{
                "name": f"第{num}笔付款比例校验",
                "mold": rule_class.mold,
                "class_name": rule_class.id,
                "method_type": rule_class.method_type,
                "data": {
                    "formula": "{第%s笔付款小写}={合同总金额小写}*{第%s笔付款比例}" % (num, num),
                },
            }
        )


async def import_tax_rule(mid: int, program_rule: PaymentRadioRule):
    rule_class = await get_or_create_rule_class(mid, program_rule.name, RuleMethodType.FORMULA)
    await NewRuleItem.create(
        **{
            "name": "含税合同总金额 = 不含税合同总金额 + 税款",
            "mold": rule_class.mold,
            "class_name": rule_class.id,
            "method_type": rule_class.method_type,
            "data": {
                "formula": "{合同总金额小写}={不含税合同总金额小写}+{税款小写}",
            },
        }
    )


async def import_accessory_rule(mid: int, program_rule: PaymentRadioRule):
    rule_class = await get_or_create_rule_class(mid, program_rule.name, RuleMethodType.TERM)
    for col in program_rule.cols.values():
        await NewRuleItem.create(
            **{
                "name": second_rules["accessory"].format(col.split("-")[-1]),
                "mold": rule_class.mold,
                "class_name": rule_class.id,
                "method_type": rule_class.method_type,
                "data": {
                    "column": col,
                    "patterns": [r".+"],
                },
            }
        )


async def main():
    await import_custom_rules()


if __name__ == "__main__":
    IOLoop.current().run_sync(main)
