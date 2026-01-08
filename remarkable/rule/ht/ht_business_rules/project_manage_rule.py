import re

from remarkable.common.constants import ComplianceStatus
from remarkable.rule.common import get_texts_map
from remarkable.rule.ht.ht_business_rules.result import get_xpath, second_rules
from remarkable.rule.rule import LegacyRule


class ProjectManageRule(LegacyRule):
    def __init__(self, cols):
        super(ProjectManageRule, self).__init__("固定条款对比")
        self.cols = cols

    def check(self, question, pdfinsight):
        specific_num = get_texts_map(self.cols, question)
        ret = []
        for cols_key, ele_info in specific_num.items():
            detail = {}
            value = ""
            result = ComplianceStatus.NONCOMPLIANCE.value
            comment_res = ">"
            if ele_info["texts"] != 0:
                value = re.sub("\n", "", ele_info["texts"])
            pattern = re.compile(r"增加工作量比例(<=|=|<|小于|等于|小于等于)\s*?[1-5]\s*?[%％]")
            if pattern.search(value):
                comment_res = "<="
                result = ComplianceStatus.COMPLIANCE.value
            comment = f"工作量比例{comment_res}5%部分纳入本合同标的"
            xpath = get_xpath(ele_info, pdfinsight)
            schema_cols = ele_info.get("schema_key", "")
            second_rule = second_rules["fix_term"].format(self.cols[cols_key].split("-")[-1])
            detail.update({"label_info": f"{self.cols[cols_key]} {comment_res}"})
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
