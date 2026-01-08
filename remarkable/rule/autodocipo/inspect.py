# ruff: noqa
import re

from remarkable import config
from remarkable.common.constants import ComplianceStatus
from remarkable.rule.common import get_all_schema, get_texts_map
from remarkable.rule.inspector import LegacyInspector
from remarkable.rule.rule import LegacyRule


class ColCache:
    special_cols = []
    specific_num = {}

    @classmethod
    def get_texts(cls, question):
        schema = get_all_schema(question)
        all_cols = schema["orders"]
        cls.specific_num = get_texts_map(all_cols, question)
        return cls.specific_num


class CompleteInspector(LegacyInspector):
    def __init__(self, **kwargs):
        kwargs["rules"] = {
            "default": [
                ForbidRule(
                    {
                        "risk_countermeasure": "风险对策",
                        "issuer_advantage": "发行人竞争优势",
                    }
                ),
                TermRule(
                    {
                        "report_name": "报告名称",
                        "risk_prompt": "科创版投资风险提示声明",
                        "title_statement": "扉页-声明",
                        "issuer_statement": "发行人声明",
                        "overview_statement": "概览-声明",
                        "last_statement": "尾页声明",
                        "post_statement": "正文后声明",
                        "sponsor_statement": "保荐人（主承销商）声明",
                        "lawyer_statement": "律师声明",
                        "accounting_statement": "会计师事务所声明",
                        "assessment_statement": "资产评估机构声明",
                        "verification_statement": "验资机构声明",
                    }
                ),
                PromptCheckRule(
                    {
                        "agency_info": "发行概况-机构信息",
                    }
                ),
                PromptCheckNullRule0(
                    [
                        "技术风险",
                        "经营风险",
                        "内控风险",
                        "财务风险",
                        "法律风险",
                        "发行失败风险",
                        "尚未盈利或存在累计未弥补亏损的风险",
                        "特别表决权股份或类似公司治理特殊安排的风险",
                        "可能严重影响公司持续经营的其他因素",
                        "发行人报告期内重大资产重组情况",
                        "最近一年发行人新增股东情况",
                        "发行人股东公开发售股份的影响",
                        "提示投资者关注股东公开发售股份事项",
                        "董事签定协议情况",
                        "监事签定协议情况",
                        "高级管理人员签定协议情况",
                        "核心技术人员签定协议情况",
                        "董事所持股份受限情况",
                        "监事所持股份受限情况",
                        "高级管理人员所持股份受限情况",
                        "核心技术人员所持股份受限情况",
                        "最近2年董事变动情况",
                        "最近2年监事变动情况",
                        "最近2年高级管理人员变动情况",
                        "最近2年核心技术人员变动情况",
                        "董监高技与发行人极其业务相关的对外投资情况",
                        "股权激励及相关安排",
                        "向单个客户销售比例超过总额50%的情况",
                        "前五名客户中存在新增客户的情况",
                        "前五名客户中存在严重依赖于少数客户的情况",
                        "发行人关联方客户情况",
                        "向单个客供应商的采购比例超过总额的50%的情况",
                        "前五名供应商中存在新增供应商的情况",
                        "前五名供应商中存在严重依赖于少数供应商的情况",
                        "发行人与他人共享资源要素情况",
                        "合作研发情况",
                        "报告期内核心技术人员的主要变动情况",
                        "报告期内核心技术人员的主要变动情况对发行人的影响",
                        "境外生产经营的总体情况",
                        "境外生产经营业务活动的地域性分析",
                        "境外资产情况",
                        "协议控制架构的具体安排",
                        "关联方的变化情况",
                        "母公司资产负债表",
                        "母公司利润表",
                        "母公司现金流量表",
                        "税收优惠",
                        "是否对税收优惠存在依赖",
                        "未来税收优惠的可持续性",
                        "尚未盈利或存在累计未弥补亏损对公司的影响",
                        "重大资本性支出与资产业务重组",
                        "盈利预测信息",
                        "盈利预测信息提示",
                        "盈利预测信息披露提示",
                        "前瞻性信息",
                        "依据",
                        "基础假设",
                        "募集资金用于研发投入、科技创新、新产品开发生产情况",
                        "特别表决权股份、协议控制架构或类似特殊安排",
                    ]
                ),
                PromptCheckNullRule1(
                    {
                        "profit_info": "盈利预测信息声明",
                        "future_profit_info": "未来实现盈利情况声明",
                    }
                ),
                AttachmentRule(["附件内容"]),
                # IssueSituationRule([
                #     '扉页-发行情况',
                #     '发行概况-本次发行基本情况',
                # ]),
                OtherCompanyRule(["发行人其他参股公司的情况"]),
                DefectDisclosureRule(
                    [
                        "注册会计师是否指出公司内部控制存在缺陷",
                        "发行人针对缺陷披露的改进措施",
                    ]
                ),
                SpecialVoteRule(
                    [
                        "设置特表表决权安排的股东大会决议",
                        "特别表决权安排运行期限",
                        "特别表决权持有人资格",
                        "特别表决权股份拥有的表决权数量与普通股份拥有的表决权数量的比例安排",
                        "持有人所持特别表决权股份能够参与表决的股东大会事项范围",
                        "特别表决权股份锁定安排及转让限制",
                        "差异化表决安排可能导致的相关风险和对公司治理的影响",
                        "相关投资者保护措施",
                    ]
                ),
                OnlyOneDisclosureRule(
                    {
                        "控股股东": [
                            "是否有控股股东",
                            "控股股东的基本情况-法人",
                            "控股股东的基本情况-自然人",
                            "控股股东的基本情况-非法人组织",
                        ],
                        "实际控制人": [
                            "是否有实际控制人",
                            "实际控制人的基本情况-法人",
                            "实际控制人的基本情况-自然人",
                            "实际控制人的基本情况-非法人组织",
                        ],
                        "主要股东的基本情况": [
                            "主要股东的基本情况-法人",
                            "主要股东的基本情况-自然人",
                            "主要股东的基本情况-非法人组织",
                        ],
                        "重大影响的股东": [
                            "对发行人有重大影响的股东情况-法人",
                            "对发行人有重大影响的股东情况-自然人",
                            "对发行人有重大影响的股东情况-非法人组织",
                        ],
                    }
                ),
                StockSituationRule(
                    [
                        [
                            "国有股份数量",
                            "国有股份情况",
                        ],
                        [
                            "外资股份数量",
                            "外资股份情况",
                        ],
                    ]
                ),
                DefaultRule(),
            ],
        }
        super(CompleteInspector, self).__init__(**kwargs)

        # 将缓存的schema字段和字段的具体内容置空
        ColCache.specific_num = {}
        ColCache.special_cols = []


class DefaultRule(LegacyRule):
    def __init__(self):
        super(DefaultRule, self).__init__("完备性检查")

    def check(self, question, pdfinsight):
        schema = get_all_schema(question)
        specific_num = ColCache.specific_num
        if not specific_num:
            specific_num = ColCache.get_texts(question)
        cols = [col for col in schema["orders"] if col not in ColCache.special_cols]
        ret = list()
        for col_cn in cols:
            ele_info = specific_num.get(col_cn, {})
            xpath = {}
            text = str(ele_info["texts"]).strip()
            comment_res = "披露" if text and text != "0" else "未披露"
            comment = col_cn + comment_res
            result = ComplianceStatus.COMPLIANCE.value if text and text != "0" else ComplianceStatus.NONCOMPLIANCE.value
            schema_cols = ele_info.get("schema_key", "")
            detail = {"line_infos": ele_info["line_infos"]}
            ret.append(
                (
                    [
                        schema_cols,
                    ],
                    result,
                    comment,
                    xpath,
                    col_cn,
                    detail,
                )
            )
        return ret


class ForbidRule(LegacyRule):
    """
    是否必须有 0  禁止有
        风险对策
        发行人竞争优势
    """

    def __init__(self, cols):
        super(ForbidRule, self).__init__("完备性检查")
        self.cols = cols

    def check(self, question, pdfinsight):
        ColCache.special_cols.extend(self.cols.values())
        specific_num = ColCache.specific_num
        if not specific_num:
            specific_num = ColCache.get_texts(question)
        ret = list()
        for col_en, col_cn in self.cols.items():
            ele_info = specific_num.get(col_cn, {})
            xpath = {}
            text = str(ele_info["texts"]).strip()
            comment = "未披露" if text and text != "0" else "披露"
            comment = col_cn + comment
            result = ComplianceStatus.NONCOMPLIANCE.value if text and text != "0" else ComplianceStatus.COMPLIANCE.value
            schema_cols = ele_info.get("schema_key", "")
            detail = {"line_infos": ele_info["line_infos"]}
            ret.append(
                (
                    [
                        schema_cols,
                    ],
                    result,
                    comment,
                    xpath,
                    col_cn,
                    detail,
                )
            )
        return ret


class TermRule(LegacyRule):
    """
    是否固定内容 1
        提取出内容之后根据固定内容来判断结果有
        披露 未披露 披露不一致
    """

    def __init__(self, cols):
        super(TermRule, self).__init__("完备性检查")
        self.cols = cols

    def check(self, question, pdfinsight):
        ColCache.special_cols.extend(self.cols.values())
        specific_num = ColCache.specific_num
        if not specific_num:
            specific_num = ColCache.get_texts(question)
        ret = list()
        for col_en, col_cn in self.cols.items():
            ele_info = specific_num.get(col_cn, {})
            pattern = term_reg[col_en]
            xpath = {}
            text = str(ele_info["texts"]).strip()
            if text == "0":
                result = ComplianceStatus.NONCOMPLIANCE.value
                comment_res = "未披露"
            else:
                if config.get_config("web.compare_term_template", True):
                    text = re.sub(r"\s", "", text)
                    if pattern.search(text):
                        result = ComplianceStatus.COMPLIANCE.value
                        comment_res = "披露"
                    else:
                        result = ComplianceStatus.NONCOMPLIANCE.value
                        comment_res = "与模板不一致"
                else:
                    result = ComplianceStatus.COMPLIANCE.value
                    comment_res = "披露"
            comment = col_cn + comment_res
            schema_cols = ele_info.get("schema_key", "")
            detail = {"line_infos": ele_info["line_infos"]}
            ret.append(
                (
                    [
                        schema_cols,
                    ],
                    result,
                    comment,
                    xpath,
                    col_cn,
                    detail,
                )
            )
        return ret


class PromptCheckNullRule0(LegacyRule):
    """
    是否必须有 2 该项内容为空时提示人工审核
        是否固定内容 0
    """

    def __init__(self, cols):
        super(PromptCheckNullRule0, self).__init__("完备性检查")
        self.cols = cols

    def check(self, question, pdfinsight):
        ColCache.special_cols.extend(self.cols)
        specific_num = ColCache.specific_num
        if not specific_num:
            specific_num = ColCache.get_texts(question)
        ret = list()
        for col_cn in self.cols:
            ele_info = specific_num.get(col_cn, {})
            xpath = {}
            text = str(ele_info["texts"]).strip()
            result, comment_res = judge_text(text, res_type="uncertain")
            comment = comment_res.format(col_cn)
            schema_cols = ele_info.get("schema_key", "")
            detail = {"line_infos": ele_info["line_infos"]}
            ret.append(
                (
                    [
                        schema_cols,
                    ],
                    result,
                    comment,
                    xpath,
                    col_cn,
                    detail,
                )
            )
        return ret


class IssueSituationRule(LegacyRule):
    """
    扉页-股东是否公开发售
    扉页-股东拟公开发售股份数量
    扉页-股东公开发售股份所得归属
    "这3个字段是相关连的，如果有股东公开发售，那么后2个字段应该全部都有数据。
    第一个字段“股东是否公开发售”除了是否存在第三种可能--未出现，此时也是需要进行提示的"
    """

    def __init__(self, cols):
        super(IssueSituationRule, self).__init__("完备性检查")
        self.cols = cols

    def check(self, question, pdfinsight):
        ColCache.special_cols.extend(self.cols)
        specific_num = ColCache.specific_num
        if not specific_num:
            specific_num = ColCache.get_texts(question)
        ret = list()
        public_pattern = re.compile(r"股东.*?公开发售|公开发售股.*?数")
        sale_num_pattern = re.compile(r"公开发售股.*?数")
        belong_pattern = re.compile(r"公开发售股份所得归属")
        for col_cn in self.cols:
            ele_info = specific_num.get(col_cn, {})
            xpath = {}
            text = str(ele_info["texts"]).strip()
            ele = pdfinsight.find_element_by_outline(
                ele_info["line_infos"][0]["page"], ele_info["line_infos"][0]["out_line"]
            )
            result = ComplianceStatus.UNCERTAIN.value
            comment_res = "需人工审核"
            if ele[0] == "TABLE":
                cells = ele[1]["cells"]
                for key, cell in cells.items():
                    row, col = split_key(key)
                    if col == "0":
                        if public_pattern.search(cell["text"]):
                            answer_key = row + "_1"
                            answer = cells.get(answer_key, 0)
                            if answer["text"] in ("是", "公开"):
                                if all(pattern.search(text) for pattern in (sale_num_pattern, belong_pattern)):
                                    result = ComplianceStatus.COMPLIANCE.value
                                    comment_res = "披露"
                                else:
                                    result = ComplianceStatus.UNCERTAIN.value
                                    comment_res = "需人工审核"
                            elif not all(pattern.search(text) for pattern in (sale_num_pattern, belong_pattern)):
                                result = ComplianceStatus.COMPLIANCE.value
                                comment_res = "披露"
                            break
            comment = col_cn + comment_res
            schema_cols = ele_info.get("schema_key", "")
            detail = {"line_infos": ele_info["line_infos"]}
            ret.append(
                (
                    [
                        schema_cols,
                    ],
                    result,
                    comment,
                    xpath,
                    col_cn,
                    detail,
                )
            )
        return ret


class OtherCompanyRule(LegacyRule):
    def __init__(self, cols):
        super(OtherCompanyRule, self).__init__("完备性检查")
        self.cols = cols
        self.patterns = {
            "公司名称": re.compile("公司名称"),
            "入股时间": re.compile("时间"),
            "出资金额": re.compile("出资金?额|注册资本"),
            "持股比例": re.compile("持股.*?比例"),
            "控股方": re.compile("控股方"),
            "主营业务情况": re.compile("主营.*?业务"),
        }

    def check(self, question, pdfinsight):
        ColCache.special_cols.extend(self.cols)
        specific_num = ColCache.specific_num
        if not specific_num:
            specific_num = ColCache.get_texts(question)
        ret = list()
        for col_cn in self.cols:
            ele_info = specific_num.get(col_cn, {})
            xpath = {}
            text = str(ele_info["texts"]).strip()
            result = ComplianceStatus.UNCERTAIN.value
            comment_res = "未披露，需人工审核"
            if text and text != 0:
                cnt = 0
                for pattern_name, pattern in self.patterns.items():
                    if pattern.search(re.sub("\\s", "", text)):
                        cnt += 1
                    else:
                        comment_res = pattern_name + "未正确披露"
                        break
                if cnt == len(self.patterns):
                    result = ComplianceStatus.COMPLIANCE.value
                    comment_res = col_cn + "披露"
            schema_cols = ele_info.get("schema_key", "")
            detail = {"line_infos": ele_info["line_infos"]}
            ret.append(
                (
                    [
                        schema_cols,
                    ],
                    result,
                    comment_res,
                    xpath,
                    col_cn,
                    detail,
                )
            )
        return ret


class DefectDisclosureRule(LegacyRule):
    """
    注册会计师是否指出公司内部控制存在缺陷
    发行人针对缺陷披露的改进措施

    如果有“注册会计师是否支出公司内部控制缺陷”，那么后一个字段必须有
    """

    def __init__(self, cols):
        super(DefectDisclosureRule, self).__init__("完备性检查")
        self.cols = cols

    def check(self, question, pdfinsight):
        ColCache.special_cols.extend(self.cols)
        specific_num = ColCache.specific_num
        if not specific_num:
            specific_num = ColCache.get_texts(question)
        ret = list()
        xpath = {}
        defect_col = self.cols[0]
        measure_col = self.cols[1]
        measure_ele_info = specific_num.get(measure_col, {})
        measure_text = str(measure_ele_info["texts"]).strip()
        defect_ele_info = specific_num.get(defect_col, {})
        defect_text = str(defect_ele_info["texts"]).strip()
        if defect_text and defect_text != 0:
            defect_result = ComplianceStatus.COMPLIANCE.value
            defect_comment_res = "{}披露".format(defect_col)
        else:
            defect_result = ComplianceStatus.UNCERTAIN.value
            defect_comment_res = "未找到{}的说明，需人工审核".format(defect_col)
        defect_detail = {"line_infos": defect_ele_info["line_infos"]}
        ret.append(
            (
                [
                    defect_ele_info.get("schema_key", ""),
                ],
                defect_result,
                defect_comment_res,
                xpath,
                defect_col,
                defect_detail,
            )
        )

        if measure_text and measure_text != 0:
            measure_result = ComplianceStatus.COMPLIANCE.value
            measure_comment_res = "{}披露".format(measure_col)
        elif defect_result == ComplianceStatus.COMPLIANCE.value:
            measure_result = ComplianceStatus.NONCOMPLIANCE.value
            measure_comment_res = "{}未披露".format(measure_col)
        else:
            measure_result = ComplianceStatus.UNCERTAIN.value
            measure_comment_res = "未找到{}的说明，需人工审核".format(measure_col)
        measure_detail = {"line_infos": measure_ele_info["line_infos"]}
        ret.append(
            (
                [
                    measure_ele_info.get("schema_key", ""),
                ],
                measure_result,
                measure_comment_res,
                xpath,
                measure_col,
                measure_detail,
            )
        )

        return ret


class SpecialVoteRule(LegacyRule):
    """
    设置特表表决权安排的股东大会决议
    特别表决权安排运行期限
    特别表决权持有人资格
    特别表决权股份拥有的表决权数量与普通股份拥有的表决权数量的比例安排
    持有人所持特别表决权股份能够参与表决的股东大会事项范围
    特别表决权股份锁定安排及转让限制
    差异化表决安排可能导致的相关风险和对公司治理的影响
    相关投资者保护措施

    如果第一个字段标注的是”没有安排特别表决权“或者类似句子，那么后面的字段可以为空

    """

    def __init__(self, cols):
        super(SpecialVoteRule, self).__init__("完备性检查")
        self.cols = cols

    def check(self, question, pdfinsight):
        ColCache.special_cols.extend(self.cols)
        specific_num = ColCache.specific_num
        if not specific_num:
            specific_num = ColCache.get_texts(question)
        xpath = {}
        ret = list()

        default_result = ComplianceStatus.UNCERTAIN.value
        default_comment_res = "未找到{}的说明，需人工审核"
        first_pattern = re.compile(r"没有安排特别表决权")
        first_col = self.cols[0]
        first_ele_info = specific_num.get(first_col, {})
        first_text = str(first_ele_info["texts"]).strip()
        if first_text and first_text != 0:
            first_result = ComplianceStatus.COMPLIANCE.value
            first_comment_res = "{}披露".format(first_col)
            if first_pattern.search(first_text):
                default_result = ComplianceStatus.COMPLIANCE.value
                default_comment_res = "{}可为空"
        else:
            first_result = ComplianceStatus.UNCERTAIN.value
            first_comment_res = "未找到{}的说明，需人工审核".format(first_col)
        ret.append(
            (
                [
                    first_ele_info.get("schema_key", ""),
                ],
                first_result,
                first_comment_res,
                xpath,
                first_col,
                {"line_infos": first_ele_info["line_infos"]},
            )
        )

        for col_cn in self.cols[1:]:
            ele_info = specific_num.get(col_cn, {})
            text = str(ele_info["texts"]).strip()
            if text and text != 0:
                result = ComplianceStatus.COMPLIANCE.value
                comment_res = "{}披露".format(col_cn)
            else:
                result = default_result
                comment_res = default_comment_res.format(col_cn)
            schema_cols = ele_info.get("schema_key", "")
            detail = {"line_infos": ele_info["line_infos"]}
            ret.append(
                (
                    [
                        schema_cols,
                    ],
                    result,
                    comment_res,
                    xpath,
                    col_cn,
                    detail,
                )
            )
        return ret


class PromptCheckNullRule1(LegacyRule):
    """
    是否必须有 2 该项内容为空时提示人工审核
        是否固定内容 1
            盈利预测信息声明
            未来实现盈利情况声明
    """

    def __init__(self, cols):
        super(PromptCheckNullRule1, self).__init__("完备性检查")
        self.cols = cols

    def check(self, question, pdfinsight):
        ColCache.special_cols.extend(self.cols.values())
        specific_num = ColCache.specific_num
        if not specific_num:
            specific_num = ColCache.get_texts(question)
        ret = list()
        for col_en, col_cn in self.cols.items():
            ele_info = specific_num.get(col_cn, {})
            pattern = prompt_check_null_reg[col_en]
            xpath = {}
            text = str(ele_info["texts"]).strip()
            if text == "0":
                result = ComplianceStatus.UNCERTAIN.value
                comment_res = "未找到{}的说明，需人工审核"
            else:
                if pattern.search(text):
                    result = ComplianceStatus.COMPLIANCE.value
                    comment_res = "{}披露"
                else:
                    result = ComplianceStatus.UNCERTAIN.value
                    comment_res = "{}与模板不一致"
            comment = comment_res.format(col_cn)
            schema_cols = ele_info.get("schema_key", "")
            detail = {"line_infos": ele_info["line_infos"]}
            ret.append(
                (
                    [
                        schema_cols,
                    ],
                    result,
                    comment,
                    xpath,
                    col_cn,
                    detail,
                )
            )
        return ret


class PromptCheckRule(LegacyRule):
    """
    是否必须有 3
        提示人工审核
    """

    def __init__(self, cols):
        super(PromptCheckRule, self).__init__("完备性检查")
        self.cols = cols

    def check(self, question, pdfinsight):
        ColCache.special_cols.extend(self.cols.values())
        specific_num = ColCache.specific_num
        if not specific_num:
            specific_num = ColCache.get_texts(question)
        ret = list()
        for col_en, col_cn in self.cols.items():
            ele_info = specific_num.get(col_cn, {})
            xpath = {}
            text = str(ele_info["texts"]).strip()
            result, comment_res = judge_text(text, res_type="uncertain")
            comment = comment_res.format(col_cn)
            schema_cols = ele_info.get("schema_key", "")
            detail = {"line_infos": ele_info["line_infos"]}
            ret.append(
                (
                    [
                        schema_cols,
                    ],
                    result,
                    comment,
                    xpath,
                    col_cn,
                    detail,
                )
            )
        return ret


class AttachmentRule(LegacyRule):
    def __init__(self, cols):
        super(AttachmentRule, self).__init__("完备性检查")
        self.cols = cols
        self.patterns = [
            re.compile("发行保荐书"),
            re.compile("上市保荐书"),
            re.compile("法律意见书"),
            re.compile("财务报告及审计报告"),
            re.compile("公司章程"),
            re.compile("发行人及其他责任主体作出的与发行人本次发行上市相关的承诺事项"),
            re.compile("发行人审计报告基准日至招股说明书签署日之间的相关财务报表及审阅报告"),
            re.compile("盈利预测报告及审核报告"),
            re.compile("内部控制鉴证报告"),
            re.compile("经注册会计师鉴证的非经常性损益明细表"),
            re.compile("中国证监会同意发行人本次公开发行注册的文件"),
        ]

    def check(self, question, pdfinsight):
        ColCache.special_cols.extend(self.cols)
        specific_num = ColCache.specific_num
        if not specific_num:
            specific_num = ColCache.get_texts(question)
        ret = list()
        col_cn = self.cols[0]
        ele_info = specific_num.get(col_cn, {})
        xpath = {}
        text = str(ele_info["texts"]).strip()
        bad_case = []
        cnt = 0
        if text and text != 0:
            for pattern in self.patterns:
                if pattern.search(re.sub("\\s", "", text)):
                    cnt += 1
                else:
                    if pattern.pattern not in (
                        "发行人审计报告基准日至招股说明书签署日之间的相关财务报表及审阅报告",
                        "盈利预测报告及审核报告",
                    ):
                        bad_case.append(pattern.pattern)
        if cnt >= len(self.patterns) - 2:
            result = ComplianceStatus.COMPLIANCE.value
            comment_res = "{}披露".format(col_cn)
        else:
            result = ComplianceStatus.UNCERTAIN.value
            comment_res = ",".join(bad_case) + "均未披露"
        schema_cols = ele_info.get("schema_key", "")
        detail = {"line_infos": ele_info["line_infos"]}
        ret.append(
            (
                [
                    schema_cols,
                ],
                result,
                comment_res,
                xpath,
                col_cn,
                detail,
            )
        )
        return ret


class OnlyOneDisclosureRule(LegacyRule):
    """
    控股股东的基本情况-法人
    控股股东的基本情况-自然人
    控股股东的基本情况-非法人组织
    法人、自然人、非法人组织只要有一组字段有数据就行，可能有多个控股股东，也可能没有
    实际控制人的基本情况-法人
    实际控制人的基本情况-自然人
    实际控制人的基本情况-非法人组织
    法人、自然人、非法人组织只要有一组字段有数据就行，可能有多个实际控制人，也可能没有
    主要股东的基本情况-法人
    主要股东的基本情况-自然人
    主要股东的基本情况-非法人组织
    是否有控股股东
    是否有实际控制人
    对发行人有重大影响的股东情况-法人
    对发行人有重大影响的股东情况-自然人
    对发行人有重大影响的股东情况-非法人组织
    如果”控股股东的基本情况“中有数据，那么是有，如果没有那么会标注一句话比如”没有控股股东“说明没有
    如果”实际控制人的基本情况“中有数据，那么是有，如果没有那么会标注一句话比如”没有实际控制人“说明没有
    无控股股东、实际控制人的，应披露这些信息；此时法人、自然人、非法人组织至少有一组是要有数据的
    """

    def __init__(self, cols):
        super(OnlyOneDisclosureRule, self).__init__("完备性检查")
        self.cols = cols
        self.pattern = re.compile("(无|没有).*?(控股股东|实际控制人)")

    def check(self, question, pdfinsight):
        specific_num = ColCache.specific_num
        if not specific_num:
            specific_num = ColCache.get_texts(question)
        ret = list()
        # 获取是否有 控股股东 实际控制人
        shareholder_exist = self.process_common_col("控股股东", specific_num, ret)
        controller_exist = self.process_common_col("实际控制人", specific_num, ret)
        # 获取 对发行人有重大影响的股东的情况 相关信息
        main_holder_res = {}
        ColCache.special_cols.extend(self.cols["重大影响的股东"])
        for col_cn in self.cols["重大影响的股东"]:
            ele_info = specific_num.get(col_cn, {})
            text = str(ele_info["texts"]).strip()
            main_holder_res[col_cn] = text

        if any((shareholder_exist, controller_exist)):
            if any(
                (value and value != "0" for value in main_holder_res.values())
            ):  # 有控股股东或者实际控制人时不允许有对发行人有重大影响的股东
                result = ComplianceStatus.NONCOMPLIANCE.value
                comment_res = "存在控股股东或者实际控制人，不应该存在对发行人有重大影响的股东"
            else:
                result = ComplianceStatus.COMPLIANCE.value
                comment_res = "存在控股股东或者实际控制人，不存在对发行人有重大影响的股东"
        else:
            if any(
                (value and value != "0" for value in main_holder_res.values())
            ):  # 有法人、自然人、非法人组织任意一个
                result = ComplianceStatus.COMPLIANCE.value
                comment_res = "不存在控股股东或者实际控制人，存在对发行人有重大影响的股东"
            else:
                result = ComplianceStatus.NONCOMPLIANCE.value
                comment_res = "存在控股股东或者实际控制人，不存在对发行人有重大影响的股东相关内容"
        for col_cn in self.cols["主要股东的基本情况"]:
            ele_info = specific_num.get(col_cn, {})
            ret.append(
                (
                    [
                        ele_info.get("schema_key", ""),
                    ],
                    result,
                    comment_res,
                    {},
                    col_cn,
                    {"line_infos": ele_info["line_infos"]},
                )
            )
        # 主要股东的基本情况
        self.process_main_holder(specific_num, ret)
        return ret

    def process_main_holder(self, specific_num, ret):
        ColCache.special_cols.extend(self.cols["主要股东的基本情况"])
        result = {}
        for col_cn in self.cols["主要股东的基本情况"]:
            ele_info = specific_num.get(col_cn, {})
            text = str(ele_info["texts"]).strip()
            result[col_cn] = text
        if any((value and value != "0" for value in result.values())):  # 有法人、自然人、非法人组织任意一个
            result = ComplianceStatus.COMPLIANCE.value
            comment_res = "存在主要股东的基本情况"
        else:
            result = ComplianceStatus.NONCOMPLIANCE.value
            comment_res = "不存在主要股东的基本情况"
        for col_cn in self.cols["主要股东的基本情况"]:
            ele_info = specific_num.get(col_cn, {})
            ret.append(
                (
                    [
                        ele_info.get("schema_key", ""),
                    ],
                    result,
                    comment_res,
                    {},
                    col_cn,
                    {"line_infos": ele_info["line_infos"]},
                )
            )

    def process_common_col(self, subject, specific_num, ret):
        cols = self.cols[subject]
        ColCache.special_cols.extend(cols)
        is_exist_issuer = True
        col_result = {}
        is_exist_col = cols[0]
        is_exist_ele = specific_num.get(is_exist_col, {})
        is_exist_text = str(is_exist_ele["texts"]).strip()
        for col_cn in cols[1:]:
            ele_info = specific_num.get(col_cn, {})
            col_result[col_cn] = str(ele_info["texts"]).strip()
        if any((value and value != "0" for value in col_result.values())):  # 有法人、自然人、非法人组织任意一个
            result = ComplianceStatus.COMPLIANCE.value
            comment_res = "存在{}".format(is_exist_col[3:])
            is_exist_comment = "存在{}".format(is_exist_col[3:])
        elif self.pattern.search(is_exist_text):  # 标注一句话比如"没有控股股东"说明没有
            result = ComplianceStatus.COMPLIANCE.value
            comment_res = "不存在{}".format(is_exist_col[3:])
            is_exist_issuer = False
        else:
            result = ComplianceStatus.NONCOMPLIANCE.value
            comment_res = "{}内容为空，请人工审核是否需要披露".format(is_exist_col[3:])
        for col_cn in cols:
            ele_info = specific_num.get(col_cn, {})
            ret.append(
                (
                    [
                        ele_info.get("schema_key", ""),
                    ],
                    result,
                    comment_res,
                    {},
                    col_cn,
                    {"line_infos": ele_info["line_infos"]},
                )
            )
        return is_exist_issuer


class StockSituationRule(LegacyRule):
    """
    国有股份数量
    国有股份情况
    外资股份数量
    外资股份情况
    如果国有股份数量这标注了”没有国有股份“或类似句子，那么后面的”国有股份情况“字段可以为空；如果国有股份数量这标注了具体数量，那么”国有股份情况“必须有数据
    如果外资股份数量这标注了”没有外资股份“或类似句子，那么后面的”外资股份情况“字段可以为空；如果外资股份数量这标注了具体数量，那么”外资股份情况“必须有数据
    """

    def __init__(self, cols):
        super(StockSituationRule, self).__init__("完备性检查")
        self.cols = cols
        self.pattern = re.compile("(无|没有).*?(国有|外资)股份")

    def check(self, question, pdfinsight):
        specific_num = ColCache.specific_num
        if not specific_num:
            specific_num = ColCache.get_texts(question)
        ret = list()
        for col_cns in self.cols:
            ColCache.special_cols.extend(col_cns)
            is_has_col = col_cns[0]
            num_col = col_cns[1]
            ele_info = specific_num.get(is_has_col, {})
            num_info = specific_num.get(num_col, {})
            text = str(ele_info["texts"]).strip()
            num_text = str(num_info["texts"]).strip()
            if text and text != "0":
                result = ComplianceStatus.COMPLIANCE.value
                comment_res = "{}披露"
                if self.pattern.search(text):
                    num_result = ComplianceStatus.COMPLIANCE.value
                    num_comment_res = "{}披露"
                else:
                    num_result, num_comment_res = judge_text(num_text)

            else:
                result = ComplianceStatus.UNCERTAIN.value
                comment_res = "未找到{}的说明，需人工审核"
                num_result = ComplianceStatus.UNCERTAIN.value
                num_comment_res = "未找到{}的说明，需人工审核"
            ret.append(
                (
                    [
                        ele_info.get("schema_key", ""),
                    ],
                    result,
                    comment_res.format(is_has_col),
                    {},
                    is_has_col,
                    {"line_infos": ele_info["line_infos"]},
                )
            )
            ret.append(
                (
                    [
                        num_info.get("schema_key", ""),
                    ],
                    num_result,
                    num_comment_res.format(num_col),
                    {},
                    num_col,
                    {"line_infos": num_info["line_infos"]},
                )
            )
        return ret


def judge_text(text, res_type="compliance"):
    if text and text != 0:
        result = ComplianceStatus.COMPLIANCE.value
        comment_res = "{}披露"
    else:
        if res_type == "compliance":
            result = ComplianceStatus.NONCOMPLIANCE.value
            comment_res = "{}未披露"
        else:
            result = ComplianceStatus.UNCERTAIN.value
            comment_res = "{}内容为空, 请人工审核是否需要披露"
    return result, comment_res


term_reg = {
    "report_name": re.compile(r".*?首次公开发行股票并在科创板上市(招股说明书)?"),
    "risk_prompt": re.compile(
        r"""
                                本次股票发行后拟在科创板市场上市，该市场具有较高的投资风险。
                                科创板公司具有研发投入大、经营风险高、业绩不稳定、退市风险高等特点，投资者面临较大的市场风险。
                                投资者应充分了解科创板市场的投资风险及本公司所披露的风险因素，审慎作出投资决定。""",
        re.X | re.I,
    ),
    "title_statement": re.compile(
        r"""
                                    (中国证监会、交易所对本次发行所作的任何决定或意见，均不表明其对注册申请文件及所披露信息的真实性、准确性、完整性作出保证，
                                    也不表明其对发行人的盈利能力、投资价值或者对投资者的收益作出实质性判断或者?保证。任何与之相反的声明均属虚假不实陈述。)?
                                    (根据《证券法》的规定，股票依法发行后，发行人经营与收益的变化，由发行人自行负责；投资者自主判断发行人的投资价值，自主作出投资决策，
                                    自行承担股票依法发行后因发行人经营与收益变化或者股票价格变动引致的投资风险。)?""",
        re.X | re.I,
    ),
    "issuer_statement": re.compile(
        r"""
                                    (发行人及全体董事、监事、高级管理人员承诺招股说明书及其他信息披露资料不存在虚假记载、误导性陈述或重大遗漏，并对其真实性、准确性、完整性承担个别
                                    和连带的法律责任。(发行人控股股东、实际控制人|发行人第一大股东)承诺本招股说明书不存在虚假记载、误导性陈述或重大遗漏，并对其真实性、准确性、完整性
                                    承担个别和连带的法律责任。(公司|发行人)负责人和主管会计工作的负责人、会计机构负责人保证招股说明书中财务会计资料真实、完整。发行人及全体董事、监事、
                                    高级管理人员、发行人的(控股|第一大)股东、?(实际控制人)?以及保荐人、承销的证券公司承诺因发行人招股说明书及其他信息披露资料有虚假记载、误导性陈述
                                    或者?重大遗漏，致使投资者在证券发行和交易中遭受损失的，将依法赔偿投资者损失。)?(保荐人及证券服务机构承诺因其为发行人本次公开发行制作、出具的文件
                                    有虚假记载、误导性陈述或者重大遗漏，给投资者造成损失的，将依法赔偿投资者损失。)?""",
        re.X | re.I,
    ),
    "overview_statement": re.compile(
        r"""本概览仅对招股说明书全文[作做]扼要提示。投资者作出投资决策前，应认真阅读招股说明书全文。""", re.X | re.I
    ),
    "last_statement": re.compile(
        r"""
                                    本公司全体董事、监事、高级管理人员承诺本招股说明书不存在虚假记载、误导性陈述或重大遗漏，并对其真实性、准确性、完整性承担个别和连带的法律责任。""",
        re.X | re.I,
    ),
    "post_statement": re.compile(
        r"""承诺本招股说明书不存在虚假记载、误导性陈述或重大遗漏，?并对其真实性、准确性、完整性承担个别和连带的法律责任。?""",
        re.X | re.I,
    ),
    "sponsor_statement": re.compile(
        r"""本公司已对招股说明书进行了核查，确认不存在虚假记载、误导性陈述或重大遗漏，并对其真实性、准确性、完整性承担相应的法律责任。""",
        re.X | re.I,
    ),
    "lawyer_statement": re.compile(
        r"""本所及经办律师已阅读招股说明书，确认招股说明书与本所出具的法律意见书无矛盾之处。
                                        本所及经办律师对发行人在招股说明书中引用的法律意见书的内容无异议，
                                        确认招股说明书不致因上述内容而出现虚假记载、误导性陈述或重大遗漏，并对其真实性、准确性、完整性承担相应的法律责任。
                                    """,
        re.X | re.I,
    ),
    "accounting_statement": re.compile(
        r"""
                        本所及签字注册会计师已阅读招股说明书，确认招股说明书与本所出具的审计报告、?(盈利预测审核报告（如有）)?、?内部控制鉴证报告及经本所鉴证的非经常性损益明细表等无矛盾
                        之处。本所及签字注册会计师对发行人在招股说明书中引用的审计报告、?(盈利预测审核报告（如有）)?、?内部控制鉴证报告及经本所鉴证的非经常性损益明细表等的内容无异议，
                        确认招股说明书不致因上述内容而出现虚假记载、误导性陈述或重大遗漏，并对其真实性、准确性、完整性承担相应的法律责任。|会计师事务所负责人
                    """,
        re.X | re.I,
    ),
    "assessment_statement": re.compile(
        r"""本机构及签字注册资产评估师已阅读招股说明书，确认招股说明书与本机构出具的资产评估报告无矛盾之处。
                                            本机构及签字注册资产评估师对发行人在招股说明书中引用的资产评估报告的内容无异议，
                                            确认招股说明书不致因上述内容而出现虚假记载、误导性陈述或重大遗漏，并对其真实性、准确性、完整性承担相应的法律责任。
                                        """,
        re.X | re.I,
    ),
    "verification_statement": re.compile(
        r"""本机构及签字注册资产评估师已阅读招股说明书，确认招股说明书与本机构出具的资产评估报告无矛盾之处。
                                            本机构及签字注册资产评估师对发行人在招股说明书中引用的资产评估报告的内容无异议，确认招股说明书不致因上述内容而出现虚假记载、
                                            误导性陈述或重大遗漏，并对其真实性、准确性、完整性(和及时性)?承担相应的法律责任。|会计师事务所负责人
                            """,
        re.X | re.I,
    ),
    "attachment": re.compile(
        r""".*?发行保荐书.*?上市保荐书.*?法律意见书.*?财务报告及审计报告.*?公司章程（草案）.*?
                                发行人及其他责任主体作出的与发行人本次发行上市相关的承诺事项.*?发行人审计报告基准日至招股说明书签署日之间的相关财务报表及审阅报告（如有）.*?
                                盈利预测报告及审核报告（如有）.*?内部控制鉴证报告；.*?经注册会计师鉴证的非经常性损益明细表.*?
                                中国证监会同意发行人本次公开发行注册的文件.*?其他与本次发行有关的重要文件。""",
        re.X | re.I,
    ),
}

prompt_check_null_reg = {
    "profit_info": re.compile(
        r"""本公司盈利预测报告是管理层在最佳估计假设的基础上编制的，但所依据的各种假设具有不确定性，投资者进行投资决策时应谨慎使用。""",
        re.X | re.I,
    ),
    "future_profit_info": re.compile(
        r"""本公司前瞻性信息是建立在推测性假设的数据基础上的预测，具有重大不确定性，投资者进行投资决策时应谨慎使用。""",
        re.X | re.I,
    ),
}


def convert_key(key):
    return key.split('"')[1::2]


def split_key(key, sep="_", convert=None):
    res = key.split(sep)
    if convert:
        return [convert(n) for n in res]
    return res
