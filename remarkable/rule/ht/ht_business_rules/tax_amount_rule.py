import decimal
import json
import logging

from remarkable.common.constants import ComplianceStatus, TaxRate
from remarkable.rule.common import get_texts_map
from remarkable.rule.ht.ht_business_rules.patterns import HT_PATTERNS
from remarkable.rule.ht.ht_business_rules.result import get_xpath, second_rules
from remarkable.rule.rule import LegacyRule


class TaxAmountRule(LegacyRule):
    """
    税款校验公式 不含税价*税率=税款
    """

    def __init__(self, cols):
        super(TaxAmountRule, self).__init__("税款校验")
        self.cols = cols

    def check(self, question, pdfinsight):
        # 从preset_answer中获取数据
        specific_num = get_texts_map(self.cols, question, sub_lower=True)
        ret = []
        # 不含税价
        notax_amount_lower = HT_PATTERNS["lower_sub_pattern"].sub("", str(specific_num["notax_amount_lower"]["texts"]))
        tax_lower = HT_PATTERNS["lower_sub_pattern"].sub("", str(specific_num["tax_lower"]["texts"]))
        tax_rate = specific_num["tax_rate"]["texts"]

        amount_tax_result, _, tax_rate_values = self.compute(notax_amount_lower, tax_lower, tax_rate, question)

        amount_tax_cols = [
            specific_num["notax_amount_lower"].get("schema_key", ""),
            specific_num["tax_rate"].get("schema_key", ""),
            specific_num["tax_lower"].get("schema_key", ""),
        ]
        amount_tax_comment = self.gen_comment(tax_rate_values, notax_amount_lower, tax_lower)
        point_sum_xpath = get_xpath(specific_num["tax_lower"], pdfinsight) or get_xpath(
            specific_num["notax_amount_lower"], pdfinsight
        )
        amount_tax_cols = [amount_tax_col for amount_tax_col in amount_tax_cols if amount_tax_col]
        detail = {"label_info": amount_tax_comment}
        ret.append(
            (
                amount_tax_cols,
                amount_tax_result,
                amount_tax_comment,
                {"xpath": point_sum_xpath},
                second_rules["tax_amount"],
                detail,
            )
        )
        return ret

    @staticmethod
    def gen_comment(tax_rate_values, notax_amount_lower, tax_lower):
        ret = []
        for i in tax_rate_values:
            tax_rate_value = i["tax_rate_value"]
            tax_rate_compare = i["tax_rate_compare"]
            compute_tax_rate = i["compute_tax_rate"]
            equal_str = "=" if tax_rate_compare else "≠"
            comment = f"{notax_amount_lower} * {tax_rate_value}% = {compute_tax_rate} {equal_str} {tax_lower}"
            if not tax_rate_compare:
                comment = f"<em>{comment}</em>"
            ret.append(comment)

        return json.dumps(ret, ensure_ascii=False)

    @staticmethod
    def compute(notax_amount_lower, tax_lower, tax_rate, question):
        tax_rate_value_rets = []
        tax_rate_values = HT_PATTERNS["tax_rate_pattern"].findall(str(tax_rate).strip())
        try:
            notax_amount_lower = decimal.Decimal(notax_amount_lower)
            tax_lower = decimal.Decimal(tax_lower)
        except decimal.InvalidOperation:
            logging.warning(
                f"convert amount error, question: {question.id}",
            )
        if not tax_rate_values:
            amount_tax_result = ComplianceStatus.NONCOMPLIANCE.value
            amount_tax_res = False
        else:
            try:
                tax_rate_values = [decimal.Decimal(i) for i in tax_rate_values]
            except decimal.InvalidOperation:
                logging.warning(f"convert amount error, question: {question.id}")
                amount_tax_res = False
                amount_tax_result = ComplianceStatus.NONCOMPLIANCE.value
            else:
                for i in tax_rate_values:
                    compute_tax_rate = notax_amount_lower.quantize(tax_lower) * i.quantize(tax_lower) / 100
                    tax_rate_value_rets.append(
                        {
                            "tax_rate_value": i,
                            "tax_rate_compare": compute_tax_rate.quantize(tax_lower) == tax_lower,
                            "compute_tax_rate": compute_tax_rate.quantize(tax_lower),
                        }
                    )
                amount_tax_res = any(i["tax_rate_compare"] for i in tax_rate_value_rets)
                amount_tax_result = (
                    ComplianceStatus.COMPLIANCE.value if amount_tax_res else ComplianceStatus.NONCOMPLIANCE.value
                )

        if not tax_rate_value_rets and notax_amount_lower and tax_lower:
            for i in (TaxRate.GENERAL, TaxRate.SPECIAL):  # 用默认的税率计算
                compute_tax_rate = notax_amount_lower.quantize(tax_lower) * decimal.Decimal(i).quantize(tax_lower) / 100
                tax_rate_value_rets.append(
                    {
                        "tax_rate_value": tax_rate,
                        "tax_rate_compare": compute_tax_rate.quantize(decimal.Decimal(".01")) == tax_lower,
                        "compute_tax_rate": compute_tax_rate.quantize(decimal.Decimal(".01")),
                    }
                )

        return amount_tax_result, amount_tax_res, tax_rate_value_rets
