import decimal
import logging

from remarkable.common.constants import ComplianceStatus
from remarkable.rule.common import get_texts_map
from remarkable.rule.ht.ht_business_rules.patterns import HT_PATTERNS
from remarkable.rule.ht.ht_business_rules.result import second_rules
from remarkable.rule.rule import LegacyRule


class TaxRule(LegacyRule):
    """
    含税合同总金额=不含税合同总金额+税款
    """

    def __init__(self, cols):
        super(TaxRule, self).__init__("税款校验")
        self.cols = cols

    def check(self, question, pdfinsight):
        # 从preset_answer中获取数据
        specific_num = get_texts_map(self.cols, question, sub_lower=True)
        ret = []
        # 含税金额与税款+不含税金额总和校验
        con_amount_lower = HT_PATTERNS["lower_sub_pattern"].sub("", str(specific_num["con_amount_lower"]["texts"]))
        notax_amount_lower = HT_PATTERNS["lower_sub_pattern"].sub("", str(specific_num["notax_amount_lower"]["texts"]))
        tax_lower = HT_PATTERNS["lower_sub_pattern"].sub("", str(specific_num["tax_lower"]["texts"]))
        if specific_num["con_amount_lower"]["texts"] == 0:
            amount_tax_result = ComplianceStatus.NONCOMPLIANCE.value
            amount_tax_res = False
        else:
            try:
                con_amount_lower = decimal.Decimal(con_amount_lower)
                notax_amount_lower = decimal.Decimal(notax_amount_lower)
                tax_lower = decimal.Decimal(tax_lower)
            except decimal.InvalidOperation:
                logging.warning(f"convert amount error, question: {question.id}")
                amount_tax_res = False
                amount_tax_result = ComplianceStatus.NONCOMPLIANCE.value
            else:
                amount_tax_res = con_amount_lower.quantize(tax_lower) == (notax_amount_lower + tax_lower).quantize(
                    tax_lower
                )
                amount_tax_result = (
                    ComplianceStatus.COMPLIANCE.value if amount_tax_res else ComplianceStatus.NONCOMPLIANCE.value
                )
        amount_tax_cols = [
            specific_num["con_amount_lower"].get("schema_key", ""),
            specific_num["notax_amount_lower"].get("schema_key", ""),
            specific_num["tax_lower"].get("schema_key", ""),
        ]
        amount_tax_comment = "{} {} {} + {}".format(
            con_amount_lower, "=" if amount_tax_res else "≠", notax_amount_lower, tax_lower
        )
        if con_amount_lower == "0":
            label_info = ""
        else:
            label_info = amount_tax_comment
        point_sum_xpath = {}
        if specific_num["con_amount_lower"]["texts"]:
            point_sum_ele = pdfinsight.find_element_by_outline(
                specific_num["con_amount_lower"]["line_infos"][0]["page"],
                specific_num["con_amount_lower"]["line_infos"][0]["out_line"],
            )
            point_sum_xpath = point_sum_ele[1].get("docx_meta", {})
        elif specific_num["con_amount_upper"]["texts"]:
            point_sum_ele = pdfinsight.find_element_by_outline(
                specific_num["con_amount_upper"]["line_infos"][0]["page"],
                specific_num["con_amount_upper"]["line_infos"][0]["out_line"],
            )
            point_sum_xpath = point_sum_ele[1].get("docx_meta", {})
        amount_tax_cols = [amount_tax_col for amount_tax_col in amount_tax_cols if amount_tax_col]
        detail = {"label_info": label_info}
        ret.append(
            (
                amount_tax_cols,
                amount_tax_result,
                amount_tax_comment,
                point_sum_xpath,
                second_rules["amount_tax_res"],
                detail,
            )
        )
        return ret
