from remarkable.common.constants import ComplianceStatus
from remarkable.rule.common import get_texts_map
from remarkable.rule.ht.ht_business_rules.patterns import HT_PATTERNS
from remarkable.rule.ht.ht_business_rules.result import get_xpath, second_rules
from remarkable.rule.rule import LegacyRule


class TaxRateRule(LegacyRule):
    """
    增值税税率满足纳税人类型要求
    """

    def __init__(self, cols):
        super(TaxRateRule, self).__init__("增值税税率校验")
        self.cols = cols

    def check(self, question, pdfinsight):
        specific_num = get_texts_map(self.cols, question)
        value = specific_num["tax_rate"]["texts"]
        tax_payer = specific_num["tax_payer"]["texts"]
        if not tax_payer:
            result = ComplianceStatus.NONCOMPLIANCE.value
            comment = "未找到纳税人资质"
        else:
            if HT_PATTERNS["tax_rate_pattern"].search(str(value).strip()):
                result = ComplianceStatus.COMPLIANCE.value
                comment_value = ""
                # tax_payer_fromat = '<em>{}</em>{}'.format(tax_payer.replace('纳税人资质', ''), '纳税人资质')
                # comment = '乙方声明具有增值税{}，适用税率为<em>{}</em>'.format(tax_payer_fromat, str(value).strip())
            else:
                result = ComplianceStatus.NONCOMPLIANCE.value
                comment_value = "不"
            comment = f"增值税税率为{value}, {comment_value}满足纳税人类型要求".format(comment_value)
        xpath = get_xpath(specific_num["tax_rate"], pdfinsight)
        schema_cols = specific_num["tax_rate"].get("schema_key", "")
        label_info = "增值税税率错误"
        return [
            (
                [
                    schema_cols,
                ],
                result,
                comment,
                {"xpath": xpath},
                second_rules["tax_rate"],
                {"label_info": label_info},
            ),
        ]
