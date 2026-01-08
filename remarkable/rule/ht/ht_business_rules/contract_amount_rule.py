import decimal
import re

from remarkable.common.constants import ComplianceStatus
from remarkable.rule.common import get_texts_map
from remarkable.rule.ht.ht_business_rules.patterns import HT_PATTERNS
from remarkable.rule.ht.ht_business_rules.result import get_xpath
from remarkable.rule.rule import LegacyRule


class ContractAmountRule(LegacyRule):
    """
    合同总额 = 第一次付款 + 第二次付款 + 第三次付款 + 第四笔付款 + 第五笔付款 + 第六笔付款
    """

    def __init__(self, cols):
        super(ContractAmountRule, self).__init__("合同总金额校验")
        self.cols = cols

    def check(self, question, pdfinsight):
        # 从preset_answer中获取数据
        specific_num = get_texts_map(self.cols, question, sub_lower=True)
        ret = []
        con_amount_lower = HT_PATTERNS["lower_sub_pattern"].sub("", str(specific_num["con_amount_lower"]["texts"]))
        # 比较合同金额与分笔付款金额总和
        point_sum = self.sum_of_points_payment(specific_num)
        if point_sum == 0:
            point_sum_res = False
            point_sum_result = ComplianceStatus.NONCOMPLIANCE.value
        else:
            point_sum_res = decimal.Decimal(con_amount_lower) == point_sum
            point_sum_result = (
                ComplianceStatus.COMPLIANCE.value if point_sum_res else ComplianceStatus.NONCOMPLIANCE.value
            )
        point_sum_cols = [
            specific_num["con_amount_lower"].get("schema_key", ""),
            specific_num["con_amount_lower1"].get("schema_key", ""),
            specific_num["con_amount_lower2"].get("schema_key", ""),
            specific_num["con_amount_lower3"].get("schema_key", ""),
            specific_num["con_amount_lower4"].get("schema_key", ""),
            specific_num["con_amount_lower5"].get("schema_key", ""),
            specific_num["con_amount_lower6"].get("schema_key", ""),
        ]
        # point_sum_comment = comments['point_sum_res'].format('' if point_sum_res else '不')
        point_sum_xpath = None
        if specific_num["con_amount_lower"]["texts"]:
            point_sum_xpath = get_xpath(specific_num["con_amount_lower"], pdfinsight)
        elif specific_num["con_amount_upper"]["texts"]:
            point_sum_xpath = get_xpath(specific_num["con_amount_upper"], pdfinsight)
        point_sum_cols = [point_sum_col for point_sum_col in point_sum_cols if point_sum_col]
        point_sum_comment, second_rule = self.get_second_rules(specific_num, point_sum_res, point_sum)
        label_info = "合同总金额" + re.sub(r"<em>|</em>", "", point_sum_comment) if con_amount_lower != "0" else ""
        ret.append(
            (
                point_sum_cols,
                point_sum_result,
                point_sum_comment,
                {"xpath": point_sum_xpath},
                second_rule,
                {"label_info": label_info},
            )
        )
        return ret

    @staticmethod
    def sum_of_points_payment(specific_num):
        """
        计算分笔付款金额之和
        """
        point_payment = {k: v for k, v in specific_num.items() if re.compile(r"con_amount_lower\d").search(k)}
        decimal.getcontext().rounding = "ROUND_HALF_UP"
        numbers = [
            float(HT_PATTERNS["lower_sub_pattern"].sub("", v["texts"]))
            for k, v in point_payment.items()
            if v["texts"] and HT_PATTERNS["lower_sub_pattern"].sub("", v["texts"])
        ]
        result = decimal.Decimal(sum(numbers))
        sums = decimal.Decimal(str(result)).quantize(decimal.Decimal("0.00"))
        return sums

    @staticmethod
    def get_second_rules(specific_num, point_sum_res, point_sum):
        """
        second_rule = 合同总额 = 第一次付款 + 第二次付款 + 第三次付款 + 第四笔付款 + 第五笔付款 + 第六笔付款
        point_sum_comment : 100000 ≠ 30000+20000+20000+20000
        :return:
        """
        num_map = {
            "2": "二",
            "3": "三",
            "4": "四",
            "5": "五",
            "6": "六",
        }
        second_rule = "合同总额 = 第一次付款"
        second_rule_add = " + 第{}次付款"
        con_amount_lower = HT_PATTERNS["lower_sub_pattern"].sub("", str(specific_num["con_amount_lower"]["texts"]))
        con_amount_lower1 = HT_PATTERNS["lower_sub_pattern"].sub("", str(specific_num["con_amount_lower1"]["texts"]))
        point_sum_comment = "{} {} {}".format(con_amount_lower, "=" if point_sum_res else "≠", con_amount_lower1)
        comment_add = " + {}"

        for col, info in specific_num.items():
            if re.compile(r"con_amount_lower[23456]").search(col):
                if info["texts"] != 0 or col not in ["con_amount_lower5", "con_amount_lower6"]:
                    num = col[-1]
                    second_rule += second_rule_add.format(num_map[num])
                    point_sum_comment += comment_add.format(
                        HT_PATTERNS["lower_sub_pattern"].sub("", str(info["texts"]))
                    )
        if not point_sum_res:
            point_sum_comment += "<em> = {}</em>".format(point_sum)
        return point_sum_comment, second_rule
