import re
from abc import ABC
from collections import defaultdict
from functools import cached_property

from remarkable.checker.cgs_checker.base_schema_checker import BaseSchemaChecker, replace_parenthesis
from remarkable.checker.checkers.conditions_checker import BaseConditionsChecker
from remarkable.common.constants import RuleType
from remarkable.common.convert_number_util import NumberUtil
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.plugins.cgs.common.enum_utils import TemplateCheckTypeEnum
from remarkable.plugins.cgs.common.fund_classification import InvestmentScopeEnum
from remarkable.plugins.cgs.common.para_similarity import ParagraphSimilarity
from remarkable.plugins.cgs.common.patterns_util import (
    P_CATALOG_TITLE,
    P_LANDLINE_NUMBER,
    P_PUBLIC_SIMILARITY_PATTERNS,
    R_CONJUNCTION,
)
from remarkable.plugins.cgs.common.template_condition import TemplateConditional, TemplateName
from remarkable.plugins.cgs.common.utils import get_outlines
from remarkable.plugins.cgs.schemas.reasons import (
    MatchFailedItem,
    ResultItem,
)
from remarkable.plugins.ext_api.common import is_table_elt


class PublicCustodySchemaChecker(BaseSchemaChecker, ABC):
    SCHEMA_NAME = "公募-托管协议"
    NAME = ""
    RELATED_NAME = ""
    LABEL = ""
    SCHEMA_FIELDS = []
    SYNONYM_PATTERNS = P_PUBLIC_SIMILARITY_PATTERNS

    @classmethod
    def get_valid_subclasses(cls, schema_names: set[str]):
        if cls.SCHEMA_NAME in schema_names:
            return cls.__subclasses__()
        return []

    @cached_property
    def result(self):
        return ResultItem(
            name=self.NAME,
            related_name=self.RELATED_NAME,
            is_compliance=False,
            reasons=[],
            suggestion=None,
            schema_id=self.schema_id,
            fid=self.file.id,
            schema_results=self.manager.build_schema_results(self.SCHEMA_FIELDS),
            label=self.LABEL,
            origin_contents=self.get_origin_contents(),
        )


class CustodyFundScopeInvestmentChecker(PublicCustodySchemaChecker):
    RELATED_NAME = "基金资产净值计算和会计核算"
    SCHEMA_FIELDS = ["托管人对管理人的监督", "估值对象"]
    LABEL = "schema_921"
    NAME = "估值对象"
    P_LINK_SENTENCE = PatternCollection(r"、|与|以?及|和|或")
    PATTERNS = [
        {"value": "银行存款本息", "pattern": PatternCollection(r"银行存款本息")},
        {"value": "应收款项", "pattern": PatternCollection(r"应收款项")},
        {"value": "其它投资等资产", "pattern": PatternCollection(r"其它投资等资产")},
        {"value": "负债", "pattern": PatternCollection(r"负债")},
    ]

    LINKED_PATTERN = [
        {"value": "目标ETF基金份额", "pattern": PatternCollection(r"目标ETF基金份额")},
    ]

    def check_para(self, template, content, conditions, public_conditions):
        format_dict = {}
        # 根据“、与和及”等词拆分当前段落，
        content_list = []
        next_pos = 0
        for link_res in self.P_LINK_SENTENCE.finditer(content):
            content_list.append((content[next_pos : link_res.span()[0]], link_res.group()))
            next_pos = link_res.span()[-1]
        if len(content) != next_pos:
            content_list.append((content[next_pos:], ""))
        # 按联结词划分词组，按顺序匹配正则
        format_vals = []
        missing_vals = []
        for check_pattern in conditions:
            for idx, (value, link_str) in enumerate(content_list):
                if check_pattern["pattern"].nexts(value):
                    format_vals.append((idx, [check_pattern["value"], link_str]))
                    break
            else:
                if check_pattern in public_conditions:
                    missing_vals.append(check_pattern["value"])

        sorted_vals = []
        for _, vals in sorted(format_vals, key=lambda x: x[0]):
            sorted_vals.extend(vals)
        # 默认不需要最后一位联结词
        format_val = "".join(sorted_vals[:-1])
        if missing_vals:
            format_val = f"{format_val}、{'、'.join(missing_vals)}"
        format_dict["RP"] = format_val
        return format_vals, template.format(**format_dict)

    def check(self):
        scope_investment = self.manager.get(self.SCHEMA_FIELDS[0])
        if not scope_investment.value:
            self.result.reasons.append(MatchFailedItem(reason_text="托管人对管理人的监督内容不可为空"))
            self.result.suggestion = "请添加托管人对管理人的监督内容"
            return self.result
        object_valuation = self.manager.get(self.SCHEMA_FIELDS[1])
        if not object_valuation.value:
            self.result.reasons.append(MatchFailedItem(reason_text="估值对象内容不可为空"))
            self.result.suggestion = "请添加估值对象"
            return self.result
        scope_values = []
        clean_text = clean_txt(scope_investment.value)
        for scope in InvestmentScopeEnum.members().values():
            p_scope: PatternCollection = scope.values[-1]
            if p_scope.nexts(clean_text):
                scope_values.append(scope.value)
        clean_text = clean_txt(object_valuation.value)
        patterns = [
            {"value": scope.value, "pattern": scope.values[-1]} for scope in InvestmentScopeEnum.members().values()
        ]
        patterns.extend(self.PATTERNS)
        public_patterns = self.PATTERNS
        if self.manager.verify_condition([TemplateConditional.SPECIAL_TYPE_LINKED_FUND]):
            format_template = "基金所拥有的{RP}。"
            patterns.extend(self.LINKED_PATTERN)
            public_patterns.extend(self.LINKED_PATTERN)
            format_vals, format_template = self.check_para(format_template, clean_text, patterns, public_patterns)
        else:
            format_template = "基金所拥有的{RP}。"
            format_vals, format_template = self.check_para(format_template, clean_text, patterns, public_patterns)

        object_values = []
        for _, val in format_vals:
            is_exist = False
            for pattern in public_patterns:
                if pattern["value"] == val[0]:
                    is_exist = True
                    break
            if not is_exist:
                object_values.append(val[0])
        outlines = object_valuation.outlines
        if not set(object_values).issubset(set(scope_values)):
            self.result.reasons.append(
                MatchFailedItem(reason_text="估值对象出现了托管人对管理人的监督中未出现的投资品种", outlines=outlines)
            )
            self.result.suggestion = (
                "估值对象的投资品种，要与托管人对管理人的监督包含的品种需匹配，请检查估值对象中投资品种"
            )
            return self.result

        self.paragraph_similarity(
            result=self.result,
            paragraphs_left_list=[[format_template]],
            paragraphs_right=[object_valuation.value],
            outlines=outlines,
            origin_content=format_template,
            name=TemplateName.EDITING_NAME,
            content_title=TemplateName.EDITING_TITLE,
        )
        return self.result


class CustodyFundTransferFinanceChecker(PublicCustodySchemaChecker, ABC):
    RELATED_NAME = "基金托管人对基金管理人的业务监督和核查"
    SCHEMA_FIELDS = ["托管人对管理人的监督"]
    LABEL = "template_936"
    NAME = "投资范围-投资转融通的产品类型限制"
    FROM = "公开募集证券投资基金参与转融通证券出借业务指引（试行）（证监会公告〔2019〕15号 2019年6月14日）"
    ORIGIN = [
        "第五条 以下基金产品可依据法律法规的规定和基金合同、招募说明书的约定，参与出借业务：",
        "（一） 处于封闭期的股票型基金和偏股混合型基金；",
        "（二）开放式股票指数基金及相关联接基金；",
        "（三）战略配售基金；",
        "（四）中国证监会认可的其他基金产品。",
        "第（一）项所称偏股混合型基金，是指基金合同明确约定股票投资比例60%以上的混合型基金。",
        "第（三）项所称战略配售基金，是指主要投资策略包括投资战略配售股票，且以封闭方式运作的证券投资基金。",
    ]

    # 股票型、混合型、开放式股票型指数基金、ETF、ETF联接基金
    P_VALID_FUND_TYPES = [
        [
            TemplateConditional.FUND_TYPE_STOCK,
        ],
        [
            TemplateConditional.FUND_MIXTURE,
        ],
        [TemplateConditional.SIDE_TYPE_OPEN, TemplateConditional.FUND_TYPE_STOCK_INDEX],
        [
            TemplateConditional.SPECIAL_TYPE_ETF,
        ],
        [
            TemplateConditional.SPECIAL_TYPE_LINKED_FUND,
        ],
    ]

    def check(self):
        scope_investment = self.manager.get(self.SCHEMA_FIELDS[0])
        if not scope_investment.value:
            self.result.reasons.append(MatchFailedItem(reason_text="托管人对管理人的监督内容不可为空"))
            self.result.suggestion = "请添加托管人对管理人的监督内容"
            return self.result

        include_fund_type = False
        for fund_type in self.P_VALID_FUND_TYPES:
            if self.manager.verify_condition(fund_type):
                include_fund_type = True
                break
        if "转融通证券出借" in scope_investment.value and not include_fund_type:
            self.result.reasons.append(MatchFailedItem(reason_text="当前基金类型不可投资转融通证券出借"))
            self.result.suggestion = "请检查投资范围"
            return self.result
        self.result.is_compliance = True
        return self.result


class CustodyFundNameChecker(PublicCustodySchemaChecker):
    """
    基金名称检查
    """

    RULE_TYPE = RuleType.TEMPLATE.value
    RELATED_NAME = "基金名称"
    SCHEMA_FIELDS = ["基金名称"]
    LABEL = "schema_930"
    NAME = "全文基金名称保持一致"
    SUGGESTIONS_ON_REVISION = ["请添加基金名称", "全文基金名称需保持一致"]
    REASON = ["基金名称不可为空", "基金名称不是"]
    P_SIGNATURE_PAGE = PatternCollection(
        [
            r"签[署字](盖章)?[页]",
            rf"(?:(?:当事人盖章|法定代表人|授权代表)[{R_CONJUNCTION}]?){{3}}(?:(?:签字|签订地|签订日)[{R_CONJUNCTION}]?){{3}}",
        ]
    )
    P_PARAGRAPHS_AFTER_CATALOG = PatternCollection(
        [
            r"拟募集发行.*以下简称",
            r"鉴于.*拟担任.*(管理|托管)人",
            r"明确.*权利义务关系",
            r"术语.*基金合同",
        ]
    )

    def check_paragraphs_after_catalog(self, fund_name_mode_value):
        chapters, _ = self.reader.find_paragraphs_by_chapters([re.compile(r"目录")], is_continued_chapter=False)
        if not chapters:
            return
        paragraphs = None
        page_start = chapters[0]["dest"]["page_index"]
        for page in self.reader.data["pages"].keys():
            page_index = int(page)
            if page_index > page_start:
                elements = self.reader.find_elements_by_page(page_index)
                for element in elements:
                    if is_table_elt(element):
                        continue
                    if P_CATALOG_TITLE.nexts(clean_txt(element["text"])):
                        break
                    paragraphs = elements
                    break
                if paragraphs:
                    break
        for paragraph in paragraphs:
            if is_table_elt(paragraph):
                continue
            paragraph_text = replace_parenthesis(paragraph["text"])
            if self.P_PARAGRAPHS_AFTER_CATALOG.nexts(paragraph_text) and fund_name_mode_value not in paragraph_text:
                self.result.is_compliance = False
                self.result.reasons.append(
                    MatchFailedItem(
                        reason_text=f"{self.REASON[1]}“{fund_name_mode_value}”",
                        page=paragraph["page"],
                        matched=False,
                        outlines=get_outlines([paragraph]),
                    )
                )
                self.result.suggestion = self.SUGGESTIONS_ON_REVISION[1]

    def check(self):
        fund_name_mode = self.manager.get(self.SCHEMA_FIELDS[0])
        if not fund_name_mode.value:
            self.result.reasons.append(MatchFailedItem(reason_text=self.REASON[0]))
            self.result.suggestion = self.SUGGESTIONS_ON_REVISION[0]
            return self.result
        fund_name_mode_value = replace_parenthesis(fund_name_mode.value)
        self.result.is_compliance = True
        unmatch_paragraphs = [
            self.check_signature_page(fund_name_mode_value, self.P_SIGNATURE_PAGE),  # 签署页
            self.check_cover(fund_name_mode_value),  # 封面
        ]

        for item in unmatch_paragraphs:
            if not item:
                continue
            self.result.reasons.append(
                MatchFailedItem(
                    reason_text=f"{self.REASON[1]}“{fund_name_mode_value}”",
                    page=item[0]["page"],
                    matched=False,
                    outlines=get_outlines(item),
                )
            )
            self.result.suggestion = self.SUGGESTIONS_ON_REVISION[1]
            self.result.is_compliance = False
        # 目录后的段落
        self.check_paragraphs_after_catalog(fund_name_mode_value)
        return self.result


class CustodyFundManagerChecker(CustodyFundNameChecker):
    RELATED_NAME = "管理人名称"
    SCHEMA_FIELDS = ["基金管理人-名称"]
    LABEL = "schema_931"
    NAME = "全文管理人名称保持一致"
    SUGGESTIONS_ON_REVISION = ["请添加管理人名称", "全文管理人名称需保持一致"]
    REASON = ["管理人名称不可为空", "管理人名称不是"]
    P_PARAGRAPHS_AFTER_CATALOG = PatternCollection(
        [
            r"鉴于.*[按|依]照中国法律",
            r"鉴于.*担任.*管理",
        ]
    )
    P_SIGNATURE_PAGE = PatternCollection(r"基金管理人[:：]")


class CustodyFundTrusteeChecker(CustodyFundManagerChecker):
    RELATED_NAME = "托管人名称"
    SCHEMA_FIELDS = ["基金托管人-名称"]
    LABEL = "schema_932"
    NAME = "全文托管人名称保持一致"
    SUGGESTIONS_ON_REVISION = ["请添加托管人名称", "全文托管人名称需保持一致"]
    REASON = ["托管人名称不可为空", "托管人名称不是"]
    P_PARAGRAPHS_AFTER_CATALOG = PatternCollection(r"鉴于.*担任.*托管")
    P_SIGNATURE_PAGE = PatternCollection(r"基金托管人[:：]")


class CustodyFundCataloguePageNumberChecker(PublicCustodySchemaChecker):
    RELATED_NAME = "目录"
    SCHEMA_FIELDS = ["目录"]
    LABEL = "schema_933"
    NAME = "验证目录准确性"
    CONTRACT_CONTENT = [
        "《证券投资基金信息披露内容与格式准则第7号<托管协议的内容与格式>》（证监基金字[2005]203号）",
        "第八条 基金托管协议目录应当自首页开始排印。目录应当列明各个具体标题及相应的页码。",
    ]
    P_PAGE_NUMBER = re.compile(rf"[{NumberUtil.R_CN_NUMBER}]+")

    def check(self):
        _, paragraphs = self.reader.find_paragraphs_by_chapters([re.compile(r"目录")])
        if not paragraphs:
            self.result.reasons.append(MatchFailedItem(reason_text="未找到目录"))
            self.result.suggestion = "请添加目录"
            return self.result

        catalog_paragraph_dict = {}
        for paragraph in paragraphs:
            paragraph_text = clean_txt(paragraph["text"])
            if P_LANDLINE_NUMBER.nexts(paragraph_text):
                continue
            if match := P_CATALOG_TITLE.nexts(paragraph_text):
                if no := match.group("no"):
                    catalog_paragraph_dict[clean_txt(match.group("content"))] = {
                        "no": int(no),
                        "paragraph": paragraph,
                    }
        page_syllabus_dict = defaultdict(list)
        title_syllabus_dict = {}
        title_page_mapping = {}
        for syllabus in self.reader.syllabuses:
            if self.reader.page_footers:
                for page_footer in self.reader.page_footers:
                    if page_footer["page"] == syllabus["dest"]["page_index"]:
                        if page_no := NumberUtil.cn_number_2_digit(
                            self.P_PAGE_NUMBER.search(page_footer["text"]).group()
                        ):
                            page_syllabus_dict[page_no].append(syllabus)
                            title_syllabus_dict[clean_txt(syllabus["title"])] = syllabus
                            title_page_mapping[clean_txt(syllabus["title"])] = int(page_footer["text"])
            else:
                page_syllabus_dict[syllabus["dest"]["page_index"]].append(syllabus)
                title_syllabus_dict[clean_txt(syllabus["title"])] = syllabus
                title_page_mapping[clean_txt(syllabus["title"])] = int(syllabus["dest"]["page_index"])

        self.result.is_compliance = True
        for content, catalog in catalog_paragraph_dict.items():
            syllabus = title_syllabus_dict.get(content)
            if syllabus:
                page_index = title_page_mapping[content]
                if catalog["no"] != page_index:
                    outlines = {
                        str(page_index): [syllabus["dest"]["box"]],
                        str(catalog["paragraph"]["page"]): [catalog["paragraph"]["outline"]],
                    }
                    self.result.reasons.append(
                        MatchFailedItem(
                            reason_text="目录与章节页码不匹配",
                            page=min(outlines, key=int, default=0),
                            outlines=outlines,
                        )
                    )
                    self.result.is_compliance = False
            else:
                page_index = catalog["no"]
                syllabuses = page_syllabus_dict.get(page_index)
                if syllabuses:
                    similarity_dict = {}
                    for item in syllabuses:
                        similarity = ParagraphSimilarity(
                            [content], [item["title"]], similarity_patterns=self.SYNONYM_PATTERNS
                        )
                        similarity_dict[item["title"]] = {
                            "outlines": {
                                str(page_index): [item["dest"]["box"]],
                                str(catalog["paragraph"]["page"]): [catalog["paragraph"]["outline"]],
                            },
                            "similarity": similarity,
                        }
                    similarity_list = sorted(
                        similarity_dict.items(), key=lambda x: x[1]["similarity"].max_ratio, reverse=True
                    )
                    outlines = similarity_list[0][1]["outlines"]
                    if similarity_list:
                        self.result.reasons.append(
                            MatchFailedItem(
                                reason_text="章节标题错误",
                                page=min(outlines, key=int, default=0),
                                outlines=outlines,
                            )
                        )
                        self.result.is_compliance = False
                else:
                    outlines = get_outlines([catalog["paragraph"]])
                    self.result.reasons.append(
                        MatchFailedItem(
                            reason_text="未找到匹配的章节标题",
                            page=min(outlines, key=int, default=0),
                            outlines=outlines,
                        )
                    )
        if not self.result.is_compliance:
            self.result.suggestion = "检查章节目录"

        return self.result


# https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2454
class CustodyContractPurposeChecker(PublicCustodySchemaChecker):
    LABEL = "schema_934"
    RELATED_NAME = ""
    NAME = "“鉴于”-制定托管协议的目的"
    FROM = "公开募集开放式证券投资基金流动性风险管理规定（证监会公告[2017]12号 2017年8月31日）"
    ORIGIN = "第八条 基金托管协议目录应当自首页开始排印。目录应当列明各个具体标题及相应的页码。"

    TEMPLATES = [
        {
            "name": TemplateName.EDITING_NAME,
            "content_title": TemplateName.EDITING_TITLE,
            "rule_fields": ["基金名称", "基金管理人-名称"],
            "items": [
                {
                    "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                    "rules": {
                        "IRP_1": {"func": "get_fund_name"},
                        "IRP_2": {"func": "get_fund_manage_name"},
                    },
                    "items": [
                        "鉴于{IRP_2}系一家依照中国法律合法成立并有效存续的有限责任公司，按照相关法律法规的规定具备担任基金管理人的资格和能力，拟募集发行{IRP_1}（以下简称“本基金”或“基金”）；",
                        "鉴于中国银河证券股份有限公司系一家依照中国法律合法成立并有效存续的证券公司，按照相关法律法规的规定具备担任基金托管人的资格和能力；",
                        "鉴于{IRP_2}拟担任{IRP_1}的基金管理人，中国银河证券股份有限公司拟担任{IRP_1}的基金托管人；",
                        "为明确{IRP_1}的基金管理人和基金托管人之间的权利义务关系，特制订本协议；",
                        "除非文义另有所指，本协议的所有术语与《{IRP_1}基金合同》（以下简称《基金合同》或基金合同）中定义的相应术语具有相同的含义。若有抵触应以《基金合同》为准，并依其条款解释。",
                    ],
                },
            ],
        },
    ]

    def check(self):
        condition_checker = BaseConditionsChecker(
            reader=self.reader,
            manager=self.manager,
            file=self.file,
            schema_id=self.schema_id,
            labels=self.labels,
            fund_manager_info=self.fund_manager_info,
        )
        template = {
            "label": self.LABEL,
            "schema_fields": self.SCHEMA_FIELDS,
            "related_name": self.RELATED_NAME,
            "name": self.NAME,
            "from": self.FROM,
            "origin": self.ORIGIN,
            "templates": self.TEMPLATES,
        }
        condition_checker.TEMPLATES = [template]
        check_results = condition_checker.check()
        if not check_results:
            return
        check_res = check_results[0]
        miss_content = not any(reason.matched for reason in check_res.reasons)
        self.result.is_compliance, self.result.reasons = condition_checker.after_match_template(
            template, check_res.reasons, miss_content
        )
        if check_res.suggestion:
            self.result.suggestion = check_res.suggestion
        return self.result
