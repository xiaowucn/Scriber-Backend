import re

from remarkable.common.constants import ComplianceStatus
from remarkable.common.diff.diff import DiffUtil
from remarkable.rule.common import get_texts_map
from remarkable.rule.ht.ht_business_rules.patterns import simplified_expression
from remarkable.rule.ht.ht_business_rules.result import get_xpath
from remarkable.rule.rule import LegacyRule


class CustomTermsRule(LegacyRule):
    """
    xxxxxxxx需与模板一致
    """

    def __init__(self, class_name: str, item_name: str, col: str, patterns: list[str] | str):
        super().__init__(class_name)
        if isinstance(col, list):
            col = col[-1]
        self.col = col
        if isinstance(patterns, str):
            patterns = patterns.split("\n")
        self.patterns = patterns
        self.rule_name = item_name

    def check(self, question, pdfinsight):
        ret = []
        ele_info = get_texts_map({self.col: self.col}, question)[self.col]
        detail = {}
        result = ComplianceStatus.NONCOMPLIANCE.value
        comment_res = "有误"
        value = self.get_answer_text(ele_info)
        try:
            for pattern in self.patterns:
                # TODO: 合并多个 detail？
                result, comment_res, detail = self.compare_str_pattern(pattern, value, ele_info)
                if result == ComplianceStatus.COMPLIANCE.value:
                    break
            label_info = self.col + comment_res
            detail.update({"label_info": label_info})
        except Exception as ex:
            comment_res = "自定义规则执行异常"
            detail["error"] = str(ex)
        xpath = get_xpath(ele_info, pdfinsight)
        schema_cols = ele_info.get("schema_key", "")
        ret.append(
            (
                [
                    schema_cols,
                ],
                result,
                comment_res,
                {"xpath": xpath},
                self.rule_name,
                detail,
            )
        )
        return ret

    @staticmethod
    def get_answer_text(info):
        if not info["texts"]:
            text = ""
        elif isinstance(info["texts"], str):
            text = info["texts"]
        elif isinstance(info["texts"], list):
            text = "".join(info["texts"])
        else:
            text = ""

        return re.sub("\n", "", text)

    @staticmethod
    def compare_str_pattern(pattern_str, value, ele_info):
        pattern = re.compile(pattern_str, re.X | re.I)
        if re.search(pattern, value):
            result = ComplianceStatus.COMPLIANCE.value
            comment_res = "正确"
            detail = {}
        else:
            result = ComplianceStatus.NONCOMPLIANCE.value
            comment_res = "有误"
            templates = simplified_expression(pattern)
            diff_util = DiffUtil([templates], [str(ele_info["texts"])])
            diff_result = diff_util.compare()
            compare_result = diff_util.parse_diff_result(diff_result)
            if compare_result == 1:
                result = ComplianceStatus.COMPLIANCE
            detail = {
                "diff_result": diff_result,
                "patterns": [templates],
            }
        return result, comment_res, detail
