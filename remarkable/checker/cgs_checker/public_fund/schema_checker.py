import re
from collections import defaultdict
from operator import itemgetter
from typing import Pattern

from remarkable.checker.cgs_checker.base_schema_checker import BaseSchemaChecker
from remarkable.checker.cgs_checker.public_fund.template_checker import (
    BaseConditionsChecker,
)
from remarkable.common.constants import RuleType
from remarkable.common.convert_number_util import NumberUtil
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.plugins.cgs.common.chapters_patterns import (
    R_CONJUNCTION,
    CatalogsPattern,
    ChapterPattern,
    ChapterRule,
)
from remarkable.plugins.cgs.common.enum_utils import ConvertContentEnum
from remarkable.plugins.cgs.common.fund_classification import (
    InvestmentScopeEnum,
    PublicFundClassifyName,
)
from remarkable.plugins.cgs.common.para_similarity import ParagraphSimilarity, Sentence
from remarkable.plugins.cgs.common.patterns_util import (
    P_BOURSE_SH,
    P_BOURSE_SZ,
    P_LINK_SENTENCE,
    P_PARA_PREFIX_NUM,
    P_PUBLIC_SIMILARITY_PATTERNS,
    P_SYMBOL_SPLIT,
    R_CN_NUMBER,
    R_FEES_PAYMENT_DATE,
    R_PUNCTUATION,
)
from remarkable.plugins.cgs.common.template_condition import (
    ContentConditional,
    FundTypeRelation,
    TemplateConditional,
    TemplateName,
    TemplateRelation,
)
from remarkable.plugins.cgs.common.utils import (
    get_chapter_info_by_outline,
    get_outlines,
    get_paragraphs_by_schema_fields,
    get_xpath_by_outlines,
)
from remarkable.plugins.cgs.rules.templates.public_fund import PUBLIC_LAW_SOURCE
from remarkable.plugins.cgs.schemas.reasons import (
    ConflictReasonItem,
    IgnoreConditionItem,
    MatchFailedItem,
    MatchReasonItem,
    MatchSuccessItem,
    MissContentReasonItem,
    NoMatchReasonItem,
    ResultItem,
    Template,
)


class PublicFundSchemaChecker(BaseSchemaChecker):
    SCHEMA_NAME = "公募-基金合同"
    NAME = ""
    RELATED_NAME = ""
    LABEL = ""
    SCHEMA_FIELDS = []
    RULE_TYPE = RuleType.SCHEMA.value
    SYNONYM_PATTERNS = P_PUBLIC_SIMILARITY_PATTERNS
    IGNORE_EXTRA_PARA = True
    CONVERT_TYPES = ConvertContentEnum.member_values()

    def prev_check(self):
        origin_schema_fields = self.SCHEMA_FIELDS
        self.SCHEMA_FIELDS = self.filter_schema_fields(origin_schema_fields)
        # schema_fields不满足条件，直接返回
        if not self.SCHEMA_FIELDS and origin_schema_fields:
            result = self.init_result()
            conditions = []
            for item in origin_schema_fields:
                if isinstance(item, tuple):
                    conditions.extend(item[1])
            result.reasons.append(
                IgnoreConditionItem(reason_text=self.generate_reason_by_template_conditions(conditions))
            )
            return result

    def check(self):
        raise NotImplementedError

    @classmethod
    def get_valid_subclasses(cls, schema_names: set[str]):
        if cls.SCHEMA_NAME in schema_names:
            return cls.__subclasses__()
        return []

    def init_result(self):
        return ResultItem(
            name=self.NAME,
            related_name=self.RELATED_NAME,
            rule_type=self.RULE_TYPE,
            is_compliance=False,
            reasons=[],
            suggestion=None,
            schema_id=self.schema_id,
            fid=self.file.id,
            schema_results=self.manager.build_schema_results(self.SCHEMA_FIELDS),
            label=self.LABEL,
            origin_contents=self.get_origin_contents(),
            contract_content=self.get_contract_content(),
        )


class ValuationObjectDatePrinciple(PublicFundSchemaChecker):
    LABEL = "template_796"
    RULE_TYPE = RuleType.TEMPLATE.value
    SCHEMA_FIELDS = ["估值日", "估值对象", "估值原则"]
    RELATED_NAME = "基金资产估值"
    NAME = "估值日、估值对象和估值原则"
    FROM = "关于发布《证券公司金融工具估值指引》等三项指引的通知 中证协发[2018]216号 2018年9月7日"
    CONTRACT_CONTENT = [
        "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
        "一、估值日",
        "本基金的估值日为本基金相关的证券交易场所的交易日以及国家法律法规规定需要对外披露基金净值的非交易日。",
        "二、估值对象",
        "基金所拥有的股票、权证、债券和银行存款本息、应收款项、其它投资等资产及负债。",
        "三、估值原则",
        "基金管理人在确定相关金融资产和金融负债的公允价值时，应符合《企业会计准则》、监管部门有关规定。",
        "（一）对存在活跃市场且能够获取相同资产或负债报价的投资品种，在估值日有报价的，除会计准则规定的例外情况外，应将该报价不加调整地应用于该资产或负债的公允价值计量。估值日无报价且最近交易日后未发生影响公允价值计量的重大事件的，应采用最近交易日的报价确定公允价值。有充足证据表明估值日或最近交易日的报价不能真实反映公允价值的，应对报价进行调整，确定公允价值。",
        "与上述投资品种形同，但具有不同特征的，应以相同资产或负债的公允价值为基础，并在估值技术中考虑不同特征因素的影响。特征是指对资产出售或使用的限制等，如果该限制是针对资产持有者的，那么在估值技术中不应将该限制作为特征考虑。此外，基金管理人不应考虑因其大量持有相关资产或负债所产生的溢价或折价。",
        "（二）对不存在活跃市场的投资品种，应采用在当前情况下适用并且有足够可利用数据和其他信息支持的估值技术确定公允价值。采用估值技术确定公允价值时，应优先使用可观察输入值，只有在无法取得相关资产或负债可观察输入值或取得不切实可行的情况下，才可以使用不可观察输入值。",
        "（三）如经济环境发生重大变化或证券发行人发生影响证券价格的重大事件，使潜在估值调整对前一估值日的基金资产净值的影响在0.25 % 以上的，应对估值进行调整并确定公允价值。",
    ]
    ORIGIN = [
        "第二章估值基本原则",
        "第三条【存在活跃市场投资品种的估值原则】",
        "对存在活跃市场且能够获取相同资产或负债报价的投资品种,在估值日有报价的,除会计准则规定的例外情况外,应将该报价不加调整地应用于该资产或负债的公允价值计量。估值日无报价且最近交易日后未发生影响公允价值计量的重大事件的,应采用最近交易日的报价确定公允价值。有充足证据表明估值日或最近交易日的报价不能真实反映公允价值的,应对报价进行调整,确定公允价值。",
        "与上述投资品种相同,但具有不同特征的,应以相同资产或负债的公允价值为基础,并在估值技术中考虑不同特征因素的影响。特征是指对资产出售或使用的限制等,如果该限制是针对资产持有者的,那么在估值技术中不应将该限制作为特征考虑。此外,持有人不应考虑因其大量持有相关资产或负债所产生的溢价或折价。",
        "第四条【不存在活跃市场投资品种的估值原则】",
        "对不存在活跃市场的投资品种,应采用在当前情况下适用并且有足够可利用数据和其他信息支持的估值技术确定公允价值。采用估值技术确定公允价值时,应优先使用可观察输入值,只有在无法取得相关资产或负债可观察输入值或取得不切实可行的情况下,才可以使用不可观察输入值。",
        "第五条【影响公允价值计量的重大事件的参考标准】",
        "当权益工具、债务工具的发行方发生以下情况时,证券公司需判断金融工具的公允价值是否产生重大变动:",
        "1)与预算、计划或阶段性目标相比,公司的业绩发生重大的变化;",
        "2)对技术产品实现阶段性目标的预期发生变化;",
        "3)所在市场或其产品或潜在产品发生重大变化;",
        "4)全球经济或者所处的经济环境发生重大变化;",
        "5)可观察到的可比公司的业绩,或整体市场的估值结果发生重大变化;",
        "6)内部事件,如欺诈、商业纠纷、诉讼、管理层或战略的改变;",
        "7)其他影响公允价值的重大事件。",
    ]

    PATTERNS = [
        {"pattern": PatternCollection(r"ETF基金"), "value": "目标ETF基金份额"},
        {"pattern": PatternCollection(r"股票(?!(?:指数|期权))"), "value": "股票"},
        {"pattern": PatternCollection(r"存托凭证"), "value": "存托凭证"},
        {"pattern": PatternCollection(r"股指期货"), "value": "股指期货合约"},
        {"pattern": PatternCollection(r"股票期权"), "value": "股票期权合约"},
        {"pattern": PatternCollection(r"债券"), "value": "债券"},
        {"pattern": PatternCollection(r"衍生"), "value": "衍生工具"},
        {"pattern": PatternCollection(r"资产支持"), "value": "资产支持证券"},
    ]
    PARA_PATTERN = PatternCollection(rf"基金所(拥有|投资)的?(?P<content>[^,，。；;]+)资产[{R_CONJUNCTION}]负债")
    DEFAULT = "目标ETF基金份额、股票、存托凭证、股指期货合约、股票期权合约、债券、衍生工具、资产支持证券"

    LAW_TEMPLATES = [
        "一、估值日",
        "本基金的估值日为本基金相关的证券交易场所的交易日以及国家法律法规规定需要对外披露基金净值的非交易日。",
        "三、估值原则",
        "基金管理人在确定相关金融资产和金融负债的公允价值时，应符合《企业会计准则》、监管部门有关规定。",
        "（一）对存在活跃市场且能够获取相同资产或负债报价的投资品种，在估值日有报价的，除会计准则规定的例外情况外，应将该报价不加调整地应用于该资产或负债的公允价值计量。估值日无报价且最近交易日后未发生影响公允价值计量的重大事件的，应采用最近交易日的报价确定公允价值。有充足证据表明估值日或最近交易日的报价不能真实反映公允价值的，应对报价进行调整，确定公允价值。",
        "与上述投资品种形同，但具有不同特征的，应以相同资产或负债的公允价值为基础，并在估值技术中考虑不同特征因素的影响。特征是指对资产出售或使用的限制等，如果该限制是针对资产持有者的，那么在估值技术中不应将该限制作为特征考虑。此外，基金管理人不应考虑因其大量持有相关资产或负债所产生的溢价或折价。",
        "（二）对不存在活跃市场的投资品种，应采用在当前情况下适用并且有足够可利用数据和其他信息支持的估值技术确定公允价值。采用估值技术确定公允价值时，应优先使用可观察输入值，只有在无法取得相关资产或负债可观察输入值或取得不切实可行的情况下，才可以使用不可观察输入值。",
        "（三）如经济环境发生重大变化或证券发行人发生影响证券价格的重大事件，使潜在估值调整对前一估值日的基金资产净值的影响在0.25%以上的，应对估值进行调整并确定公允价值。",
    ]

    def check_law(self, result: ResultItem, common_paragraphs):
        # 法规
        self.paragraph_similarity(
            result=result,
            paragraphs_left_list=[self.LAW_TEMPLATES],
            paragraphs_right=common_paragraphs,
            outlines=self.calc_outlines_by_paragraphs(common_paragraphs),
            origin_content="\n".join(self.LAW_TEMPLATES),
            name=TemplateName.LAW_NAME,
            content_title=TemplateName.LAW_TITLE,
            source=PUBLIC_LAW_SOURCE,
        )

    def check_editing(self, result: ResultItem, common_paragraphs):
        # 范文
        answer = self.manager.get(self.SCHEMA_FIELDS[1])
        investment_scope_value = clean_txt(self.manager.get("基金投资范围").value)
        res = self.PARA_PATTERN.nexts(clean_txt(answer.value))
        match_content = res.groupdict()["content"]
        # 根据“、与和及”等词拆分当前段落，
        content_list = []
        next_pos = 0
        for link_res in P_LINK_SENTENCE.finditer(match_content):
            content_list.append((match_content[next_pos : link_res.span()[0]], link_res.group()))
            next_pos = link_res.span()[-1]
        if len(match_content) != next_pos:
            content_list.append((match_content[next_pos:], ""))
        format_vals = []
        for idx, (value, link_str) in enumerate(content_list):
            for check_pattern in self.PATTERNS:
                if check_pattern["pattern"].nexts(value):
                    if not check_pattern["pattern"].nexts(investment_scope_value):
                        result.reasons.append(MatchFailedItem(reason_text="估值对象出现了投资范围中未出现的投资品种"))
                        result.suggestion = "估值对象投资品种，要与投资范围包含的品种需匹配，请检查估值对象中投资品种"
                        return
                    else:
                        format_vals.append((idx, [check_pattern["value"], link_str]))
                        break
        sorted_vals = []
        for _, vals in sorted(format_vals, key=lambda x: x[0]):
            sorted_vals.extend(vals)
        # 默认不需要最后一位联结词
        format_val = "".join(sorted_vals[:-1])
        templates = [
            "二：基金所拥有的{}、银行存款本息、应收款项、其它投资等资产及负债。".format(format_val or self.DEFAULT)
        ]
        self.paragraph_similarity(
            result=result,
            paragraphs_left_list=[templates],
            paragraphs_right=common_paragraphs,
            outlines=self.calc_outlines_by_paragraphs(common_paragraphs),
            origin_content=templates[0],
            name=TemplateName.EDITING_NAME,
            content_title=TemplateName.EDITING_TITLE,
        )

    def check(self):
        result = self.init_result()
        self.check_schema_fields(result)
        if result.suggestion:
            return result
        answer_chapter, common_paragraphs = get_paragraphs_by_schema_fields(
            self.reader, self.manager, self.SCHEMA_FIELDS
        )
        if not common_paragraphs:
            result.reasons.append(MatchFailedItem(reason_text="当前规则对应的要素答案未找到对应内容"))
            return result
        self.check_law(result, common_paragraphs)
        self.check_editing(result, common_paragraphs)
        return result


class FundInvestmentScopeChecker(PublicFundSchemaChecker):
    LABEL = "schema_818"
    RELATED_NAME = "基金的投资"
    NAME = "投资范围-投资融资融券的产品类型限制"
    FROM = "基金参与融资融券及转融通证券出借业务指引（中基协发〔2015〕4号 2015年4月17日）"
    ORIGIN = [
        "第四条【参与范围和比例】基金参与融资融券交易及转融通证券出借交易，除中国证监会另有规定或批准的特殊基金品种外，应当遵守下列要求：",
        "（一）股票型基金、混合型基金可以参与融资业务。基金参与融资业务后，在任何交易日日终，股票型、混合型基金持有的融资买入股票与其他有价证券市值之和，不得超过基金资产净值的95%。",
        "（二）采用绝对收益、对冲策略的基金可以参与融券交易。基金参与融券交易，融券资产净值不得高于基金资产净值的33%。",
    ]
    SCHEMA_FIELDS = ["基金的类别、类型", "基金投资范围"]

    R_INVESTMENT_SCOPE = ["融资", "融券"]
    # 股票型/混合型
    P_VALID_FUND_TYPES = [TemplateConditional.FUND_TYPE_STOCK_MIXTURE]
    # 融资/融券
    P_INVESTMENT_SCOPE = [TemplateConditional.SPECIAL_TYPE_FINANCING_OR_SECURITIES_LENDING]

    def check(self):
        result = self.init_result()
        self.check_schema_fields(result)
        if result.suggestion:
            return result
        suggestions = []
        if self.manager.verify_condition(self.P_VALID_FUND_TYPES) or not self.manager.verify_condition(
            self.P_INVESTMENT_SCOPE
        ):
            result.is_compliance = True
        else:
            result.reasons.append(
                MatchFailedItem(reason_text=f"当前基金类型投资范围不可投资{'或'.join(self.R_INVESTMENT_SCOPE)}")
            )
            suggestions.append(f"建议检查当前投资范围（{'或'.join(self.R_INVESTMENT_SCOPE)}）")

        result.suggestion = "\n".join(suggestions)
        return result


class RefinanceInvestmentScopeChecker(FundInvestmentScopeChecker):
    LABEL = "schema_819"
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

    R_INVESTMENT_SCOPE = ["转融通证券出借"]
    # 股票型/混合型/开放式股票型指数基金/ETF/ETF联接基金
    P_VALID_FUND_TYPES = [TemplateConditional.FUND_TYPE_STOCK_MIXTURE_ETF_LINKED]
    P_INVESTMENT_SCOPE = [TemplateConditional.SPECIAL_TYPE_RE_FINANCE]


class FundBourseTypeChecker(PublicFundSchemaChecker):
    LABEL = "schema_817"
    RELATED_NAME = "基金份额的上市交易"
    NAME = "基金份额的上市交易-交易所"
    FROM = [
        "深圳证券交易所证券投资基金交易和申购赎回实施细则（2022年修订）（深证上〔2022〕559号 2022年06月10日）",
        "深圳证券交易所证券投资基金上市规则（2006年02月13日深证会[2006]3号）",
    ]
    ORIGIN = [
        (
            "第六条 封闭式基金、交易型开放式基金（以下简称“ETF”）、上市开放式基金（以下简称“LOF”）、分级基金及本所认可的其他基金品种，可以在本所上市交易。"
            "封闭式基金是指在本所上市交易、基金份额总额在基金合同期限内固定不变的基金。ETF是指在本所上市交易的开放式基金，其基金份额使用组合证券、"
            "现金或者基金合同约定的其他对价按照“份额申购、份额赎回”的方式进行申赎。LOF是指在本所上市交易的开放式基金，其基金份额使用现金按照“金额申购、份额赎回”的方式进行申赎。"
        ),
        (
            "分级基金是指通过基金合同约定的风险收益分配方式，将基金份额分为预期风险收益不同的子份额，其中全部或者部分类别份额在本所上市交易或者申赎的基金。根据基金合同的约定，"
            "分级基金的基础份额和子份额之间可以通过分拆、合并进行配对转换，分拆、合并的具体规则由本所或者其他办理场所另行规定。"
        ),
        "第二条 本规则所称基金指封闭式基金、上市开放式基金、交易型开放式指数基金及其他证券投资基金。",
    ]
    SCHEMA_FIELDS = ["上市交易所", "基金的类别、类型"]

    BOURSE_CHECKERS = [
        (
            P_BOURSE_SZ,
            {
                "suggestion": "深交所上市的产品类型应为：封闭式、ETF、LOF、分级基金",
                "conditions": [TemplateConditional.SPECIAL_TYPE_ETF_LOF_CLOSE_CLASSIFY],
            },
        ),
        (
            P_BOURSE_SH,
            {
                "suggestion": "上交所上市的产品类型应为：封闭式、ETF",
                "conditions": [TemplateConditional.SPECIAL_TYPE_ETF_OR_CLOSE],
            },
        ),
    ]

    def check(self):
        result = self.init_result()
        if not self.manager.verify_condition([TemplateConditional.LISTED_TRANSACTION_YES]):
            result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型为非上市类型"))
        else:
            self.check_schema_fields(result)
            if result.suggestion:
                return result
            suggestions = []
            bourse_values = self.manager.check_stock_bourse()
            bourse_name = (bourse_values and bourse_values[0].value) or ""
            for p_bourse, check_dict in self.BOURSE_CHECKERS:
                if not p_bourse.nexts(bourse_name):
                    continue
                result.is_compliance = self.manager.verify_condition(check_dict["conditions"])
                if not result.is_compliance:
                    result.reasons.append(MatchFailedItem(reason_text="交易所与产品类型不匹配"))
                    suggestions.append(check_dict["suggestion"])
                break
            else:
                result.reasons.append(MatchFailedItem(reason_text="交易所应为上交所或深交所"))
                suggestions.append("建议检查当前交易所")
            result.suggestion = "\n".join(suggestions)

        return result


class FundNameChecker(PublicFundSchemaChecker):
    """
    基金名称检查
    """

    RULE_TYPE = RuleType.TEMPLATE.value
    RELATED_NAME = "基金名称"
    SCHEMA_FIELDS = ["基金名称"]
    LABEL = "schema_809"
    NAME = "全文基金名称保持一致"
    SUGGESTIONS_ON_REVISION = ["请添加基金名称", "全文基金名称需保持一致"]
    REASON = ["基金名称不可为空", "基金名称不是"]
    P_TAIL_PAGE = None
    P_CHAPTERS = {
        "前言": [re.compile(r"前言")],
        "释义": [re.compile(r"释义")],
    }

    P_PARAPHRASES = [
        re.compile(rf"^\d*.{{0,3}}基金[{R_CONJUNCTION}]本基金"),
        re.compile(rf"^\d*.{{0,3}}基金合同[{R_CONJUNCTION}]本基金合同"),
        re.compile(r"^\d*.{0,3}托管协议"),
        re.compile(r"^\d*.{0,3}招募说明书"),
        re.compile(r"^\d*.{0,3}基金产品资料概要"),
        re.compile(r"^\d*.{0,3}基金份额发售公告"),
        re.compile(r"^\d*.{0,3}上市交易公告书"),
    ]

    P_FOREWORD = re.compile(r"由基金管理人依照.{10,20}募集.{1,5}中国证券监督管理委员会.{1,10}中国证监会.{1,5}注册")

    MATCHING_FIELD = ""

    def _return(self, is_compliance, reasons, suggestion):
        result = self.init_result()
        result.is_compliance = is_compliance
        result.reasons = reasons
        result.suggestion = suggestion
        return result

    def check(self):
        fund_name_mode = self.manager.get(self.SCHEMA_FIELDS[0])
        reasons = []
        suggestion = None

        if not fund_name_mode.value:
            reasons.append(MatchFailedItem(reason_text=self.REASON[0]))
            suggestion = self.SUGGESTIONS_ON_REVISION[0]
            return self._return(False, reasons, suggestion)

        # 1、检查封面
        unmatch_paragraphs = self.check_cover(fund_name_mode.value)
        # 检查签署页
        unmatch_paragraphs.extend(self.check_signature_page(fund_name_mode.value, self.P_TAIL_PAGE))

        # 3、根据正则检查相关页面
        valid_types = ["PARAGRAPH", "TABLE"]
        for key, values in self.P_CHAPTERS.items():
            _, paragraphs = self.reader.find_paragraphs_by_chapters(
                values, is_continued_chapter=False, valid_types=valid_types
            )
            sentences = Sentence.create_sentences(paragraphs, ignore_numbering=False, split=False)
            if key == "释义":
                for _sentence in sentences:
                    for reg in self.P_PARAPHRASES:
                        if reg.match(clean_txt(_sentence.text)):
                            if fund_name_mode.value not in _sentence.text and (
                                self.MATCHING_FIELD and self.MATCHING_FIELD not in _sentence.text
                            ):
                                unmatch_paragraphs.append(_sentence.origin)
            elif key == "前言":
                for _sentence in sentences:
                    if self.P_FOREWORD.search(clean_txt(_sentence.text)):
                        if fund_name_mode.value not in _sentence.text:
                            unmatch_paragraphs.append(_sentence.origin)
        is_compliance = True
        if unmatch_paragraphs:
            page_paragraphs = defaultdict(list)
            for paragraph in unmatch_paragraphs:
                page_paragraphs[paragraph["page"]].append(paragraph)
            for page in sorted(page_paragraphs):
                outlines = get_outlines(page_paragraphs[page])
                reasons.append(
                    MatchFailedItem(
                        reason_text=f"{self.REASON[1]}“{fund_name_mode.value}”",
                        page=page,
                        matched=False,
                        outlines=outlines,
                    )
                )
            suggestion = self.SUGGESTIONS_ON_REVISION[1]
            is_compliance = False
        return self._return(is_compliance, reasons, suggestion)


class FundManagerChecker(FundNameChecker):
    """
    管理人名称检查
    """

    RELATED_NAME = "管理人名称"
    SCHEMA_FIELDS = ["基金管理人-名称"]
    LABEL = "schema_810"
    NAME = "全文管理人名称保持一致"
    SUGGESTIONS_ON_REVISION = ["请添加管理人名称", "全文管理人名称需保持一致"]
    REASON = ["管理人名称不可为空", "管理人名称不是"]
    P_CHAPTERS = {
        "释义": [re.compile(r"释义")],
    }
    P_TAIL_PAGE = PatternCollection(r"基金管理人[:：]")

    P_PARAPHRASES = [
        re.compile(r"^\d*.{0,3}基金管理人"),
        re.compile(r"^\d*.{0,3}登记机构"),
        re.compile(r"^\d*.{0,3}销售机构"),
    ]

    MATCHING_FIELD = "基金管理人"


class FundTrusteeChecker(FundNameChecker):
    """
    托管人名称检查
    """

    RELATED_NAME = "基金托管人"
    SCHEMA_FIELDS = ["基金托管人-名称"]
    LABEL = "schema_811"
    NAME = "全文托管人名称保持一致"
    SUGGESTIONS_ON_REVISION = ["请添加托管人名称", "全文托管人名称需保持一致"]
    REASON = ["托管人名称不可为空", "托管人名称不是"]
    P_CHAPTERS = {
        "释义": [re.compile(r"释义")],
    }
    P_TAIL_PAGE = PatternCollection(r"基金托管人[:：]")

    P_PARAPHRASES = [
        re.compile(r"^\d*.{0,3}基金托管人"),
    ]


class FundPublicDisclosureChecker(PublicFundSchemaChecker):
    LABEL = "schema_821"
    SCHEMA_FIELDS = ["公开披露的基金信息"]
    RELATED_NAME = "基金的信息披露"
    NAME = "信息披露-公开披露的信息"
    FROM = "公开募集证券投资基金信息披露管理办法（证监会令第166号修订 2020年3月20日）"
    ORIGIN = [
        "第六条　公开披露的基金信息包括：",
        "（一）基金招募说明书；",
        "（二）基金合同；",
        "（三）基金托管协议；",
        "（四）基金产品资料概要；",
        "（五）基金份额发售公告；",
        "（六）基金募集情况；",
        "（七）基金份额上市交易公告书；",
        "（八）基金资产净值、基金份额净值；",
        "（九）基金份额申购、赎回价格；",
        "（十）基金定期报告，包括年度报告、中期报告和季度报告（含资产组合季度报告）；",
        "（十一）临时报告；",
        "（十二）基金份额持有人大会决议；",
        "（十三）基金管理人、基金托管人的专门基金托管部门的重大人事变动；",
        "（十四）涉及基金财产、基金管理业务、基金托管业务的诉讼或者仲裁；",
        "（十五）澄清公告；",
        "（十六）清算报告；",
        "（十七）中国证监会规定的其他信息。",
    ]
    R_PREFIX_NUM = r"（）()\d一二三四五六七八九十、《》"

    TEMPLATES = [
        {
            "template": ["基金招募说明书"],
            "pattern": PatternCollection(rf"^[{R_PREFIX_NUM}]*?(?:基金)?招募说明书.?$"),
        },
        {
            "template": ["基金合同"],
            "pattern": PatternCollection(rf"^[{R_PREFIX_NUM}]*?基金合同.?$"),
        },
        {
            "template": ["基金托管协议"],
            "pattern": PatternCollection(rf"^[{R_PREFIX_NUM}]*?(?:基金)?托管协议.?$"),
        },
        {
            "template": ["基金产品资料概要"],
            "pattern": PatternCollection(rf"^[{R_PREFIX_NUM}]*?(?:基金)?产品资料概要.?$"),
        },
        {
            "template": ["基金份额发售公告"],
            "pattern": PatternCollection(rf"^[{R_PREFIX_NUM}]*?(?:基金)?份额发售公告.?$"),
        },
        {
            "template": ["基金募集情况"],
            "pattern": PatternCollection(rf"^[{R_PREFIX_NUM}]*?(?:基金)?募集情况.?$"),
        },
        {
            "conditions": [TemplateConditional.LISTED_TRANSACTION_YES],
            "template": ["基金份额上市交易公告书"],
            "pattern": PatternCollection(rf"^[{R_PREFIX_NUM}]*?(?:基金)?份额上市交易公告书.?$"),
        },
        {
            "template": ["基金资产净值、基金份额净值", "基金净值信息"],
            "pattern": PatternCollection(rf"^[{R_PREFIX_NUM}]*?(?:基金)?(?:(?:资产|份额)净值|净值信息).?$"),
        },
        {
            "template": ["基金份额申购、赎回价格", "基金份额申购、赎回对价"],
            "pattern": PatternCollection(rf"^[{R_PREFIX_NUM}]*?(?:基金)?(?:份额申购|赎回价格|赎回对价).?$"),
        },
        {
            "template": [
                "基金定期报告，包括年度报告、中期报告和季度报告（含资产组合季度报告）",
                "基金定期报告，包括基金年度报告、基金中期报告和基金季度报告",
            ],
            "pattern": PatternCollection(rf"^[{R_PREFIX_NUM}]*?(?:基金)?定期报告.?$"),
        },
        {
            "template": ["临时报告"],
            "pattern": PatternCollection(rf"^[{R_PREFIX_NUM}]*?临时报告.?$"),
        },
        {
            "template": ["基金份额持有人大会决议"],
            "pattern": PatternCollection(rf"^[{R_PREFIX_NUM}]*?(?:基金)?份额持有人大会决议.?$"),
        },
        {
            "template": ["澄清公告"],
            "pattern": PatternCollection(rf"^[{R_PREFIX_NUM}]*?澄清公告.?$"),
        },
        {
            "template": ["清算报告"],
            "pattern": PatternCollection(rf"^[{R_PREFIX_NUM}]*?清算报告.?$"),
        },
        {
            "template": ["中国证监会规定的其他信息"],
            "pattern": PatternCollection(rf"^[{R_PREFIX_NUM}]*?中国证监会规定的其他信息.?$"),
        },
    ]

    def check(self):
        result = self.init_result()
        name, content_title = TemplateName.LAW_NAME, TemplateName.LAW_TITLE

        _, paragraphs = get_paragraphs_by_schema_fields(self.reader, self.manager, self.SCHEMA_FIELDS)
        template_mappings = []
        prefix_num = 1
        for item in self.TEMPLATES:
            if not item.get("conditions") or self.manager.verify_condition(item["conditions"]):
                item["prefix"] = str(prefix_num)
                template_mappings.append(item)
                prefix_num += 1
        origin_content = "\n".join([f"{item['prefix']} {item['template']}" for item in template_mappings])
        if not paragraphs:
            result.reasons = [NoMatchReasonItem(template=Template(content=origin_content, name=name))]
            return result
        match_list = defaultdict(list)
        for template_dict in template_mappings:
            is_match = False
            for _para in paragraphs:
                content = clean_txt(_para["text"])
                for val in P_SYMBOL_SPLIT.split(content):
                    if template_dict["pattern"].nexts(val):
                        is_match = True
                        match_list[_para["index"]].append(template_dict)
                        break
                if is_match:
                    break
            if not is_match:
                match_list[-1].append(template_dict)
        templates = self.recombinate_templates(match_list)
        template_paragraphs = []
        format_templates = []
        for para, val in templates:
            if para:
                template_paragraphs.append(para)
                format_templates.append(val)
        format_templates = BaseConditionsChecker.recombined_template(format_templates)
        self.paragraph_similarity(
            result=result,
            paragraphs_left_list=format_templates,
            paragraphs_right=template_paragraphs,
            outlines=self.calc_outlines_by_paragraphs(template_paragraphs),
            origin_content=origin_content,
            name=name,
            content_title=content_title,
            source=PUBLIC_LAW_SOURCE,
        )
        return result

    def assemble_sentence(self, sorted_vals):
        """
        组装句子:
        eg:
        from:[['基金招募说明书', '1'], '、', ['基金合同', '2'], '、', ['基金托管协议', '3'], '、', ['基金产品资料概要', '4'], '']
        to： ['基金招募说明书、基金合同、基金托管协议、基金产品资料概要',
         '1、基金合同、基金托管协议、基金产品资料概要',
         '基金招募说明书、2、基金托管协议、基金产品资料概要',
          '1、2、基金托管协议、基金产品资料概要',
          '基金招募说明书、基金合同、3、基金产品资料概要',
          '1、基金合同、3、基金产品资料概要',
          '基金招募说明书、2、3、基金产品资料概要',
          '1、2、3、基金产品资料概要',
          '基金招募说明书、基金合同、基金托管协议、4',
          '1、基金合同、基金托管协议、4',
          '基金招募说明书、2、基金托管协议、4',
          '1、2、基金托管协议、4',
          '基金招募说明书、基金合同、3、4',
          '1、基金合同、3、4',
          '基金招募说明书、2、3、4',
          '1、2、3、4'
          ]
        """
        if len(sorted_vals) == 1:
            return sorted_vals[0]
        res_list = sorted_vals[0]
        for sorted_val in sorted_vals[1:]:
            if isinstance(sorted_val, list):
                temps = []
                for item in sorted_val:
                    for s in res_list:
                        temps.append(s + item)
                res_list = temps
            if isinstance(sorted_val, str):
                res_list = [s + sorted_val for s in res_list]
        return res_list

    def recombinate_templates(self, match_templates: dict) -> list[tuple]:
        templates = []
        for para_index, template_dicts in match_templates.items():
            if para_index == -1:
                continue
            prefix = ""
            _, para = self.reader.find_element_by_index(para_index)
            content = clean_txt(para["text"])
            if len(template_dicts) == 1:
                # 默认不需要最后一位联结词
                if res := P_PARA_PREFIX_NUM.nexts(content):
                    prefix = res.group("prefix")
                temps = [f"{prefix}{temp}" for temp in template_dicts[0]["template"]]
                templates.append((para, temps))
                continue
            content = clean_txt(para["text"])
            # 根据“、与和及”等词拆分当前段落，
            content_list = []
            next_pos = 0
            for link_res in P_SYMBOL_SPLIT.finditer(content):
                content_list.append((content[next_pos : link_res.start()], link_res.group()))
                next_pos = link_res.end()
            if len(content) != next_pos:
                content_list.append((content[next_pos:], ""))
            # 按联结词划分词组，按顺序匹配正则
            format_vals = []
            for template_dict in template_dicts:
                for idx, (value, link_str) in enumerate(content_list):
                    if template_dict["pattern"].nexts(value):
                        format_vals.append((idx, [template_dict["template"], link_str]))
                        break

            sorted_vals = []
            for _, vals in sorted(format_vals, key=lambda x: x[0]):
                sorted_vals.extend(vals)
            res_list = self.assemble_sentence(sorted_vals)
            # 默认不需要最后一位联结词
            if res := P_PARA_PREFIX_NUM.nexts(content):
                prefix = res.group("prefix")
            res_list = [f"{prefix}{res}" for res in res_list]
            templates.append((para, res_list))

        if template_dicts := match_templates[-1]:
            for template in template_dicts:
                templates.append((None, template["template"]))
        return templates


class RightChapterAbstractChecker(PublicFundSchemaChecker):
    # 基金合同当事人的权利与义务
    LABEL = "schema_824"
    RELATED_NAME = "基金合同内容摘要"
    NAME = "合同摘要-当事人权利义务"

    RESULT_NAME = "正文"
    CONTENT_TITLE = "合同摘要"

    EXIST_COMPLIANCE = False

    P_DIGEST_CHAPTER = CatalogsPattern.FUND_CONTRACT_DIGEST.pattern

    # 合同摘要->基金合同当事人的权利与义务->(份额持有人/管理人/托管人)的权利和义务
    DIGEST_CHAPTERS = [
        ChapterRule(
            [
                CatalogsPattern.FUND_CONTRACT_DIGEST,
                CatalogsPattern.FUND_RIGHT_OBLIGATION,
                CatalogsPattern.FUND_RIGHT_OBLIGATION_SHARE_HOLDER_RIGHT_DUTY,
            ],
            is_continued_chapter=False,
        ).convert2dict(),
        ChapterRule(
            [
                CatalogsPattern.FUND_CONTRACT_DIGEST,
                CatalogsPattern.FUND_RIGHT_OBLIGATION,
                CatalogsPattern.FUND_RIGHT_OBLIGATION_MANAGER_RIGHT_DUTY,
            ],
            is_continued_chapter=False,
        ).convert2dict(),
        ChapterRule(
            [
                CatalogsPattern.FUND_CONTRACT_DIGEST,
                CatalogsPattern.FUND_RIGHT_OBLIGATION,
                CatalogsPattern.FUND_RIGHT_OBLIGATION_TRUSTEE_RIGHT_DUTY,
            ],
            is_continued_chapter=False,
        ).convert2dict(),
    ]
    # 正文：基金合同当事人权利与义务 -> (份额持有人/管理人/托管人)的权利和义务
    CONTRACT_CHAPTERS = [
        ChapterRule(
            [CatalogsPattern.FUND_RIGHT_OBLIGATION, CatalogsPattern.FUND_RIGHT_OBLIGATION_SHARE_HOLDER_RIGHT_DUTY],
            is_continued_chapter=False,
        ).convert2dict(),
        ChapterRule(
            [CatalogsPattern.FUND_RIGHT_OBLIGATION, CatalogsPattern.FUND_RIGHT_OBLIGATION_MANAGER_RIGHT_DUTY],
            is_continued_chapter=False,
        ).convert2dict(),
        ChapterRule(
            [CatalogsPattern.FUND_RIGHT_OBLIGATION, CatalogsPattern.FUND_RIGHT_OBLIGATION_TRUSTEE_RIGHT_DUTY],
            is_continued_chapter=False,
        ).convert2dict(),
    ]

    # 份额持有人、管理人、托管人
    PARENT_CHAPTER_PATTERNS = [
        CatalogsPattern.FUND_RIGHT_OBLIGATION_SHARE_HOLDER,
        CatalogsPattern.FUND_RIGHT_OBLIGATION_MANAGER,
        CatalogsPattern.FUND_RIGHT_OBLIGATION_TRUSTEE,
    ]

    def check(self):
        result = self.init_result()
        digest_reasons, digest_paragraphs = self.get_paragraphs_by_chapter(self.DIGEST_CHAPTERS)
        contract_reasons, contract_paragraphs = self.get_paragraphs_by_chapter(
            self.CONTRACT_CHAPTERS, ignore_digest=True
        )
        result.reasons.extend(digest_reasons)
        result.reasons.extend(contract_reasons)
        if not (digest_paragraphs and contract_paragraphs):
            return result
        # 忽略正文中一级标题、合同摘要中一级及二级标题
        return self.compare_digest_with_contract_paras(contract_paragraphs, digest_paragraphs, result)

    def compare_digest_with_contract_paras(self, contract_paragraphs, digest_paragraphs, result):
        similarity = ParagraphSimilarity(
            contract_paragraphs,
            digest_paragraphs,
            similarity_patterns=self.SYNONYM_PATTERNS,
        )
        origin_content = "\n".join([para["text"] for para in digest_paragraphs])
        outlines = self.calc_outlines_by_paragraphs(digest_paragraphs)
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2996#note_420560
        if (
            similarity.is_full_matched_or_contain
            or similarity.is_full_matched_without_extra_para
            or (self.EXIST_COMPLIANCE and similarity.is_matched)
        ):
            result.reasons.append(
                MatchReasonItem(
                    template=Template(content=origin_content, name=self.RESULT_NAME, content_title=self.RESULT_NAME),
                    content=similarity.right_content,
                    content_title=self.CONTENT_TITLE,
                    page=min(outlines, key=int, default=0),
                    outlines=outlines,
                    diff=similarity.simple_results,
                )
            )
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2996#note_420540
            result.is_compliance = True
            return result
        if similarity.is_matched:
            result.reasons.append(
                ConflictReasonItem(
                    template=Template(content=origin_content, name=self.RESULT_NAME, content_title=self.RESULT_NAME),
                    content=similarity.right_content,
                    page=min(outlines, key=int, default=0),
                    content_title=self.CONTENT_TITLE,
                    outlines=outlines,
                    diff=similarity.simple_results,
                    xpath=get_xpath_by_outlines(self.reader, outlines),
                )
            )
            return result
        outlines = get_outlines(digest_paragraphs)
        result.reasons.append(
            MatchFailedItem(
                page=min(outlines, key=int, default=0),
                outlines=outlines,
                reason_text=f"未找到与{self.CONTENT_TITLE}相似的内容",
            )
        )
        return result

    def get_paragraphs_by_chapter(self, chapter_rules: list, ignore_digest=False):
        slice_num = 1 if ignore_digest else 2
        reasons = []
        paragraphs = []
        for idx, rule in enumerate(chapter_rules):
            offset = 0
            chapters, _ = self.reader.find_paragraphs_by_chapters(rule["chapters"][:1])
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2049
            # 非摘要章节，如果该章节为非一级且父章节为摘要章节，则提示未找到
            parent_chapter = None
            if chapters and ignore_digest and chapters[0]["level"] != 1:
                parent_chapter = self.reader.syllabus_dict.get(chapters[0]["parent"])
            if not chapters or (parent_chapter and self.P_DIGEST_CHAPTER.search(clean_txt(parent_chapter["title"]))):
                reasons.append(
                    MissContentReasonItem(
                        reason_text=rule["miss_detail"]["reason_text"],
                        miss_content=rule["miss_detail"].get("miss_content"),
                    )
                )
                continue
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2136#note_324409
            with_parent_pattern_paras = []
            if self.PARENT_CHAPTER_PATTERNS:
                with_parent_pattern_paras = self.get_paragraphs_by_patterns(
                    [*rule["chapters"][1:-1], self.PARENT_CHAPTER_PATTERNS[idx].pattern],
                    rule["is_continued_chapter"],
                    parent_chapter=chapters[0],
                )
            if not (
                _paras := (
                    self.get_paragraphs_by_patterns(
                        rule["chapters"][1:], rule["is_continued_chapter"], parent_chapter=chapters[0]
                    )
                    or with_parent_pattern_paras
                )
            ):
                reasons.append(
                    MissContentReasonItem(
                        reason_text=rule["miss_detail"]["reason_text"],
                        miss_content=rule["miss_detail"].get("miss_content"),
                    )
                )
                continue
            _, elt = self.reader.find_element_by_index(chapters[0]["element"])
            if elt:
                if elt not in _paras:
                    _paras.append(elt)
            else:
                offset = 1
            _paras = sorted(_paras, key=itemgetter("index"))
            paragraphs.extend(_paras[slice_num - offset :])
        filter_paras = []
        for para in paragraphs:
            if para and para not in filter_paras:
                filter_paras.append(para)
        return reasons, sorted(filter_paras, key=itemgetter("index"))

    def get_paragraphs_by_patterns(
        self, chapter_patterns: list[Pattern], is_continued_chapter=True, parent_chapter=None
    ):
        if not chapter_patterns:
            if not parent_chapter:
                return []
            return self.reader.get_elements_by_syllabus(parent_chapter)
        candidates = parent_chapter["children"] if parent_chapter else None
        _chapters, paras = self.reader.find_paragraphs_by_chapters(
            chapter_patterns,
            is_continued_chapter=is_continued_chapter,
            with_parent_chapters=True,
            candidates=candidates,
        )
        for chapter in _chapters[:-1]:
            _, elt = self.reader.find_element_by_index(chapter["element"])
            if elt:
                paras.append(elt)
        return paras


class IncomeDistributionAbstractChecker(RightChapterAbstractChecker):
    # 基金的收益与分配
    LABEL = "schema_825"
    NAME = "合同摘要-收益分配"

    # 摘要章节
    DIGEST_CHAPTERS = [ChapterPattern.CHAPTER_FUND_CONTRACT_DIGEST_INCOME_ALLOCATION]
    # 正文章节
    CONTRACT_CHAPTERS = [ChapterPattern.CHAPTER_FUND_INCOME_ALLOCATION]

    PARENT_CHAPTER_PATTERNS = []


class CostRevenueAbstractChecker(IncomeDistributionAbstractChecker):
    # 基金的费用与税收
    LABEL = "schema_826"
    NAME = "合同摘要-费用与税收"

    # 摘要章节
    DIGEST_CHAPTERS = [ChapterPattern.CHAPTER_FUND_CONTRACT_DIGEST_COST_REVENUE]
    # 正文章节
    CONTRACT_CHAPTERS = [ChapterPattern.CHAPTER_FUND_BASIC_COST_REVENUE]


class InvestAbstractChecker(IncomeDistributionAbstractChecker):
    # 基金的投资
    LABEL = "schema_827"
    NAME = "合同摘要-基金的投资"

    # 合同摘要->基金的投资 -> 投资目标/投资范围/投资限制-组合限制/投资限制-禁止行为
    DIGEST_CHAPTERS = [
        ChapterRule(
            [
                CatalogsPattern.FUND_CONTRACT_DIGEST,
                CatalogsPattern.FUND_INVEST,
                CatalogsPattern.FUND_INVEST_SCOPE_TARGET,
            ]
        ).convert2dict(),
        ChapterRule(
            [
                CatalogsPattern.FUND_CONTRACT_DIGEST,
                CatalogsPattern.FUND_INVEST,
                CatalogsPattern.FUND_INVEST_SCOPE_INVESTMENT,
            ]
        ).convert2dict(),
        ChapterRule(
            [
                CatalogsPattern.FUND_CONTRACT_DIGEST,
                CatalogsPattern.FUND_INVEST,
                CatalogsPattern.FUND_INVEST_SCOPE_INVESTMENT_RESTRICTION,
                CatalogsPattern.FUND_INVEST_SCOPE_COMBINATORIAL_RESTRICTION,
            ]
        ).convert2dict(),
        ChapterRule(
            [
                CatalogsPattern.FUND_CONTRACT_DIGEST,
                CatalogsPattern.FUND_INVEST,
                CatalogsPattern.FUND_INVEST_SCOPE_INVESTMENT_RESTRICTION,
                CatalogsPattern.FUND_INVEST_SCOPE_FORBIDDING_ACT,
            ]
        ).convert2dict(),
    ]

    # 正文：基金的投资 -> 投资目标/投资范围/投资限制-组合限制/投资限制-禁止行为
    CONTRACT_CHAPTERS = [
        ChapterRule([CatalogsPattern.FUND_INVEST, CatalogsPattern.FUND_INVEST_SCOPE_TARGET]).convert2dict(),
        ChapterRule([CatalogsPattern.FUND_INVEST, CatalogsPattern.FUND_INVEST_SCOPE_INVESTMENT]).convert2dict(),
        ChapterRule(
            [
                CatalogsPattern.FUND_INVEST,
                CatalogsPattern.FUND_INVEST_SCOPE_INVESTMENT_RESTRICTION,
                CatalogsPattern.FUND_INVEST_SCOPE_COMBINATORIAL_RESTRICTION,
            ]
        ).convert2dict(),
        ChapterRule(
            [
                CatalogsPattern.FUND_INVEST,
                CatalogsPattern.FUND_INVEST_SCOPE_INVESTMENT_RESTRICTION,
                CatalogsPattern.FUND_INVEST_SCOPE_FORBIDDING_ACT,
            ]
        ).convert2dict(),
    ]


class AssetValuationAbstractChecker(IncomeDistributionAbstractChecker):
    # 基金资产估值
    LABEL = "schema_829"
    NAME = "合同摘要-估值方法"

    # 合同摘要->基金资产估值-> 估值对象/估值方法
    DIGEST_CHAPTERS = [
        ChapterRule(
            [
                CatalogsPattern.FUND_CONTRACT_DIGEST,
                CatalogsPattern.FUND_ASSET_VALUATION_OR_VALUE_CALCULATION_ANNOUNCEMENT_MODE,
                CatalogsPattern.FUND_ASSET_VALUATION_OBJECT,
            ]
        ).convert2dict(),
        ChapterRule(
            [
                CatalogsPattern.FUND_CONTRACT_DIGEST,
                CatalogsPattern.FUND_ASSET_VALUATION_OR_VALUE_CALCULATION_ANNOUNCEMENT_MODE,
                CatalogsPattern.FUND_ASSET_VALUATION_METHOD,
            ]
        ).convert2dict(),
    ]
    # 正文：基金资产估值-> 估值对象/估值方法
    CONTRACT_CHAPTERS = [
        ChapterRule(
            [
                CatalogsPattern.FUND_ASSET_VALUATION,
                CatalogsPattern.FUND_ASSET_VALUATION_OBJECT,
            ]
        ).convert2dict(),
        ChapterRule(
            [
                CatalogsPattern.FUND_ASSET_VALUATION,
                CatalogsPattern.FUND_ASSET_VALUATION_METHOD,
            ]
        ).convert2dict(),
    ]


class PropertyLiquidationAbstractChecker(IncomeDistributionAbstractChecker):
    # 基金合同的变更、终止与基金财产的清算
    LABEL = "schema_830"
    NAME = "合同摘要-合同变更、终止、清算"

    # 摘要章节
    DIGEST_CHAPTERS = [ChapterPattern.CHAPTER_FUND_CONTRACT_DIGEST_PROPERTY_LIQUIDATION]
    # 正文章节
    CONTRACT_CHAPTERS = [ChapterPattern.CHAPTER_FUND_PROPERTY_LIQUIDATION]


class ApplicationLawAbstractChecker(IncomeDistributionAbstractChecker):
    # 争议的处理
    LABEL = "schema_831"
    NAME = "合同摘要-争议的处理"

    # 摘要章节
    DIGEST_CHAPTERS = [ChapterPattern.CHAPTER_FUND_CONTRACT_DIGEST_PROCESSING_APPLICATION_LAW]
    # 正文章节
    CONTRACT_CHAPTERS = [ChapterPattern.CHAPTER_FUND_PROCESSING_APPLICATION_LAW]


class ShareHolderAbstractChecker(IncomeDistributionAbstractChecker):
    # 基金份额持有人大会召集、议事及表决的程序和规则
    LABEL = "schema_833"
    NAME = "合同摘要-份额持有人大会"

    # 摘要章节
    DIGEST_CHAPTERS = [ChapterPattern.CHAPTER_FUND_CONTRACT_DIGEST_SHARE_HOLDER]
    # 正文章节
    CONTRACT_CHAPTERS = [ChapterPattern.CHAPTER_FUND_SHARE_HOLDER]


class InvestmentStrategyChecker(PublicFundSchemaChecker):
    # 基金的投资
    LABEL = "schema_835"
    RELATED_NAME = "基金的投资"
    NAME = "投资策略与投资范围匹配"
    SCHEMA_FIELDS = ["投资策略", "基金投资范围"]
    CONTRACT_CONTENT = [
        "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
        "三、投资策略",
        "(清晰明确，投资逻辑清晰)",
    ]

    P_IGNORE_STRATEGY = PatternCollection(r"(?:大类|类别)资产|资产配置")
    P_STRATEGY_TAIL = PatternCollection(r"(?:(?:投资)?(?:策略|配置|管理){1,2})")

    def check(self):
        result = self.init_result()
        self.check_schema_fields(result)
        if result.suggestion:
            return result
        strategy_answer = self.manager.get("投资策略")
        # syllabus chapter key
        extra_keys = ("element", "level", "children")
        strategy_chapters = get_chapter_info_by_outline(self.reader, strategy_answer.outlines, extra_keys)
        if not strategy_chapters:
            result.reasons.append(MatchFailedItem(reason_text="投资策略章节为空"))
            result.suggestion.append("请补充“投资策略”章节")
            return result
        # 拆分投资策略且忽略大类资产
        suggestions = []
        scope_values = self.manager.classification_mapping.get(PublicFundClassifyName.INVESTMENT_SCOPE, [])
        is_exist = True
        child_chapters = self.reader.syllabus_reader.get_child_syllabus(
            strategy_chapters[-1], level=strategy_chapters[-1]["level"] + 1
        )
        if not child_chapters:
            result.reasons.append(IgnoreConditionItem(reason_text="投资策略中缺少小标题，无法进行比对"))
            return result

        for chapter in child_chapters:
            clean_title = self.P_STRATEGY_TAIL.sub("", clean_txt(chapter["title"]))
            if self.P_IGNORE_STRATEGY.nexts(clean_title):
                continue
            for scope in InvestmentScopeEnum.members().values():
                p_scope: PatternCollection = scope.values[-1]
                if not p_scope.nexts(clean_title) or scope in scope_values:
                    continue
                is_exist = False
                break
            if not is_exist:
                result.reasons.append(MatchFailedItem("投资策略出现了投资范围中未出现的投资品种"))
                suggestions.append("投资策略中小标题的投资品种，要与投资范围包含的品种需匹配，请检查投资策略中投资品种")
                break
        else:
            result.is_compliance = True
            result.reasons.append(MatchSuccessItem("投资策略中的投资品种与投资范围一致"))
        result.suggestion = "\n".join(suggestions)
        return result


class ContractValidityAbstractChecker(IncomeDistributionAbstractChecker):
    # 合同存放地和投资者获取方式
    LABEL = "schema_832"
    NAME = "合同摘要-合同存放地和投资者获取方式"

    EXIST_COMPLIANCE = True

    # 摘要章节
    DIGEST_CHAPTERS = [ChapterPattern.CHAPTER_FUND_CONTRACT_DIGEST_CONTRACT_VALIDITY]
    # 正文章节
    CONTRACT_CHAPTERS = [ChapterPattern.CHAPTER_FUND_CONTRACT_VALIDITY]


class NetAssetValueAbstractChecker(IncomeDistributionAbstractChecker):
    # 资产净值
    LABEL = "schema_828"
    NAME = "合同摘要-资产净值"

    # 合同摘要->基金资产净值
    DIGEST_CHAPTERS = [
        ChapterRule(
            [
                CatalogsPattern.FUND_CONTRACT_DIGEST,
                CatalogsPattern.FUND_DIGEST_VALUE_CALCULATION_ANNOUNCEMENT_MODE,
                CatalogsPattern.FUND_PROPERTY_TOTAL_ASSETS,
            ]
        ).convert2dict(),
        ChapterRule(
            [
                CatalogsPattern.FUND_CONTRACT_DIGEST,
                CatalogsPattern.FUND_DIGEST_VALUE_CALCULATION_ANNOUNCEMENT_MODE,
                CatalogsPattern.FUND_PROPERTY_NET_ASSET_VALUE,
            ]
        ).convert2dict(),
        ChapterRule(
            [
                CatalogsPattern.FUND_CONTRACT_DIGEST,
                CatalogsPattern.FUND_DIGEST_VALUE_CALCULATION_ANNOUNCEMENT_MODE,
                CatalogsPattern.FUND_VALUE_CALCULATION_ANNOUNCEMENT_MODE,
            ]
        ).convert2dict(),
    ]
    # 正文: 基金的财产->资产总值/资产净值
    # 正文: 信息披露->基金净值信息的公告方式
    CONTRACT_CHAPTERS = [
        ChapterRule([CatalogsPattern.FUND_PROPERTY, CatalogsPattern.FUND_PROPERTY_TOTAL_ASSETS]).convert2dict(),
        ChapterRule([CatalogsPattern.FUND_PROPERTY, CatalogsPattern.FUND_PROPERTY_NET_ASSET_VALUE]).convert2dict(),
        ChapterRule(
            [CatalogsPattern.FUND_INFORMATION_DISCLOSURE, CatalogsPattern.FUND_VALUE_CALCULATION_ANNOUNCEMENT_MODE]
        ).convert2dict(),
    ]


class FundFeesPaymentChecker(PublicFundSchemaChecker):
    LABEL = "schema_836"
    RELATED_NAME = "基金费用与税收"
    NAME = "管理费、托管费、销售服务费表达规范"
    SCHEMA_FIELDS = [
        "基金管理费-计提方法、计提标准和支付方式",
        "基金托管费-计提方法、计提标准和支付方式",
        "客户服务费用-计提方法、计提标准和支付方式",
    ]

    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2043
    R_STATEMENT_1 = r"{name}每日计[算提].按月支付.*?管理人.?核"
    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2042
    R_STATEMENT_2 = (
        r"{name}每日计[算提].*?逐日累计.*?(?:(?:(?:管理人|托管人)[^{punctuation}]*?){{2}}核.*?支[取付]给?(?:(?:基金)?管理人)?"
        r"|管理人向(?:基金)?托管人[^{punctuation}]*?划?[付款]{{1,2}})"
    )
    R_STATEMENT_3 = (
        r"{name}每日计[算提].*?(?:(?:(?:管理人|托管人)[^{punctuation}]*?){{2}}核.*?"
        r"|管理人向(?:基金)?托管人[^{punctuation}]*?划?[付款]{{1,2}}).*?(?:不可抗力|财产无法变现).?导?致使?无法按时"
    )

    FUND_FEES_SCHEMA_FIELDS = {
        "基金管理费": SCHEMA_FIELDS[0],
        "基金托管费": SCHEMA_FIELDS[1],
        "销售服务费": SCHEMA_FIELDS[2],
    }

    FUND_FEES_STATEMENTS = {
        "基金管理费": {
            "statement_1": PatternCollection(R_STATEMENT_1.format(**{"name": "管理费"})),
            "statement_2": PatternCollection(R_STATEMENT_2.format(**{"name": "管理费", "punctuation": R_PUNCTUATION})),
            "statement_3": PatternCollection(R_STATEMENT_3.format(**{"name": "管理费", "punctuation": R_PUNCTUATION})),
        },
        "基金托管费": {
            "statement_1": PatternCollection(R_STATEMENT_1.format(**{"name": "托管费"})),
            "statement_2": PatternCollection(R_STATEMENT_2.format(**{"name": "托管费", "punctuation": R_PUNCTUATION})),
            "statement_3": PatternCollection(R_STATEMENT_3.format(**{"name": "托管费", "punctuation": R_PUNCTUATION})),
        },
        "销售服务费": {
            "statement_1": PatternCollection(R_STATEMENT_1.format(**{"name": "服务费"})),
            "statement_2": PatternCollection(R_STATEMENT_2.format(**{"name": "服务费", "punctuation": R_PUNCTUATION})),
            "statement_3": PatternCollection(R_STATEMENT_3.format(**{"name": "服务费", "punctuation": R_PUNCTUATION})),
        },
    }

    FUND_FEES_PAYMENT = {
        "基金管理费": PatternCollection(
            R_FEES_PAYMENT_DATE.format(**{"name": "管理费", "punctuation": R_PUNCTUATION, "num": R_CN_NUMBER})
        ),
        "基金托管费": PatternCollection(
            R_FEES_PAYMENT_DATE.format(**{"name": "托管费", "punctuation": R_PUNCTUATION, "num": R_CN_NUMBER})
        ),
        "销售服务费": PatternCollection(
            R_FEES_PAYMENT_DATE.format(**{"name": "服务费", "punctuation": R_PUNCTUATION, "num": R_CN_NUMBER})
        ),
    }

    def check(self):
        result = self.init_result()
        fees_statements = defaultdict()
        payments = []
        not_found_statements = []
        for name, statement_dict in self.FUND_FEES_STATEMENTS.items():
            _, paragraphs = get_paragraphs_by_schema_fields(
                self.reader, self.manager, [self.FUND_FEES_SCHEMA_FIELDS[name]]
            )
            is_match = False
            for s_type, pattern in statement_dict.items():
                for para in paragraphs:
                    clean_content = clean_txt(para["text"])
                    if pattern.nexts(clean_content):
                        is_match = True
                        fees_statements[name] = s_type
                        if s_type == "statement_2":
                            val = None
                            if res := self.FUND_FEES_PAYMENT[name].nexts(clean_content):
                                val = str(NumberUtil.cn_number_2_digit(res.group("val")))
                            payments.append(val)
                        break
                if is_match:
                    break
            if not is_match:
                not_found_statements.append(name)
        if not_found_statements:
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2036#note_320756
            result.reasons.append(
                MatchFailedItem(reason_text=f"表达不规范，未找到“{'、'.join(not_found_statements)}”支付方式的表述")
            )
            if len(not_found_statements) > 1:
                return result
        suggestions = []
        content = "、".join(fees_statements.keys())
        if len(set(fees_statements.values())) != 1:
            result.reasons.append(MatchFailedItem(reason_text=f"{content}支付方式的表述不规范"))
            suggestions.append(f"请检查{content}的支付方式")
        else:
            result.reasons.append(MatchFailedItem(reason_text=f"{content}支付方式的表述一致"))
            result.is_compliance = True
            if payments:
                if all(item is not None for item in payments) and len(set(payments)) == 1:
                    result.reasons.append(MatchFailedItem(reason_text=f"{content}支付时间的表述一致"))
                else:
                    result.is_compliance = False
                    result.reasons.append(MatchFailedItem(reason_text=f"{content}支付时间的表述不规范"))
                    suggestions.append(f"请检查{content}的支付时间")

        if len(fees_statements) != 3:
            result.is_compliance = False

        result.suggestion = "\n".join(suggestions)
        return result


class InvestmentRatioChecker(PublicFundSchemaChecker):
    LABEL = "schema_815"
    RELATED_NAME = "基金的投资"
    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2230#note_331955
    NAME = "投资组合比例-一般规定"
    SCHEMA_FIELDS = [("投资比例", [TemplateConditional.FUND_TYPE_INVESTMENT_RATIO_CONDITIONS])]
    FROM = [
        "公开募集证券投资基金运作管理办法（证监会令第104号2014年7月7日）",
        "公开募集证券投资基金运作指引第2号——基金中基金指引（证监会公告〔2016〕20号2016年9月11日）",
    ]
    CONTRACT_CONTENT = [
        "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
        "基金的投资组合比例为：",
        "【股票型 / 混合型 / 债券型】",
        "【指数型】投资于标的指数成份股和备选成份股的比例不得低于基金资产净值的90 %。（指数增强型基金及债券指数型基金除外）",
    ]
    ORIGIN = [
        "第三十条 基金合同和基金招募说明书应当按照下列规定载明基金的类别：",
        "（一）百分之八十以上的基金资产投资于股票的，为股票基金；",
        "（二）百分之八十以上的基金资产投资于债券的，为债券基金；",
        "（三）仅投资于货币市场工具的，为货币市场基金；",
        "（四）百分之八十以上的基金资产投资于其他基金份额的，为基金中基金；",
        "（五）投资于股票、债券、货币市场工具或其他基金份额，并且股票投资、债券投资、基金投资的比例不符合第（一）项、第（二）项、第（四）项规定的，为混合基金；",
        "（六）中国证监会规定的其他基金类别。",
        "第三十一条",
        "基金名称显示投资方向的，应当有百分之八十以上的非现金基金资产属于投资方向确定的内容。",
        "第三条",
        "基金中基金是指，将80 % 以上的基金资产投资于经中国证监会依法核准或注册的公开募集的基金份额的基金。",
        "投资于标的指数成份股和备选成份股的比例不得低于基金资产净值的90%。（指数增强型基金及债券指数型基金除外）",
    ]

    TEMPLATES_CONF_FOR_EDITING = [
        {
            "name": TemplateName.EDITING_NAME,
            "content_title": TemplateName.EDITING_TITLE,
            "chapter": ChapterPattern.CHAPTER_FUND_INVESTMENT_RESTRICTION,
            "content_condition": ContentConditional.PROPORTION_OF_FUND_PORTFOLIO,
            "items": [item],
        }
        for item in [
            {
                "conditions": [TemplateConditional.FUND_TYPE_ENHANCE_INDEX],
                "items": [
                    "本基金投资于股票资产的比例不低于基金资产的{X4}，投资于标的指数成份股、备选成份股的资产的比例不低于非现金基金资产的80%；"
                ],
            },
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1577#note_320906
            # 指数型/债券指数/股票指数
            {
                "conditions": [
                    TemplateConditional.FUND_TYPE_BOND_OR_STOCK_INDEX,
                    TemplateConditional.FUND_TYPE_ENHANCE_INDEX_NO,
                ],
                "items": ["投资于标的指数成份股和备选成份股的比例不得低于基金资产净值的90%。"],
            },
            {
                "conditions": [TemplateConditional.FUND_TYPE_BOND_INDEX],
                "items": [
                    "本基金投资于债券资产的比例不低于基金资产的{X5}，本基金投资于标的指数成份券、备选成份券的比例不低于本基金非现金基金资产的80%；"
                ],
            },
            {
                "conditions": [TemplateConditional.FUND_TYPE_BOND],
                "items": [
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2206#note_331935
                    [
                        "本基金投资于债券资产的比例不低于基金资产的{X0}；",
                        "债券资产投资占基金资产的比例不低于{X0}；",
                    ]
                ],
            },
            {
                "conditions": [TemplateConditional.FUND_TYPE_STOCK],
                "items": [
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2206#note_331935
                    [
                        "本基金投资于股票资产的比例不低于基金资产的{X0}；",
                        "股票资产投资占基金资产的比例不低于{X0}；",
                        "本基金股票资产占基金资产的比例为80%-{X1}；",
                    ]
                ],
            },
            {
                "conditions": [TemplateConditional.FUND_MIXTURE],
                "items": [
                    [
                        "股票资产的比例为基金资产的{X2}-{X3}；",
                        "本基金股票资产占基金资产的比例为{X2}-{X3}；",
                    ],
                ],
            },
            {
                "conditions": [TemplateConditional.SIDE_TYPE_FOF],
                "items": [
                    [
                        "本基金投资于经中国证监会依法核准或注册公开募集的基金份额的比例不少于基金资产的{X7}；",
                        "投资于证券投资基金的比例不低于基金资产的{X6}；",
                        "投资于证券投资基金的资产不低于基金资产的{X6}；",
                    ],
                ],
            },
            {
                "conditions": [TemplateConditional.SPECIAL_TYPE_LINKED_FUND],
                "items": [
                    "投资于目标ETF的比例不低于基金资产净值的90%；",
                ],
            },
            {
                "conditions": [TemplateConditional.FUND_TYPE_STOCK_INDEX],
                "items": [
                    "投资于标的指数成份股和备选成份股的资产比例不低于非现金基金资产的80%且不低于基金资产净值的90%；",
                ],
            },
        ]
    ]

    DR_TEMPLATES_CONF_FOR_EDITING = [
        {
            "name": TemplateName.EDITING_NAME,
            "content_title": TemplateName.EDITING_TITLE,
            "chapter": ChapterPattern.CHAPTER_FUND_INVESTMENT_RESTRICTION,
            "content_condition": ContentConditional.PROPORTION_OF_FUND_PORTFOLIO,
            "items": [item],
        }
        for item in [
            {
                "conditions": [TemplateConditional.FUND_TYPE_ENHANCE_INDEX],
                "items": [
                    "本基金投资于股票及存托凭证资产的比例不低于基金资产的{X4}，投资于标的指数成份股、备选成份股的资产的比例不低于非现金基金资产的80%；"
                ],
            },
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1577#note_320906
            # 指数型/债券指数/股票指数
            {
                "conditions": [
                    TemplateConditional.FUND_TYPE_BOND_OR_STOCK_INDEX,
                    TemplateConditional.FUND_TYPE_ENHANCE_INDEX_NO,
                ],
                "items": ["投资于标的指数成份股和备选成份股的比例不得低于基金资产净值的90%。"],
            },
            {
                "conditions": [TemplateConditional.FUND_TYPE_BOND_INDEX],
                "items": [
                    "本基金投资于债券资产的比例不低于基金资产的{X5}，本基金投资于标的指数成份券、备选成份券的比例不低于本基金非现金基金资产的80%；"
                ],
            },
            {
                "conditions": [TemplateConditional.FUND_TYPE_BOND],
                "items": [
                    [
                        "本基金投资于债券资产的比例不低于基金资产的{X0}；",
                        "债券资产投资占基金资产的比例不低于{X0}；",
                    ]
                ],
            },
            {
                "conditions": [TemplateConditional.FUND_TYPE_STOCK],
                "items": [
                    [
                        "本基金投资于股票及存托凭证资产的比例不低于基金资产的{X0}；",
                        "股票及存托凭证资产投资占基金资产的比例不低于{X0}；",
                        "本基金股票及存托凭证资产占基金资产的比例为80%-{X1}；",
                    ]
                ],
            },
            {
                "conditions": [TemplateConditional.FUND_MIXTURE],
                "items": [
                    [
                        "股票及存托凭证资产的比例为基金资产的{X2}-{X3}；",
                        "本基金股票及存托凭证资产占基金资产的比例为{X2}-{X3}；",
                    ],
                ],
            },
            {
                "conditions": [TemplateConditional.SIDE_TYPE_FOF],
                "items": [
                    [
                        "本基金投资于经中国证监会依法核准或注册公开募集的基金份额的比例不少于基金资产的{X7}；",
                        "投资于证券投资基金的比例不低于基金资产的{X6}；",
                        "投资于证券投资基金的资产不低于基金资产的{X6}；",
                    ],
                ],
            },
            {
                "conditions": [TemplateConditional.SPECIAL_TYPE_LINKED_FUND],
                "items": [
                    "投资于目标ETF的比例不低于基金资产净值的90%；",
                ],
            },
            {
                "conditions": [TemplateConditional.FUND_TYPE_STOCK_INDEX],
                "items": [
                    "投资于标的指数成份股和备选成份股的资产比例不低于非现金基金资产的80%且不低于基金资产净值的90%；",
                ],
            },
        ]
    ]

    def check(self):
        result = self.init_result()
        self.check_schema_fields(result)
        if result.suggestion:
            return result
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2022#note_320814
        # 存托凭证： “股票”转换为“股票及存托凭证”
        template_items = self.TEMPLATES_CONF_FOR_EDITING
        if self.manager.verify_condition([TemplateConditional.SPECIAL_TYPE_DR]):
            template_items = self.DR_TEMPLATES_CONF_FOR_EDITING
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
            "from": "",
            "origin": "",
            "templates": [],
        }
        reasons = []
        suggestions = []
        for template_item in template_items:
            template["templates"] = [template_item]
            condition_checker.TEMPLATES = [template]
            if not (check_res := condition_checker.check()):
                continue
            check_res = check_res[0]
            # 所有的范文模板均参与检查，忽略不满足条件的模板对象，其余均保留
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2022#note_319450
            conditions: list[TemplateRelation]
            if conditions := template_item["items"][0].get("conditions"):
                condition_relation: FundTypeRelation = conditions[0].values[0]
                reason_text = f"未找到“{condition_relation.value.value}”的范文内容"
                for reason in check_res.reasons:
                    # 特殊处理：模板中需要替换的内容如果未找到，不通过原因为“请补充***”,只对该类型进行处理
                    if not isinstance(reason, (MatchReasonItem, ConflictReasonItem)) and reason.reason_text.startswith(
                        "请补充"
                    ):
                        reason.reason_text = reason_text + f"；{reason.reason_text}"
                reasons.extend(check_res.reasons)
            if check_res.suggestion:
                suggestions.append(check_res.suggestion)

        if not reasons:
            return

        if any(not isinstance(reason, IgnoreConditionItem) for reason in reasons):
            reasons = [reason for reason in reasons if not isinstance(reason, IgnoreConditionItem)]
        match_reasons = [reason for reason in reasons if isinstance(reason, (MatchReasonItem, ConflictReasonItem))]
        reasons = self.filter_same_reason(reasons)
        match_reasons = self.filter_same_reason(match_reasons)
        result.reasons = match_reasons if match_reasons else reasons
        result.suggestion = "\n\n".join(suggestions)
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2022#note_323295
        result.is_compliance = all(isinstance(reason, MatchReasonItem) for reason in reasons)
        return result


class FundTypeChecker(PublicFundSchemaChecker):
    LABEL = "template_812"
    RELATED_NAME = "基金的基本情况"
    NAME = "基金的类别"
    SCHEMA_FIELDS = ["基金的类别、类型"]
    FROM = "公开募集证券投资基金运作管理办法（证监会令第104号 2014年7月7日）"
    ORIGIN = [
        "第三十条基金合同和基金招募说明书应当按照下列规定载明基金的类别：",
        "（一）百分之八十以上的基金资产投资于股票的，为股票基金；",
        "（二）百分之八十以上的基金资产投资于债券的，为债券基金；",
        "（三）仅投资于货币市场工具的，为货币市场基金；",
        "（四）百分之八十以上的基金资产投资于其他基金份额的，为基金中基金；",
        "（五）投资于股票、债券、货币市场工具或其他基金份额，并且股票投资、债券投资、基金投资的比例不符合第（一）项、第（二）项、第（四）项规定的，为混合基金；",
        "（六）中国证监会规定的其他基金类别。",
    ]
    CONTRACT_CONTENT = [
        "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
        "二、基金的类别",
        "股票型 / 债券型 / 混合型证券投资基金",
    ]
    TEMPLATES = [
        {
            "name": TemplateName.LAW_NAME,
            "content_title": TemplateName.LAW_TITLE,
            "chapter": ChapterPattern.CHAPTER_FUND_TYPES_OF_FUNDS,
            "min_ratio": 0.2,
            "items": [
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2089#note_323184
                {
                    "single_optional": [
                        {
                            "conditions": [TemplateConditional.FUND_TYPE_STOCK],
                            "items": [
                                "二、基金的类别",
                                "股票型证券投资基金",
                            ],
                        },
                        {
                            "conditions": [TemplateConditional.FUND_TYPE_BOND],
                            "items": [
                                "二、基金的类别",
                                "债券型证券投资基金",
                            ],
                        },
                        {
                            "conditions": [TemplateConditional.FUND_MIXTURE],
                            "items": [
                                "二、基金的类别",
                                "混合型证券投资基金",
                            ],
                        },
                    ]
                },
            ],
        },
        {
            "name": TemplateName.EDITING_NAME,
            "content_title": TemplateName.EDITING_TITLE,
            "chapter": ChapterPattern.CHAPTER_FUND_TYPES_OF_FUNDS,
            "min_ratio": 0.2,
            "items": [
                {
                    "single_optional": [
                        {
                            "conditions": [TemplateConditional.SIDE_TYPE_MONEY],
                            "items": [
                                "货币市场基金",
                            ],
                        },
                        {
                            "conditions": [TemplateConditional.SPECIAL_TYPE_LINKED_FUND],
                            "items": [
                                "ETF联接基金",
                            ],
                        },
                        {
                            "conditions": [TemplateConditional.FUND_TYPE_STOCK_INDEX],
                            "items": [
                                "股票型证券投资基金",
                            ],
                        },
                        {
                            "conditions": [TemplateConditional.FUND_TYPE_BOND_INDEX],
                            "items": [
                                "债券型证券投资基金",
                            ],
                        },
                        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2089#note_321926
                        {
                            "conditions": [TemplateConditional.FUND_TYPE_COMMODITIES_FUTURES_INDEX],
                            "items": [
                                "商品期货型证券投资基金",
                            ],
                        },
                    ]
                },
            ],
        },
    ]

    def check(self):
        fund_type_mode = self.manager.get(self.SCHEMA_FIELDS[0])
        if not fund_type_mode.value:
            result = self.init_result()
            suggestion = "请添加基金的类别、类型"
            result.is_compliance = False
            result.reasons = [MatchFailedItem(reason_text="基金的类别、类型不能为空")]
            result.suggestion = suggestion
            return result

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
            "contract_content": self.CONTRACT_CONTENT,
        }
        condition_checker.TEMPLATES = [template]
        result = condition_checker.check()
        if not result:
            return
        result = result[0]
        result.rule_type = self.RULE_TYPE
        miss_content = not any(reason.matched for reason in result.reasons)
        matched, reasons = condition_checker.after_match_template(template, result.reasons, miss_content)
        result.reasons = reasons
        result.is_compliance = matched
        return result
