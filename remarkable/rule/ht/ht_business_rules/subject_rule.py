from remarkable.common.constants import ComplianceStatus
from remarkable.rule.common import get_texts_map
from remarkable.rule.ht.ht_business_rules.result import get_xpath, second_rules
from remarkable.rule.rule import LegacyRule


class SubjectRule(LegacyRule):
    def __init__(
        self,
    ):
        super(SubjectRule, self).__init__("固定条款对比")
        self.cols = {
            "quality_standard": "质量考核标准",
            "continuous_monitor": "持续监控机制",
        }

    def check(self, question, pdfinsight):
        cols = self.cols
        specific_num = get_texts_map(cols, question)
        ret = []
        for cols_key, ele_info in specific_num.items():
            col_text = str(ele_info["texts"]).strip()
            comment = "" if col_text and col_text != "0" else "缺少{}".format(cols[cols_key])
            result = (
                ComplianceStatus.COMPLIANCE.value
                if col_text and col_text != "0"
                else ComplianceStatus.NONCOMPLIANCE.value
            )
            xpath = get_xpath(ele_info, pdfinsight)
            second_rule = second_rules["fix_term"].format(cols[cols_key].split("-")[-1])
            schema_cols = ele_info.get("schema_key", "")
            ret.append(
                (
                    [
                        schema_cols,
                    ],
                    result,
                    comment,
                    {"xpath": xpath},
                    second_rule,
                    {},
                )
            )
        return ret
