import logging
import re

# for eval
from remarkable.common.constants import ComplianceStatus
from remarkable.rule.common import get_texts_map
from remarkable.rule.ht.ht_business_rules.result import get_xpath
from remarkable.rule.rule import LegacyRule


class FormulaRule(LegacyRule):
    column_pattern = re.compile(r"{([^}]+)}")
    value_pattern = re.compile(r"\d+(,\d+)*(:?\.\d+)?[%％]?")

    """公式规则
    """

    def __init__(self, class_name, rule_name, formula):
        super(FormulaRule, self).__init__(class_name)
        self.second_name = rule_name
        self.formula = formula

    def check(self, question, pdfinsight):
        ret = []
        columns = self.get_cols_from_formula(self.formula)
        specific_nums = get_texts_map({c: c for c in columns}, question)
        first_num = specific_nums[columns[0]] if columns else {}
        detail = {}
        if first_num.get("texts"):
            try:
                result, comment = self.calculate_with_formula(self.formula, specific_nums)
            except Exception as ex:
                result = False
                comment = "自定义规则执行异常"
                detail["error"] = str(ex)
            detail["label_info"] = comment
            enum_result = ComplianceStatus.COMPLIANCE.value if result else ComplianceStatus.NONCOMPLIANCE.value
            aim_element_xpath = get_xpath(first_num, pdfinsight)
            ret.append(
                (
                    [c.get("schema_key") for c in specific_nums.values()],
                    enum_result,
                    comment,
                    {"xpath": aim_element_xpath},
                    self.second_name,
                    detail,
                )
            )
        return ret

    def get_cols_from_formula(self, formula):
        return self.column_pattern.findall(formula)

    def calculate_with_formula(self, formula, specific_nums):
        formula_obj = Formula(formula)
        res, detail = formula_obj.calculate(
            **{col: self.specific_num_value(info) for col, info in specific_nums.items()}
        )
        return res, detail

    def specific_num_value(self, info):
        if not info["texts"]:
            return "0"
        text = re.sub(r"\s", "", "".join(info["texts"]))
        matchval = self.value_pattern.search(text)
        if matchval:
            return matchval.group(0).replace(",", "")
        return "0"


class Formula:
    CMPOPER = [">=", "<=", "=", ">", "<"]
    RE_NUMBER = re.compile(r"(\d+(:?\.\d+)?)")
    RE_PERCENT_SIGN = re.compile(r"[%％]")

    def __init__(self, formula_string) -> None:
        self.formula_string = formula_string

    def validate(self, formula):
        if not any((c in formula) for c in self.CMPOPER):
            raise Exception("formula need a compare operator")
        # TODO: 校验是只包含数字的公式

    def calculate(self, **kwargs):
        formula = self.formula_string.format(**kwargs)
        self.validate(formula)
        return self.eval(formula), formula

    def eval(self, formula):
        if not re.search(r"[<>=]=", formula):
            formula = formula.replace("=", "==")
        formula = self.RE_NUMBER.sub(r"Decimal('\1')", formula)
        formula = self.RE_PERCENT_SIGN.sub("*Decimal('0.01')", formula)
        result = eval(formula) is True
        logging.debug(f"'{formula}' is {result}")
        return result
