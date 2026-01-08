import decimal
import json
import logging

from remarkable.common.constants import ComplianceStatus, TaxRate
from remarkable.rule.common import get_texts_map
from remarkable.rule.ht.ht_business_rules.patterns import HT_PATTERNS
from remarkable.rule.ht.ht_business_rules.result import get_xpath, second_rules
from remarkable.rule.rule import LegacyRule


class TaxRateFormulaRule(LegacyRule):
    """
    (含税价-不含税价)/不含税价=税率
    """

    def __init__(self, cols):
        super(TaxRateFormulaRule, self).__init__("增值税税率校验")
        self.cols = cols

    def check(self, question, pdfinsight):
        specific_num = get_texts_map(self.cols, question)
        notax_amount_lower = HT_PATTERNS["lower_sub_pattern"].sub("", str(specific_num["notax_amount_lower"]["texts"]))
        con_amount_lower = HT_PATTERNS["lower_sub_pattern"].sub("", str(specific_num["con_amount_lower"]["texts"]))
        tax_rate = specific_num["tax_rate"]["texts"]
        schema_cols = [
            specific_num["con_amount_lower"].get("schema_key", ""),
            specific_num["notax_amount_lower"].get("schema_key", ""),
            specific_num["tax_rate"].get("schema_key", ""),
        ]
        amount_tax_result, comment = self.compute(tax_rate, notax_amount_lower, con_amount_lower, question)
        xpath = get_xpath(specific_num["tax_rate"], pdfinsight)
        return [
            (
                schema_cols,
                amount_tax_result,
                comment,
                {"xpath": xpath},
                second_rules["tax_rate_formula"],
                {"label_info": comment},
            ),
        ]

    def compute(self, tax_rate, notax_amount_lower, con_amount_lower, question):
        need_compare = True
        tax_rate_values = HT_PATTERNS["tax_rate_pattern"].findall(str(tax_rate).strip())
        tax_comments = []
        if not tax_rate_values:
            need_compare = False
        else:
            if len(tax_rate_values) > 1:
                need_compare = False
        try:
            notax_amount_lower = decimal.Decimal(notax_amount_lower)
            con_amount_lower = decimal.Decimal(con_amount_lower)
            tax_rate_values = [decimal.Decimal(i) for i in tax_rate_values]
        except decimal.InvalidOperation:
            logging.warning(f"convert amount error, question: {question.id}")
            amount_tax_result = ComplianceStatus.NONCOMPLIANCE.value
            tax_comments.append("增值税税率错误")
        else:
            notax_amount = self.format_amount(notax_amount_lower)
            if notax_amount == decimal.Decimal(0):
                amount_tax_result = ComplianceStatus.NONCOMPLIANCE.value
                tax_comments.append("增值税税率错误")
            else:
                tax_rate_values = [self.format_amount(i) for i in tax_rate_values]
                compute_tax_rate = ((self.format_amount(con_amount_lower) - notax_amount) / notax_amount).quantize(
                    decimal.Decimal(".01")
                ) * 100
                amount_tax_res = compute_tax_rate in tax_rate_values
                amount_tax_result = (
                    ComplianceStatus.COMPLIANCE.value if amount_tax_res else ComplianceStatus.NONCOMPLIANCE.value
                )
                comment_equal_str = "=" if amount_tax_res else "≠"
                if need_compare:
                    comment = (
                        f"计算：({con_amount_lower} - {notax_amount_lower})  /  {notax_amount_lower}"
                        f" = {compute_tax_rate}% {comment_equal_str} {tax_rate_values[0]}%"
                    )
                else:
                    comment = f"计算：({con_amount_lower} - {notax_amount_lower})  /  {notax_amount_lower} = {compute_tax_rate}%"
                tax_comments.append(comment)
                # for item in set(tax_rate_values).difference(set([compute_tax_rate])):
                for item in (TaxRate.GENERAL, TaxRate.SPECIAL):
                    tax_comments.extend(self.gen_additional_comment(notax_amount, item))

        return amount_tax_result, json.dumps(tax_comments, ensure_ascii=False)

    @staticmethod
    def gen_additional_comment(notax_amount, item):
        ret = []
        item = decimal.Decimal(item).quantize(decimal.Decimal(".01"))
        include_tax_amount = notax_amount * (1 + item / 100)
        include_tax_amount = decimal.Decimal(include_tax_amount).quantize(decimal.Decimal(".01"))
        ret.append(f"<em>备注：计算{int(item)}%税率含税价=（1+{int(item)}%）*含税价格</em>")
        ret.append(f"<em>{int(item)}%税率含税价=（1+{int(item)}%）*{notax_amount}={include_tax_amount}</em>")
        return ret

    @staticmethod
    def format_amount(amount):
        return amount.quantize(decimal.Decimal(".01"))
