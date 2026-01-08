# ruff: noqa
from remarkable.common.constants import ComplianceStatus
from remarkable.rule.common import get_texts_map
from remarkable.rule.ht.ht_business_rules.result import comments, get_xpath, second_rules
from remarkable.rule.rule import LegacyRule


class AccessoryRule(LegacyRule):
    """
    （按合同类型，略有不同）
    是否含有附件《项目工作说明书》
    是否含有附件《保密协议》
    """

    def __init__(self, cols):
        super(AccessoryRule, self).__init__("附件检查")
        self.cols = cols

    def check(self, question, pdfinsight):
        specific_num = get_texts_map(self.cols, question)
        ret = list()
        for cols_key, ele_info in specific_num.items():
            comment = "" if ele_info["texts"] else comments["accessory"]
            result = ComplianceStatus.COMPLIANCE.value if ele_info["texts"] else ComplianceStatus.NONCOMPLIANCE.value
            xpath = get_xpath(ele_info, pdfinsight)
            schema_cols = ele_info.get("schema_key", "")
            second_rule = second_rules["accessory"].format(self.cols[cols_key].split("-")[-1])
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
