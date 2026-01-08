from remarkable.common.constants import ComplianceStatus
from remarkable.rule.common import get_texts_map
from remarkable.rule.ht.ht_business_rules.result import comments, get_xpath, second_rules
from remarkable.rule.rule import LegacyRule


class PMRule(LegacyRule):
    """
    甲方项目负责人校验
    乙方项目负责人校验
    """

    def __init__(
        self,
    ):
        super(PMRule, self).__init__("项目负责人")

    def check(self, question, pdfinsight):
        cols = {
            "partya_pm": "甲方项目经理",
            "partyb_pm": "乙方项目经理",
        }
        specific_num = get_texts_map(cols, question)
        ret = []
        for cols_key, ele_info in specific_num.items():
            pm_name = str(ele_info["texts"]).strip()
            comment = "" if pm_name and pm_name != "0" else comments["pm"]
            result = (
                ComplianceStatus.COMPLIANCE.value
                if pm_name and pm_name != "0"
                else ComplianceStatus.NONCOMPLIANCE.value
            )
            xpath = get_xpath(ele_info, pdfinsight)
            second_rule = second_rules["pm"].format(cols[cols_key][:2])
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
