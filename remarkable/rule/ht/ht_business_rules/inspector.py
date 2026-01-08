import json
from copy import deepcopy
from json.decoder import JSONDecodeError

from remarkable.common.constants import AuditStatusEnum, ComplianceStatus, RuleMethodType
from remarkable.common.storage import localstorage
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.pw_models.model import NewRuleClass, NewRuleItem
from remarkable.rule.ht.ht_business_rules.accessory_rule import AccessoryRule
from remarkable.rule.ht.ht_business_rules.case_rule import CaseRule
from remarkable.rule.ht.ht_business_rules.contract_amount_rule import ContractAmountRule
from remarkable.rule.ht.ht_business_rules.custom_terms_rule import CustomTermsRule
from remarkable.rule.ht.ht_business_rules.fixed_terms_rule import FixedTermsRule
from remarkable.rule.ht.ht_business_rules.formula_rule import FormulaRule
from remarkable.rule.ht.ht_business_rules.last_charge_rule import LastChargeRule
from remarkable.rule.ht.ht_business_rules.party_b_employee_rule import PartyBEmployeeRule
from remarkable.rule.ht.ht_business_rules.patterns import hard_pur_patterns, soft_dev_patterns, soft_use_patterns
from remarkable.rule.ht.ht_business_rules.payment_radio_rule import PaymentRadioRule
from remarkable.rule.ht.ht_business_rules.pm_rule import PMRule
from remarkable.rule.ht.ht_business_rules.project_manage_rule import ProjectManageRule
from remarkable.rule.ht.ht_business_rules.subject_rule import SubjectRule
from remarkable.rule.ht.ht_business_rules.tax_amount_rule import TaxAmountRule
from remarkable.rule.ht.ht_business_rules.tax_rate_formula_rule import TaxRateFormulaRule
from remarkable.rule.ht.ht_business_rules.tax_rate_rule import TaxRateRule
from remarkable.rule.ht.ht_business_rules.tax_rule import TaxRule
from remarkable.rule.inspector import LegacyInspector


class HTInspector(LegacyInspector):
    """海通旧合规检查类，暂不使用
    保留用于 `效果比对` 以及 `旧规则导入到自定义规则`
    """

    def __init__(self, schema_name, **kwargs):
        kwargs["mold"] = schema_name
        kwargs["rules"] = HT_RULES_CONFIG.get(schema_name) or []
        super(HTInspector, self).__init__(**kwargs)


HT_RULES_CONFIG = {
    "default": [],
    "软件开发外包合同": [
        CaseRule(
            {
                "con_amount_upper": "合同总金额大写",
                "con_amount_lower": "合同总金额小写",
                "con_amount_upper1": "第一笔付款大写",
                "con_amount_lower1": "第一笔付款小写",
                "con_amount_upper2": "第二笔付款大写",
                "con_amount_lower2": "第二笔付款小写",
                "con_amount_upper3": "第三笔付款大写",
                "con_amount_lower3": "第三笔付款小写",
                "con_amount_upper4": "第四笔付款大写",
                "con_amount_lower4": "第四笔付款小写",
                "con_amount_upper5": "第五笔付款大写",
                "con_amount_lower5": "第五笔付款小写",
                "con_amount_upper6": "第六笔付款大写",
                "con_amount_lower6": "第六笔付款小写",
                "notax_amount_upper": "不含税合同总金额大写",
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_upper": "税款大写",
                "tax_lower": "税款小写",
                "ops_amount_upper": "维护费用大写",
                "ops_amount_lower": "维护费用小写",
            }
        ),
        ContractAmountRule(
            {
                "con_amount_upper": "合同总金额大写",
                "con_amount_lower": "合同总金额小写",
                "con_amount_upper1": "第一笔付款大写",
                "con_amount_lower1": "第一笔付款小写",
                "con_amount_upper2": "第二笔付款大写",
                "con_amount_lower2": "第二笔付款小写",
                "con_amount_upper3": "第三笔付款大写",
                "con_amount_lower3": "第三笔付款小写",
                "con_amount_upper4": "第四笔付款大写",
                "con_amount_lower4": "第四笔付款小写",
                "con_amount_upper5": "第五笔付款大写",
                "con_amount_lower5": "第五笔付款小写",
                "con_amount_upper6": "第六笔付款大写",
                "con_amount_lower6": "第六笔付款小写",
                "tax_upper": "税款大写",
                "tax_lower": "税款小写",
            }
        ),
        PaymentRadioRule(),
        TaxRule(
            {
                "con_amount_upper": "合同总金额大写",
                "con_amount_lower": "合同总金额小写",
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_lower": "税款小写",
            }
        ),
        TaxRateRule(
            {
                "tax_rate": "增值税使用税率",
                "tax_payer": "乙方纳税人资质",
            }
        ),
        TaxAmountRule(
            {
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_rate": "增值税使用税率",
                "tax_lower": "税款小写",
            }
        ),
        TaxRateFormulaRule(
            {
                "con_amount_lower": "合同总金额小写",
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_rate": "增值税使用税率",
            }
        ),
        LastChargeRule(
            {
                "last_charge": "最后一笔费用支付",
            }
        ),
        FixedTermsRule(
            {
                "vat_term1": "增值税涉税固定条款1",
                "vat_term2": "增值税涉税固定条款2",
                "vat_term3": "增值税涉税固定条款3",
                "vat_term4": "增值税涉税固定条款4",
                "patent_term": "知识产权",
                "partyb_code_function": "代码功能范围条款",
                "partyb_info_security": "信息安全条款",
                "partyb_sys_bug": "系统漏洞条款",
                "partyb_issue_waring": "重大事项告知条款",
                "partyb_emergency_plan": "应急预案条款",
                "partyb_confidentiality": "乙方权利和义务-保密责任",
                "confidentiality": "保密责任",
                "breach_duty1": "违约责任1",
                "breach_duty2": "违约责任2",
                "breach_duty3": "违约责任3",
                "breach_duty4": "违约责任4",
                "partya_emergency_plan": "应急预案条款（甲方）",
                "partyb_service_commitment": "乙方服务承诺",
                "contract_validity": "合同效力",
                "partyb_right_safety": "乙方权利和义务-安全生产相关条款",
                "partyb_record_supervision": "乙方义务-备案监督条款",
                "partyb_violation_supervision": "乙方义务-违规监督条款",
                "partyb_arbitration_notice": "乙方义务-纠纷、仲裁告知条款",
                "partyb_illegal_procurement": "乙方义务-违规采购条款",
                "partyb_compliance_management": "乙方义务-合规管理条款",
                "partyb_quality_control": "乙方义务-质量控制条款",
            },
            soft_dev_patterns,
        ),
        ProjectManageRule(
            {
                "project_manage": "项目变更管理",
            }
        ),
        PMRule(),
        SubjectRule(),
        AccessoryRule(
            {
                "accessory_sow": "附件-项目工作说明书",
                "accessory_nda": "附件-保密协议",
            }
        ),
        PartyBEmployeeRule(),
    ],
    "软件使用许可合同": [
        CaseRule(
            {
                "con_amount_upper": "合同总金额大写",
                "con_amount_lower": "合同总金额小写",
                "con_amount_upper1": "第一笔付款大写",
                "con_amount_lower1": "第一笔付款小写",
                "con_amount_upper2": "第二笔付款大写",
                "con_amount_lower2": "第二笔付款小写",
                "con_amount_upper3": "第三笔付款大写",
                "con_amount_lower3": "第三笔付款小写",
                "con_amount_upper4": "第四笔付款大写",
                "con_amount_lower4": "第四笔付款小写",
                "con_amount_upper5": "第五笔付款大写",
                "con_amount_lower5": "第五笔付款小写",
                "con_amount_upper6": "第六笔付款大写",
                "con_amount_lower6": "第六笔付款小写",
                "notax_amount_upper": "不含税合同总金额大写",
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_upper": "税款大写",
                "tax_lower": "税款小写",
                "ops_amount_upper": "维护费用大写",
                "ops_amount_lower": "维护费用小写",
            }
        ),
        ContractAmountRule(
            {
                "con_amount_upper": "合同总金额大写",
                "con_amount_lower": "合同总金额小写",
                "con_amount_upper1": "第一笔付款大写",
                "con_amount_lower1": "第一笔付款小写",
                "con_amount_upper2": "第二笔付款大写",
                "con_amount_lower2": "第二笔付款小写",
                "con_amount_upper3": "第三笔付款大写",
                "con_amount_lower3": "第三笔付款小写",
                "con_amount_upper4": "第四笔付款大写",
                "con_amount_lower4": "第四笔付款小写",
                "con_amount_upper5": "第五笔付款大写",
                "con_amount_lower5": "第五笔付款小写",
                "con_amount_upper6": "第六笔付款大写",
                "con_amount_lower6": "第六笔付款小写",
            }
        ),
        PaymentRadioRule(),
        TaxRule(
            {
                "con_amount_upper": "合同总金额大写",
                "con_amount_lower": "合同总金额小写",
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_lower": "税款小写",
            }
        ),
        TaxRateRule(
            {
                "tax_rate": "增值税税率",
                "tax_payer": "乙方纳税人资质",
            }
        ),
        TaxAmountRule(
            {
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_rate": "增值税税率",
                "tax_lower": "税款小写",
            }
        ),
        TaxRateFormulaRule(
            {
                "con_amount_lower": "合同总金额小写",
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_rate": "增值税税率",
            }
        ),
        LastChargeRule(
            {
                "last_charge": "最后一笔付款条件",
            }
        ),
        FixedTermsRule(
            {
                "vat_term1": "增值税涉税固定条款1",
                "vat_term2": "增值税涉税固定条款2",
                "vat_term3": "增值税涉税固定条款3",
                "vat_term4": "增值税涉税固定条款4",
                "partyb_code_function": "代码功能及规范条款",
                "partyb_info_security": "信息安全条款",
                "partyb_sys_bug": "系统漏洞条款",
                "partyb_data_safe": "数据安全条款",
                "partyb_issue_waring": "重大事项告知条款",
                "partyb_emergency_plan": "应急预案条款",
                "partyb_confidentiality": "保密责任条款",
                "confidentiality": "保密责任",
                "breach_duty1": "违约责任1",
                "breach_duty2": "违约责任2",
                "breach_duty3": "违约责任3",
                "breach_duty4": "违约责任4",
                "breach_duty5": "违约责任5",
                "partya_emergency_plan": "应急预案条款（甲方）",
                "partyb_service_commitment": "乙方服务承诺",
                "contract_validity": "合同效力",
                "partyb_record_supervision": "乙方义务-备案监督条款",
                "partyb_violation_supervision": "乙方义务-违规监督条款",
                "partyb_arbitration_notice": "乙方义务-纠纷、仲裁告知条款",
                "partyb_illegal_procurement": "乙方义务-违规采购条款",
                "partyb_compliance_management": "乙方义务-合规管理条款",
                "partyb_quality_control": "乙方义务-质量控制条款",
            },
            soft_use_patterns,
        ),
        ProjectManageRule(
            {
                "project_manage": "项目变更管理",
            }
        ),
        PMRule(),
        SubjectRule(),
        AccessoryRule(
            {
                "accessory_sow": "附件-项目工作说明书",
                "accessory_nda": "附件-项目保密协议",
            }
        ),
    ],
    "硬件采购合同": [
        CaseRule(
            {
                "con_amount_upper": "合同总金额大写",
                "con_amount_lower": "合同总金额小写",
                "con_amount_upper1": "第一笔付款大写",
                "con_amount_lower1": "第一笔付款小写",
                "con_amount_upper2": "第二笔付款大写",
                "con_amount_lower2": "第二笔付款小写",
                "con_amount_upper3": "第三笔付款大写",
                "con_amount_lower3": "第三笔付款小写",
                "con_amount_upper4": "第四笔付款大写",
                "con_amount_lower4": "第四笔付款小写",
                "con_amount_upper5": "第五笔付款大写",
                "con_amount_lower5": "第五笔付款小写",
                "con_amount_upper6": "第六笔付款大写",
                "con_amount_lower6": "第六笔付款小写",
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_lower": "税款小写",
            }
        ),
        ContractAmountRule(
            {
                "con_amount_upper": "合同总金额大写",
                "con_amount_lower": "合同总金额小写",
                "con_amount_upper1": "第一笔付款大写",
                "con_amount_lower1": "第一笔付款小写",
                "con_amount_upper2": "第二笔付款大写",
                "con_amount_lower2": "第二笔付款小写",
                "con_amount_upper3": "第三笔付款大写",
                "con_amount_lower3": "第三笔付款小写",
                "con_amount_upper4": "第四笔付款大写",
                "con_amount_lower4": "第四笔付款小写",
                "con_amount_upper5": "第五笔付款大写",
                "con_amount_lower5": "第五笔付款小写",
                "con_amount_upper6": "第六笔付款大写",
                "con_amount_lower6": "第六笔付款小写",
            }
        ),
        PaymentRadioRule(),
        TaxRule(
            {
                "con_amount_upper": "合同总金额大写",
                "con_amount_lower": "合同总金额小写",
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_lower": "税款小写",
            }
        ),
        TaxRateRule(
            {
                "tax_rate": "增值税适用税率",
                "tax_payer": "乙方纳税人资质",
            }
        ),
        TaxAmountRule(
            {
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_rate": "增值税适用税率",
                "tax_lower": "税款小写",
            }
        ),
        TaxRateFormulaRule(
            {
                "con_amount_lower": "合同总金额小写",
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_rate": "增值税适用税率",
            }
        ),
        FixedTermsRule(
            {
                "vat_term1": "增值税涉税固定条款1",
                "vat_term2": "增值税涉税固定条款2",
                "vat_term3": "增值税涉税固定条款3",
                "vat_term4": "增值税涉税固定条款4",
                "partyb_code_function": "代码及功能规范条款",
                "partyb_info_security": "信息安全条款",
                "partyb_sys_bug": "系统漏洞条款",
                "partyb_issue_waring": "重大事项告知条款",
                "partyb_data_safe": "数据安全条款",
                "partyb_emergency_plan": "应急预案条款",
                "partyb_confidentiality": "保密责任条款",
                "confidentiality": "保密责任",
                "breach_duty1": "违约责任1",
                "breach_duty2": "违约责任2",
                "breach_duty3": "违约责任3",
                "partyb_service_commitment": "乙方服务承诺",
                "contract_effective_change": "合同生效和变更",
                "partyb_record_supervision": "乙方义务-备案监督条款",
                "partyb_violation_supervision": "乙方义务-违规监督条款",
                "partyb_arbitration_notice": "乙方义务-纠纷、仲裁告知条款",
                "partyb_illegal_procurement": "乙方义务-违规采购条款",
                "partyb_compliance_management": "乙方义务-合规管理条款",
                "partyb_quality_control": "乙方义务-质量控制条款",
            },
            hard_pur_patterns,
        ),
        PMRule(),
        AccessoryRule(
            {
                "accessory_nda": "附件-项目保密协议",
            }
        ),
    ],
}


class HTCustomInspector(LegacyInspector):
    def __init__(self, schema_name, rule_groups: tuple[NewRuleClass, list[NewRuleItem]] = None, **kwargs):
        preset_rules = HT_CUSTOM_RULES_BASE_CONFIG.get(schema_name) or []
        custom_rules = []
        for rule_class, items in rule_groups or []:
            for item in items:
                if rule_class.method_type == RuleMethodType.TERM.value:
                    custom_rules.append(
                        CustomTermsRule(rule_class.name, item.name, item.data["column"], item.data["patterns"])
                    )
                elif rule_class.method_type == RuleMethodType.FORMULA.value:
                    custom_rules.append(FormulaRule(rule_class.name, item.name, item.data["formula"]))
        kwargs["rules"] = {
            schema_name: preset_rules + custom_rules,
            "default": [],
        }
        super(HTCustomInspector, self).__init__(**kwargs)

    def gen_rule_result(self, _file, question, mold):
        """Deprecated legacy func"""
        root_schema_name = mold.data["schemas"][0]["name"]
        schema_dict = {schema["name"]: schema for schema in mold.data["schemas"]}
        pdfinsight = None
        pdfinsight_path = _file.pdfinsight_path()
        if pdfinsight_path:
            pdfinsight = PdfinsightReader(localstorage.mount(pdfinsight_path))
        rules = self.rules[mold.name] if mold.name in self.rules else self.rules.get("default", [])
        rule_results = []
        for rule in rules:
            for result in rule.check(question, pdfinsight):
                if not result:
                    continue
                cols, check_result, comment, pos, second_rule, detail = result
                if not cols:
                    continue
                try:
                    rule_name = json.loads(cols[0])[-1].split(":")[0]
                    col_attributes = deepcopy(schema_dict[root_schema_name]["schema"][rule_name])
                    col_attributes.update({"name": rule_name})
                    rule_result = self.build_col(
                        col_attributes, [root_schema_name], index_l=("0", "0"), root_schema_name=root_schema_name
                    )
                except JSONDecodeError:
                    rule_result = {}
                rule_result["data"] = []
                rule_result["value"] = check_result
                rule_result["misc"] = {
                    "rule": rule.name,
                    "schema_cols": cols,
                    "result": check_result,
                    "comment": comment,
                    "comment_pos": pos,
                    "fid": _file.id,
                    "audit_status": AuditStatusEnum.ACCEPT.value
                    if result == ComplianceStatus.NONCOMPLIANCE.value
                    else AuditStatusEnum.UNAUDITED.value,
                    "second_rule": second_rule,
                    "detail": detail,
                }
                rule_results.append(rule_result)
        return rule_results


# 特定 schema 固有的检查项（由代码实现）
HT_CUSTOM_RULES_BASE_CONFIG = {
    "default": [],
    "软件开发外包合同": [
        CaseRule(
            {
                "con_amount_upper": "合同总金额大写",
                "con_amount_lower": "合同总金额小写",
                "con_amount_upper1": "第一笔付款大写",
                "con_amount_lower1": "第一笔付款小写",
                "con_amount_upper2": "第二笔付款大写",
                "con_amount_lower2": "第二笔付款小写",
                "con_amount_upper3": "第三笔付款大写",
                "con_amount_lower3": "第三笔付款小写",
                "con_amount_upper4": "第四笔付款大写",
                "con_amount_lower4": "第四笔付款小写",
                "con_amount_upper5": "第五笔付款大写",
                "con_amount_lower5": "第五笔付款小写",
                "con_amount_upper6": "第六笔付款大写",
                "con_amount_lower6": "第六笔付款小写",
                "notax_amount_upper": "不含税合同总金额大写",
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_upper": "税款大写",
                "tax_lower": "税款小写",
                "ops_amount_upper": "维护费用大写",
                "ops_amount_lower": "维护费用小写",
            }
        ),
        TaxRateRule(
            {
                "tax_rate": "增值税使用税率",
                "tax_payer": "乙方纳税人资质",
            }
        ),
        TaxAmountRule(
            {
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_rate": "增值税使用税率",
                "tax_lower": "税款小写",
            }
        ),
        TaxRateFormulaRule(
            {
                "con_amount_lower": "合同总金额小写",
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_rate": "增值税使用税率",
            }
        ),
        LastChargeRule(
            {
                "last_charge": "最后一笔费用支付",
            }
        ),
        ProjectManageRule(
            {
                "project_manage": "项目变更管理",
            }
        ),
        PMRule(),
        PartyBEmployeeRule(),
    ],
    "软件使用许可合同": [
        CaseRule(
            {
                "con_amount_upper": "合同总金额大写",
                "con_amount_lower": "合同总金额小写",
                "con_amount_upper1": "第一笔付款大写",
                "con_amount_lower1": "第一笔付款小写",
                "con_amount_upper2": "第二笔付款大写",
                "con_amount_lower2": "第二笔付款小写",
                "con_amount_upper3": "第三笔付款大写",
                "con_amount_lower3": "第三笔付款小写",
                "con_amount_upper4": "第四笔付款大写",
                "con_amount_lower4": "第四笔付款小写",
                "con_amount_upper5": "第五笔付款大写",
                "con_amount_lower5": "第五笔付款小写",
                "con_amount_upper6": "第六笔付款大写",
                "con_amount_lower6": "第六笔付款小写",
                "notax_amount_upper": "不含税合同总金额大写",
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_upper": "税款大写",
                "tax_lower": "税款小写",
                "ops_amount_upper": "维护费用大写",
                "ops_amount_lower": "维护费用小写",
            }
        ),
        TaxRateRule(
            {
                "tax_rate": "增值税税率",
                "tax_payer": "乙方纳税人资质",
            }
        ),
        TaxAmountRule(
            {
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_rate": "增值税税率",
                "tax_lower": "税款小写",
            }
        ),
        TaxRateFormulaRule(
            {
                "con_amount_lower": "合同总金额小写",
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_rate": "增值税税率",
            }
        ),
        LastChargeRule(
            {
                "last_charge": "最后一笔付款条件",
            }
        ),
        ProjectManageRule(
            {
                "project_manage": "项目变更管理",
            }
        ),
        PMRule(),
    ],
    "硬件采购合同": [
        CaseRule(
            {
                "con_amount_upper": "合同总金额大写",
                "con_amount_lower": "合同总金额小写",
                "con_amount_upper1": "第一笔付款大写",
                "con_amount_lower1": "第一笔付款小写",
                "con_amount_upper2": "第二笔付款大写",
                "con_amount_lower2": "第二笔付款小写",
                "con_amount_upper3": "第三笔付款大写",
                "con_amount_lower3": "第三笔付款小写",
                "con_amount_upper4": "第四笔付款大写",
                "con_amount_lower4": "第四笔付款小写",
                "con_amount_upper5": "第五笔付款大写",
                "con_amount_lower5": "第五笔付款小写",
                "con_amount_upper6": "第六笔付款大写",
                "con_amount_lower6": "第六笔付款小写",
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_lower": "税款小写",
            }
        ),
        TaxRateRule(
            {
                "tax_rate": "增值税适用税率",
                "tax_payer": "乙方纳税人资质",
            }
        ),
        TaxAmountRule(
            {
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_rate": "增值税适用税率",
                "tax_lower": "税款小写",
            }
        ),
        TaxRateFormulaRule(
            {
                "con_amount_lower": "合同总金额小写",
                "notax_amount_lower": "不含税合同总金额小写",
                "tax_rate": "增值税适用税率",
            }
        ),
        PMRule(),
    ],
}
