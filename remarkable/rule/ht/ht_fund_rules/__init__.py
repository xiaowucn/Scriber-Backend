from remarkable.common.constants import RuleMethodType
from remarkable.rule.ht.ht_business_rules.formula_rule import FormulaRule
from remarkable.rule.ht.ht_fund_rules.chapter_diff import ChapterChecker, ChapterDiff
from remarkable.rule.ht.ht_fund_rules.field_compliance import FieldCompliance
from remarkable.rule.ht.ht_fund_rules.field_consistency import FieldConsistency
from remarkable.rule.inspector import Inspector


class HTFundInspector(Inspector):
    def __init__(self, *args, **kwargs):
        _, rule_groups = args
        custom_rules = []
        for rule_class, items in rule_groups or []:
            for item in items:
                if rule_class.method_type == RuleMethodType.TERM.value:
                    custom_rules.append(ChapterChecker(rule_class.name, custom_config=item.to_dict()))
                elif rule_class.method_type == RuleMethodType.FORMULA.value:
                    custom_rules.append(FormulaRule(rule_class.name, item.name, item.data["formula"]))

        default_chapters = [
            "前言",
            "释义",
            "基金的财产",
            "指令的发送、确认与执行",
            "交易及清算交收安排",
            "越权交易",
            "基金财产的估值和会计核算",
            "信息披露与报告",
            "基金份额的非交过户和冻结、解冻",
            "基金合同的成立、生效",
            "基金合同的效力、变更、解除与终止",
            "违约责任",
            "法律适用和争议的处理",
        ]
        if custom_rules:
            for custom_rule in custom_rules:
                if custom_rule.name != "章节模板对比":
                    continue
                chapter_name = custom_rule.custom_config["data"]["column"]
                if isinstance(chapter_name, list):
                    chapter_name = chapter_name[-1]
                if chapter_name in default_chapters:
                    default_chapters.remove(chapter_name)
        rules_from_code = [
            FieldConsistency("字段一致性比较"),
            FieldCompliance("字段合规性检查"),
            ChapterDiff("章节模板对比", chapters=default_chapters),
        ]
        kwargs["rules"] = rules_from_code + custom_rules
        super(HTFundInspector, self).__init__(*args, **kwargs)
