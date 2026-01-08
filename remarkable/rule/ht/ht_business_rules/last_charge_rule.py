import re

from remarkable.common.constants import ComplianceStatus
from remarkable.rule.common import get_texts_map
from remarkable.rule.ht.ht_business_rules.result import comments, get_xpath, second_rules
from remarkable.rule.rule import LegacyRule


class LastChargeRule(LegacyRule):
    """
    最后一笔付款时间应大于验收后一年
    """

    def __init__(self, cols):
        super(LastChargeRule, self).__init__("最后一笔付款条件校验")
        self.cols = cols

    def check(self, question, pdfinsight):
        pattern = re.compile(r"^在(许可)?软件(验收合格|安装运行)(届满)?[一两二三四五六七八九十]年后.*个工作日内$")
        # ele_info, schema_cols = get_text_by_answer(question.preset_answer, self.cols['last_charge'])
        specific_num = get_texts_map(self.cols, question)
        value = specific_num["last_charge"]["texts"]
        if pattern.search(re.sub(r"\s", "", str(value))):
            result = ComplianceStatus.COMPLIANCE.value
            comment_res = "大"
        else:
            result = ComplianceStatus.NONCOMPLIANCE.value
            comment_res = "小"
        comment = comments["last_charge"].format(comment_res)
        xpath = get_xpath(specific_num["last_charge"], pdfinsight)
        schema_cols = specific_num["last_charge"].get("schema_key", "")
        return [
            (
                [
                    schema_cols,
                ],
                result,
                comment,
                {"xpath": xpath},
                second_rules["last_charge"],
                {},
            ),
        ]
