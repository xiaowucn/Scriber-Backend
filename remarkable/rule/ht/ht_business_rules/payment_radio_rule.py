import decimal
import logging
import re

from remarkable.common.constants import ComplianceStatus
from remarkable.rule.common import get_texts_map
from remarkable.rule.ht.ht_business_rules.patterns import HT_PATTERNS
from remarkable.rule.ht.ht_business_rules.result import comments, get_xpath, second_rules
from remarkable.rule.rule import LegacyRule


class PaymentRadioRule(LegacyRule):
    """
    分笔付款比例校验
    """

    def __init__(self):
        super(PaymentRadioRule, self).__init__("分笔付款比例校验")
        self.cols = {
            "con_amount_lower": "合同总金额小写",
            "con_amount_lower1": "第一笔付款小写",
            "con_amount_lower2": "第二笔付款小写",
            "con_amount_lower3": "第三笔付款小写",
            "con_amount_lower4": "第四笔付款小写",
            "con_amount_lower5": "第五笔付款小写",
            "con_amount_lower6": "第六笔付款小写",
            "payment_ratio1": "第一笔付款比例",
            "payment_ratio2": "第二笔付款比例",
            "payment_ratio3": "第三笔付款比例",
            "payment_ratio4": "第四笔付款比例",
            "payment_ratio5": "第五笔付款比例",
            "payment_ratio6": "第六笔付款比例",
        }

    def check(self, question, pdfinsight):
        specific_num = get_texts_map(self.cols, question, sub_lower=True)
        ret = []
        ret.append(self.radio_res("con_amount_lower", "payment_ratio1", "con_amount_lower1", specific_num, pdfinsight))
        ret.append(self.radio_res("con_amount_lower", "payment_ratio2", "con_amount_lower2", specific_num, pdfinsight))
        ret.append(self.radio_res("con_amount_lower", "payment_ratio3", "con_amount_lower3", specific_num, pdfinsight))
        ret.append(self.radio_res("con_amount_lower", "payment_ratio4", "con_amount_lower4", specific_num, pdfinsight))
        ret.append(self.radio_res("con_amount_lower", "payment_ratio5", "con_amount_lower5", specific_num, pdfinsight))
        ret.append(self.radio_res("con_amount_lower", "payment_ratio6", "con_amount_lower6", specific_num, pdfinsight))
        return ret

    @staticmethod
    def radio_res(total_amount, radio, split_paymant, specific_num, pdfinsight):
        total = HT_PATTERNS["lower_sub_pattern"].sub("", str(specific_num[total_amount]["texts"]))
        radio_num = specific_num[radio]["texts"]
        schema_cols = [
            specific_num[total_amount].get("schema_key", ""),
            specific_num[radio].get("schema_key", ""),
            specific_num[split_paymant].get("schema_key", ""),
        ]
        xpath = get_xpath(specific_num[radio], pdfinsight)
        if not radio_num or not total:
            if radio in ["payment_ratio5", "payment_ratio6"]:
                return None
            result = ComplianceStatus.NONCOMPLIANCE.value
            comment = "未提取到数据"
            label_info = "未提取" + comments[radio]
            ret = ([], result, comment, {"xpath": xpath}, second_rules[radio], {"label_info": label_info})
            return ret
        radio_num = re.sub("\\s", "", radio_num)
        split_num = HT_PATTERNS["lower_sub_pattern"].sub("", str(specific_num[split_paymant]["texts"]))
        if total != "0":
            try:
                radio_num = decimal.Decimal(re.sub("\\s", "", radio_num)[:-1])
                split_num = decimal.Decimal(split_num)
                total = decimal.Decimal(total)
            except decimal.InvalidOperation as e:
                logging.error(e)
                result = False
            else:
                result = (split_num / total * 100).quantize(radio_num) == radio_num.quantize(radio_num)
        else:
            result = False
        radio_result = ComplianceStatus.COMPLIANCE.value if result else ComplianceStatus.NONCOMPLIANCE.value
        comment = "{} * {}% {} {}".format(total, radio_num, "=" if result else "≠", split_num)

        ret = (schema_cols, radio_result, comment, {"xpath": xpath}, second_rules[radio], {})
        return ret
