from remarkable.rule.common import get_texts_map
from remarkable.rule.ht.ht_business_rules.result import amount_res
from remarkable.rule.rule import LegacyRule


class CaseRule(LegacyRule):
    """
    合同总额大小写对比结果
    第一笔付款大小写对比结果
    第二笔付款大小写对比结果
    第三笔付款大小写对比结果
    第四笔付款大小写对比结果
    第五笔付款大小写对比结果
    第六笔付款大小写对比结果
    """

    def __init__(self, cols):
        super(CaseRule, self).__init__("大小写校验")
        self.cols = cols

    def check(self, question, pdfinsight):
        # 从preset_answer中获取数据
        specific_num = get_texts_map(self.cols, question, sub_lower=True)

        ret = []
        # 比较合同金额大小写
        ret.append(amount_res("con_amount_upper", "con_amount_lower", specific_num, "con_amount_res", pdfinsight))
        # 比较分笔付款金额大小写
        ret.append(amount_res("con_amount_upper1", "con_amount_lower1", specific_num, "con_amount_res1", pdfinsight))
        ret.append(amount_res("con_amount_upper2", "con_amount_lower2", specific_num, "con_amount_res2", pdfinsight))
        ret.append(amount_res("con_amount_upper3", "con_amount_lower3", specific_num, "con_amount_res3", pdfinsight))
        ret.append(amount_res("con_amount_upper4", "con_amount_lower4", specific_num, "con_amount_res4", pdfinsight))
        ret.append(amount_res("con_amount_upper5", "con_amount_lower5", specific_num, "con_amount_res5", pdfinsight))
        ret.append(amount_res("con_amount_upper6", "con_amount_lower6", specific_num, "con_amount_res6", pdfinsight))
        # 不含税金额大小写
        if "notax_amount_upper" in self.cols:
            ret.append(
                amount_res("notax_amount_upper", "notax_amount_lower", specific_num, "notax_amount_res", pdfinsight)
            )
        # 税金额大小写
        if "tax_upper" in self.cols:
            ret.append(amount_res("tax_upper", "tax_lower", specific_num, "tax_res", pdfinsight))
        # 运维费用
        if "ops_amount_upper" in self.cols:
            ret.append(amount_res("ops_amount_upper", "ops_amount_lower", specific_num, "ops_charge", pdfinsight))
        return ret
