import re

from remarkable.common.constants import ComplianceStatus
from remarkable.rule.common import get_texts_map
from remarkable.rule.ht.ht_business_rules.common import is_similar_str
from remarkable.rule.ht.ht_business_rules.patterns import simplified_expression
from remarkable.rule.ht.ht_business_rules.result import comments, get_diff_res, get_xpath, second_rules
from remarkable.rule.rule import LegacyRule


class FixedTermsRule(LegacyRule):
    """
    xxxxxxxx需与模板一致
    """

    def __init__(self, cols, patterns):
        super(FixedTermsRule, self).__init__("固定条款对比")
        self.cols = cols
        self.patterns = patterns

    def check(self, question, pdfinsight):
        specific_num = get_texts_map(self.cols, question)
        ret = []
        for cols_key, ele_info in specific_num.items():
            detail = {}
            value = ""
            result = ComplianceStatus.NONCOMPLIANCE.value
            comment_res = "有误"
            if ele_info["texts"] != 0:
                value = re.sub("\n", "", ele_info["texts"])
            pattern = self.patterns[cols_key]
            if isinstance(pattern, list):
                for _pattern in pattern:
                    origin_texts = simplified_expression(_pattern)
                    if not is_similar_str(value, origin_texts):
                        continue
                    result, comment_res, detail = self.compare_str_pattern(_pattern, value, ele_info)
            else:
                result, comment_res, detail = self.compare_str_pattern(pattern, value, ele_info)
            comment = comments["fix_term"].format(comment_res)
            label_info = self.cols[cols_key] + comment_res
            xpath = get_xpath(ele_info, pdfinsight)
            schema_cols = ele_info.get("schema_key", "")
            second_rule = second_rules["fix_term"].format(self.cols[cols_key])
            detail.update({"label_info": label_info})
            ret.append(
                (
                    [
                        schema_cols,
                    ],
                    result,
                    comment,
                    {"xpath": xpath},
                    second_rule,
                    detail,
                )
            )
        return ret

    @staticmethod
    def compare_str_pattern(pattern, value, ele_info):
        if pattern.search(value):
            result = ComplianceStatus.COMPLIANCE.value
            comment_res = "正确"
            detail = {}
        else:
            result = ComplianceStatus.NONCOMPLIANCE.value
            comment_res = "有误"
            detail = {"text_diff": get_diff_res(str(ele_info["texts"]), pattern)}
        return result, comment_res, detail
