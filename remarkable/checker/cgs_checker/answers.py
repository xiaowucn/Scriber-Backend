from functools import cached_property

import attrs

from remarkable.checker.answers import AnswerManager
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.plugins.cgs.common.chapters_patterns import (
    R_CONJUNCTION,
    CatalogsPattern,
    CustodyCatalogsPattern,
)
from remarkable.plugins.cgs.common.fund_classification import (
    AssetClassifyName,
    AssetFundTypeEnum,
    AssetManagementOperateModeEnum,
    AssetProjectNameEnum,
    CustodyClassifyName,
    CustodySettleAccountsMode,
    DisclosureEnum,
    FundStockBourseNameEnum,
    FundSubscriptionSubChapterEnum,
    FundTypeEnum,
    InvestmentScopeEnum,
    MoldNameEnum,
    OperateModeEnum,
    PublicFundClassifyName,
    RelationEnum,
    ShareCategoryEnum,
    SpecialTypeEnum,
)
from remarkable.plugins.cgs.common.patterns_util import (
    P_ASSET_STOCK_RIGHT,
    P_BOURSE_SH,
    P_BOURSE_SZ,
    P_CUSTODY_STOCK,
    P_EMPLOY_INVESTMENT_ADVISER,
    P_NON_STANDARD_INVESTMENT,
    P_OPERATE_MODE_CLOSE,
    P_WITHOUT_HOLDER_MEETING,
)
from remarkable.plugins.cgs.common.template_condition import (
    AllMatchRelation,
    FundTypeRelation,
    TemplateRelation,
)

P_STOCK_EXCHANGE = PatternCollection([r"(?:上海|深圳)证券交易所", r"[上深]交所"])
P_SIDE_POCKET = PatternCollection(
    [
        rf"侧袋机制的?实施[{R_CONJUNCTION}]投资运作安排$",
        "(?:实施|侧袋机制){2}期间的?(?:基金)?资产估值",
    ]
)
P_FUND_BASIC_INFO_PORTION = PatternCollection([r"基金份额的?类别(?:设置)?$"])

P_FUND_SUBSCRIPTION_CONVERT = PatternCollection([r"转换$"])
P_FUND_SUBSCRIPTION_PERIOD_INVEST = PatternCollection([r"定期定额投资(?:计划)?$"])
P_FUND_SUBSCRIPTION_TRANSFER_CUSTODY = PatternCollection([r"转托管$"])
P_FUND_SUBSCRIPTION_NON_TRANSACTION_TRANSFER = PatternCollection([r"非交易过户"])

VALID_CUSTODY_INVESTMENT_SCOPES = (
    InvestmentScopeEnum.HK_STOCK,
    InvestmentScopeEnum.CREDIT,
    InvestmentScopeEnum.STOCK_INDEX_FEATURES,
    InvestmentScopeEnum.DEBT_FEATURES,
    InvestmentScopeEnum.COMMODITY_FEATURES,
    InvestmentScopeEnum.STOCK_FEATURES,
    InvestmentScopeEnum.RE_FINANCE,
    InvestmentScopeEnum.ABS,
    InvestmentScopeEnum.DR,
    InvestmentScopeEnum.FINANCING,
    InvestmentScopeEnum.SECURITIES_LENDING,
    InvestmentScopeEnum.NCD,
)


@attrs.define(slots=False)
class CGSAnswerManager(AnswerManager):
    @cached_property
    def classification_mapping(self):
        """
        OPERATE_MODE = "运作方式"
        FUND_TYPE = "投资对象"
        LISTED_TRANSACTION = "上市交易"
        SPECIAL_TYPE = "特殊类别"
        SIDE_POCKET = "侧袋机制"
        SHARE_CLASSIFY = "份额分类"
        INVESTMENT_SCOPE = "投资范围"
        """
        if MoldNameEnum.PUBLIC_FUND.value in self.mold.name:
            return {
                PublicFundClassifyName.OPERATE_MODE: self.check_operate_mode(),
                PublicFundClassifyName.FUND_TYPE: self.check_fund_type(),
                PublicFundClassifyName.LISTED_TRANSACTION: self.check_disclosure_chapter(
                    [CatalogsPattern.FUND_LISTED_LISTED_TRANSACTION.pattern], P_STOCK_EXCHANGE
                ),
                PublicFundClassifyName.SPECIAL_TYPE: self.check_special_type(),
                PublicFundClassifyName.SIDE_POCKET: self.check_disclosure_chapter(
                    [CatalogsPattern.FUND_INVEST.pattern], P_SIDE_POCKET
                ),
                PublicFundClassifyName.SHARE_CLASSIFY: self.check_disclosure_chapter(
                    [CatalogsPattern.FUND_BASIC_INFORMATION.pattern], P_FUND_BASIC_INFO_PORTION
                ),
                PublicFundClassifyName.INVESTMENT_SCOPE: self.check_investment_scope(
                    PublicFundClassifyName.answer_field_map()[PublicFundClassifyName.INVESTMENT_SCOPE][0],
                ),
                PublicFundClassifyName.FUND_SUBSCRIPTION: self.check_fund_subscription_chapter(),
                PublicFundClassifyName.STOCK_BOURSE: self.check_stock_bourse(),
                PublicFundClassifyName.SHARE_CATEGORY: self.check_share_category_content(),
            }
        if MoldNameEnum.PUBLIC_CUSTODY.value in self.mold.name:
            return {
                CustodyClassifyName.OPERATE_MODE: self.check_custody_operate_mode(),
                CustodyClassifyName.FUND_TYPE: self.check_custody_fund_type(),
                CustodyClassifyName.SPECIAL_TYPE: self.check_custody_special_type(),
                CustodyClassifyName.SIDE_POCKET: self.check_disclosure_chapter(
                    [CustodyCatalogsPattern.FUND_NET_ASSET_VALUE_CALCULATION_ACCOUNTING.pattern], P_SIDE_POCKET
                ),
                CustodyClassifyName.INVESTMENT_SCOPE: self.check_investment_scope(
                    CustodyClassifyName.answer_field_map()[CustodyClassifyName.INVESTMENT_SCOPE][0],
                    VALID_CUSTODY_INVESTMENT_SCOPES,
                ),
                CustodyClassifyName.SETTLE_ACCOUNTS_MODE: self.check_settle_accounts_mode(),
            }
        if MoldNameEnum.ASSET_MANAGEMENT.value in self.mold.name:
            return {
                # 单一或集合
                AssetClassifyName.PROJECT_NAME: self.check_project_name(),
                # 类别：FOF、权益、固定收益、期货和衍生品、混合
                AssetClassifyName.PROJECT_TYPE: self.check_project_type(),
                # 有无持有人大会
                AssetClassifyName.PROJECT_GENERAL_MEETING: self.check_holder_meeting_chapter(),
                # 有无投资顾问
                AssetClassifyName.INVESTMENT_ADVISER: self.check_investment_adviser(),
                # 是否为封闭式
                AssetClassifyName.OPERATE_MODE: self.check_asset_operate_mode(),
                # 是否为非标投资
                AssetClassifyName.NON_STANDARD_INVESTMENT: self.check_is_non_standard_investment(),
                # 是否有股权
                AssetClassifyName.STOCK_RIGHT: self.check_is_exist_stock_right(),
            }
        return {}

    def check_share_category_content(self):
        correct_types = []
        _, paragraphs = self.reader.find_paragraphs_by_chapters([CatalogsPattern.FUND_PARAPHRASE.pattern])
        for category_type in ShareCategoryEnum.members().values():
            for paragraph in paragraphs:
                p_category: PatternCollection = category_type.values[-1]
                if p_category.nexts(clean_txt(paragraph["text"])):
                    correct_types.append(category_type)
        return correct_types

    def check_settle_accounts_mode(self):
        for pattern in [
            CustodyCatalogsPattern.FUND_CUSTODY_PROPERTY.pattern,
            CustodyCatalogsPattern.FUND_INSTRUCTIONS_SEND_VERIFY_EXECUTE.pattern,
        ]:
            _, paragraphs = self.reader.find_paragraphs_by_chapters([pattern])
            for paragraph in paragraphs:
                if "证券资金账户" in clean_txt(paragraph["text"]):
                    return [CustodySettleAccountsMode.SECURITIES_TRADER_MODE]
        return [CustodySettleAccountsMode.TRUSTEE_MODE]

    def check_stock_bourse(self):
        answer = self.get(PublicFundClassifyName.answer_field_map()[PublicFundClassifyName.STOCK_BOURSE][0]).value or ""
        if P_BOURSE_SH.nexts(answer):
            return [FundStockBourseNameEnum.SHANGHAI]
        if P_BOURSE_SZ.nexts(answer):
            return [FundStockBourseNameEnum.SHENZHEN]
        return []

    def check_fund_subscription_chapter(self):
        sub_chapters = set()
        root = self.reader.find_chapter_by_patterns([CatalogsPattern.FUND_SUBSCRIPTION.pattern])
        if not root:
            return []
        for chapter in self.reader.syllabus_reader.get_child_syllabus(root[-1]):
            clean_title = clean_txt(chapter["title"])
            if P_FUND_SUBSCRIPTION_CONVERT.nexts(clean_title):
                sub_chapters.add(FundSubscriptionSubChapterEnum.CONVERT)
            elif P_FUND_SUBSCRIPTION_PERIOD_INVEST.nexts(clean_title):
                sub_chapters.add(FundSubscriptionSubChapterEnum.PERIOD_INVEST)
            elif P_FUND_SUBSCRIPTION_TRANSFER_CUSTODY.nexts(clean_title):
                sub_chapters.add(FundSubscriptionSubChapterEnum.TRANSFER_CUSTODY)
            elif P_FUND_SUBSCRIPTION_NON_TRANSACTION_TRANSFER.nexts(clean_title):
                sub_chapters.add(FundSubscriptionSubChapterEnum.NON_TRANSACTION_TRANSFER)
        return list(sub_chapters)

    def check_operate_mode(self):
        operate_mode_answer = (
            self.get(PublicFundClassifyName.answer_field_map()[PublicFundClassifyName.OPERATE_MODE][0]).value or ""
        )
        fund_name_answer = (
            self.get(PublicFundClassifyName.answer_field_map()[PublicFundClassifyName.SPECIAL_TYPE][0]).value or ""
        )
        res = []
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1837
        # https://mm.paodingai.com/cheftin/pl/fufki7d9ejgwfy6tpj5uysbyko
        if OperateModeEnum.OPEN.values[-1].nexts(operate_mode_answer):
            res = [OperateModeEnum.OPEN]
        if OperateModeEnum.REGULAR_OPEN.values[-1].nexts(fund_name_answer):
            res.append(OperateModeEnum.REGULAR_OPEN)
        if OperateModeEnum.CLOSE.values[-1].nexts(fund_name_answer):
            if OperateModeEnum.OPEN in res:
                res.remove(OperateModeEnum.OPEN)
            else:
                res.append(OperateModeEnum.CLOSE)
        if OperateModeEnum.INITIATE.values[-1].nexts(fund_name_answer):
            res.append(OperateModeEnum.INITIATE)
        return res

    def check_custody_operate_mode(self):
        # 开放式：基金名称不包含：封闭
        # 封闭式：基金名称包含：封闭
        # 发起式：基金名称包含：发起式
        # 定期开放式：基金名称包含：定期开放（规则中未明确区分的开放式，默认包含定期开放式）
        operate_mode_answer = (
            self.get(CustodyClassifyName.answer_field_map()[CustodyClassifyName.OPERATE_MODE][0]).value or ""
        )
        res = set()
        if OperateModeEnum.REGULAR_OPEN.values[-1].nexts(operate_mode_answer):
            res.add(OperateModeEnum.REGULAR_OPEN)
            res.add(OperateModeEnum.OPEN)
        if OperateModeEnum.CLOSE.values[-1].nexts(operate_mode_answer):
            res.add(OperateModeEnum.CLOSE)
        if OperateModeEnum.INITIATE.values[-1].nexts(operate_mode_answer):
            res.add(OperateModeEnum.INITIATE)
        if not OperateModeEnum.CLOSE.values[-1].nexts(operate_mode_answer):
            res.add(OperateModeEnum.OPEN)
        return list(res)

    def check_fund_type(self):
        type_field, name_field = PublicFundClassifyName.answer_field_map()[PublicFundClassifyName.FUND_TYPE]
        fund_type_answer = self.get(type_field).value or ""
        fund_name_answer = self.get(name_field).value or ""
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1255#note_301017
        if "货币基金" in fund_name_answer or "货币市场基金" in fund_name_answer:
            return [FundTypeEnum.MONEY]
        if "混合型" in fund_type_answer:
            return [FundTypeEnum.MIXTURE]

        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1392#note_308142
        fund_types = []
        if is_index := any(
            val in fund_name_answer for val in ("指数", "期货交易型开放式证券投资基金", "黄金交易型开放式证券投资基金")
        ):
            fund_types.append(FundTypeEnum.INDEX)
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1881#note_310925
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2067#note_322275
        if "指数增强" in fund_name_answer:
            fund_types.append(FundTypeEnum.ENHANCE_INDEX)

        if "股票" in fund_type_answer:
            if is_index:
                fund_types.append(FundTypeEnum.STOCK_INDEX)
            fund_types.append(FundTypeEnum.STOCK)
        elif "债券" in fund_type_answer:
            if is_index:
                fund_types.append(FundTypeEnum.BOND_INDEX)
            fund_types.append(FundTypeEnum.BOND)
        elif "商品期货" in fund_type_answer:
            if is_index:
                fund_types.append(FundTypeEnum.COMMODITIES_FUTURES_INDEX)
            fund_types.append(FundTypeEnum.COMMODITIES_FUTURES)
        return fund_types

    def check_custody_fund_type(self):
        # 货币基金：基金名称包含：货币市场基金、货币基金
        # 债券型：基金名称包含：债
        # 混合型：基金名称包含：混合
        # 指数型：基金名称包含：指数
        # 指数增强型：基金名称包含：指数增强
        # 股票型：基金名称包含：股票
        # 股票指数型：基金名称包含指数；同时包含沪深/上证/中证/深证/创业板/中小企业/恒生/A股/股票/北证/国证/中创
        # 债券指数型：基金名称包含指数；同时包含中债/债
        fund_name_answer = (
            self.get(CustodyClassifyName.answer_field_map()[CustodyClassifyName.FUND_TYPE][0]).value or ""
        )
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1255#note_301017
        if "货币基金" in fund_name_answer or "货币市场基金" in fund_name_answer:
            return [FundTypeEnum.MONEY]
        if "混合" in fund_name_answer:
            return [FundTypeEnum.MIXTURE]

        fund_types = []
        if is_index := any(
            val in fund_name_answer for val in ("指数", "期货交易型开放式证券投资基金", "黄金交易型开放式证券投资基金")
        ):
            fund_types.append(FundTypeEnum.INDEX)
        if "指数增强" in fund_name_answer:
            fund_types.append(FundTypeEnum.ENHANCE_INDEX)
        elif P_CUSTODY_STOCK.nexts(fund_name_answer):
            if is_index:
                fund_types.append(FundTypeEnum.STOCK_INDEX)
            fund_types.append(FundTypeEnum.STOCK)
        elif "债" in fund_name_answer:
            if is_index:
                fund_types.append(FundTypeEnum.BOND_INDEX)
            fund_types.append(FundTypeEnum.BOND)
        return fund_types

    def check_investment_scope(self, schema_field, custody_investment_scopes=None):
        answer = self.get(schema_field).value or ""
        if not answer:
            return []
        correct_types = []
        for fund_attr in InvestmentScopeEnum.members().values():
            if custody_investment_scopes and fund_attr not in custody_investment_scopes:
                continue
            p_attr: PatternCollection = fund_attr.values[-1]
            if p_attr.nexts(answer):
                correct_types.append(fund_attr)
        return correct_types

    def check_special_type(self):
        answer = self.get(PublicFundClassifyName.answer_field_map()[PublicFundClassifyName.SPECIAL_TYPE][0]).value or ""
        if not answer:
            return []
        res = set()
        for special_type in SpecialTypeEnum.members().values():
            p_attr: PatternCollection = special_type.values[-1]
            if p_attr.nexts(answer):
                res.add(special_type)
                if special_type in [SpecialTypeEnum.FEATURES_ETF, SpecialTypeEnum.GOLD_ETF]:
                    res.add(SpecialTypeEnum.ETF)
                elif special_type == SpecialTypeEnum.GOLD_ETF_LINKED:
                    res.add(SpecialTypeEnum.LINKED_FUND)
        return list(res)

    def check_custody_special_type(self):
        answer = self.get(CustodyClassifyName.answer_field_map()[CustodyClassifyName.SPECIAL_TYPE][0]).value or ""
        if not answer:
            return []
        res = set()
        for special_type in SpecialTypeEnum.members().values():
            # 托管无分级基金、黄金ETF联接
            if special_type in (SpecialTypeEnum.GOLD_ETF_LINKED, SpecialTypeEnum.CLASSIFICATION):
                continue
            p_attr: PatternCollection = special_type.values[-1]
            if p_attr.nexts(answer):
                res.add(special_type)
                if special_type in [SpecialTypeEnum.FEATURES_ETF, SpecialTypeEnum.GOLD_ETF]:
                    res.add(SpecialTypeEnum.ETF)
                elif special_type == SpecialTypeEnum.GOLD_ETF_LINKED:
                    res.add(SpecialTypeEnum.LINKED_FUND)
        return list(res)

    def check_project_name(self):
        project_name_answer = (
            self.get(AssetClassifyName.answer_field_map()[AssetClassifyName.PROJECT_NAME][0]).value or ""
        )
        for project_type in AssetProjectNameEnum.members().values():
            p_attr: PatternCollection = project_type.values[-1]
            if p_attr.nexts(project_name_answer):
                return [project_type]
        return []

    def check_project_type(self):
        project_type_answer = (
            self.get(AssetClassifyName.answer_field_map()[AssetClassifyName.PROJECT_TYPE][0]).value or ""
        )
        ret = []
        for project_type in AssetFundTypeEnum.members().values():
            p_attr: PatternCollection = project_type.values[-1]
            if p_attr.nexts(project_type_answer):
                ret.append(project_type)
        return ret

    def check_holder_meeting_chapter(self):
        # 无大会: 章节“资产管理计划的参与、退出与转让”或“份额持有人大会及日常机构”包含：“本计划不设份额持有人大会及日常机构”或者“本计划不设置份额持有人大会及日常机构”
        # 反之则有大会
        chapters = []
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2012#note_339664
        for pattern in (
            CatalogsPattern.ASSET_MANAGE_PLAN_PARTICIPATION_WITHDRAWAL_TRANSFER.pattern,
            CatalogsPattern.GENERAL_ASSEMBLY_DAILY_INSTITUTIONS.pattern,
        ):
            chapters.extend(self.reader.find_sylls_by_pattern([pattern]))
        if not chapters:
            return [DisclosureEnum.NO]
        for chapter in chapters:
            for index in range(*chapter["range"]):
                elt_type, element = self.reader.find_element_by_index(index)
                if (
                    elt_type == "PARAGRAPH"
                    and not element.get("fragment")
                    and P_WITHOUT_HOLDER_MEETING.nexts(clean_txt(element["text"]))
                ):
                    return [DisclosureEnum.NO]
        return [DisclosureEnum.YES]

    def check_investment_adviser(self):
        # 投顾:投资顾问章节约定聘请xx公司为投资顾问
        investment_adviser_answer = (
            self.get(AssetClassifyName.answer_field_map()[AssetClassifyName.INVESTMENT_ADVISER][0]).value or ""
        )
        if P_EMPLOY_INVESTMENT_ADVISER.nexts(clean_txt(investment_adviser_answer)):
            return [DisclosureEnum.YES]
        return [DisclosureEnum.NO]

    def check_asset_operate_mode(self):
        operate_mode_answer = (
            self.get(AssetClassifyName.answer_field_map()[AssetClassifyName.OPERATE_MODE][0]).value or ""
        )
        if P_OPERATE_MODE_CLOSE.nexts(operate_mode_answer):
            return [AssetManagementOperateModeEnum.CLOSE]
        return []

    def check_is_non_standard_investment(self):
        # 是否为非标投资
        investment_answer = (
            self.get(AssetClassifyName.answer_field_map()[AssetClassifyName.NON_STANDARD_INVESTMENT][0]).value or ""
        )
        if P_NON_STANDARD_INVESTMENT.nexts(clean_txt(investment_answer)):
            return [DisclosureEnum.YES]
        return [DisclosureEnum.NO]

    def check_is_exist_stock_right(self):
        # 是否有股权
        investment_answer = self.get(AssetClassifyName.answer_field_map()[AssetClassifyName.STOCK_RIGHT][0]).value or ""
        if P_ASSET_STOCK_RIGHT.nexts(clean_txt(investment_answer)):
            return [DisclosureEnum.YES]
        return [DisclosureEnum.NO]

    def verify_condition(self, template_conditions: list[TemplateRelation] | None):
        if not template_conditions:
            return True

        # 多个conditions需全部满足条件
        for condition in template_conditions:
            default_values = self.classification_mapping.get(condition.name, [])
            # 同一个条件内的多个值满足一个即可
            for val_condition in condition.values:
                if isinstance(val_condition, FundTypeRelation) and self.verify_relation(
                    val_condition, default_values=default_values
                ):
                    break
                elif isinstance(val_condition, AllMatchRelation) and all(
                    self.verify_relation(value, default_values=default_values) for value in val_condition.values
                ):
                    break
            else:
                return False
        return True

    def verify_relation(self, relation: FundTypeRelation, default_values=None):
        if not relation:
            return True

        attr_values = (relation.name and self.classification_mapping.get(relation.name, [])) or default_values or []
        if relation.relation == RelationEnum.EQUAL and relation.value in attr_values:
            return True
        if relation.relation == RelationEnum.UNEQUAL and relation.value not in attr_values:
            return True
        return False
