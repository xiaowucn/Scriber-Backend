from dataclasses import dataclass
from types import MappingProxyType

from aenum import Enum, MultiValueEnum

from remarkable.common.pattern import PatternCollection
from remarkable.plugins.cgs.common.patterns_util import P_OPERATE_MODE_CLOSE, R_CONJUNCTION


class MixinEnum(Enum):
    @classmethod
    def members(cls) -> MappingProxyType:
        return MappingProxyType(cls._member_map_)


class MoldNameEnum(MixinEnum):
    PUBLIC_FUND = "公募-基金合同"
    PUBLIC_CUSTODY = "公募-托管协议"
    ASSET_MANAGEMENT = "公募-资产管理合同"


@dataclass
class PublicFundClassifyName:
    OPERATE_MODE = "运作方式"
    FUND_TYPE = "基金类型"
    LISTED_TRANSACTION = "上市交易"
    SPECIAL_TYPE = "特殊类别"
    SIDE_POCKET = "侧袋机制"
    SHARE_CLASSIFY = "份额分类"
    INVESTMENT_SCOPE = "基金投资范围"
    # 申购与赎回章节是否存在指定子标题
    FUND_SUBSCRIPTION = "申购与赎回章节"
    # 交易所名称
    STOCK_BOURSE = "交易所"
    # 结算模式
    SETTLE_ACCOUNTS_MODE = "结算模式"
    # 释义章节披露的份额分类类型 A/C类/...
    SHARE_CATEGORY = "份额类别"

    @classmethod
    def answer_field_map(cls) -> dict:
        return {
            cls.OPERATE_MODE: ["运作方式"],
            cls.FUND_TYPE: ["基金的类别、类型", "基金名称"],
            cls.SPECIAL_TYPE: ["基金名称"],
            cls.INVESTMENT_SCOPE: ["基金投资范围"],
            cls.STOCK_BOURSE: ["上市交易所"],
        }


class RelationEnum(MultiValueEnum, MixinEnum):
    EQUAL = 1, "等于"
    UNEQUAL = 2, "不等于"
    LTE = 3, "小于等于"
    GTE = 4, "大于等于"
    LT = 5, "小于"
    GT = 6, "大于"


class ContentValueTypeEnum(MixinEnum):
    STR = "str"
    NUMBER = "number"
    PERCENTAGE = "percentage"


class OperateModeEnum(MultiValueEnum, MixinEnum):
    REGULAR_OPEN = "定期开放式", PatternCollection(r"定期开放")
    OPEN = "开放式", PatternCollection(r"(?<!定期)开放式")
    CLOSE = "封闭式", P_OPERATE_MODE_CLOSE
    INITIATE = "发起式", PatternCollection(r"发起式")


class DisclosureEnum(Enum):
    YES = "是"
    NO = "否"


class FundTypeEnum(Enum):
    """
    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1255#note_301017
    基金名称包含：货币基金、货币市场基金
    基金类别：债券型
    基金类别：混合型
    基金名称包含：指数 默认包含指数增强、股票指数、债券指数
    指数增强型: 指数型的一种类别。基金名称包含：指数增强）；
    股票指数型: 指数型的一种类别。基金名称包含指数；基金类别：股票型）
    债券指数型: 指数型的一种类别。基金名称包含指数；基金类别：债券型）
    商品期货指数型: 指数型的一种类别。基金名称包含指数；基金类别：商品期货型）
    基金类别：股票型
    """

    MONEY = "货币基金"
    BOND = "债券型"
    MIXTURE = "混合型"
    ENHANCE_INDEX = "指数增强型"
    STOCK_INDEX = "股票指数型"
    BOND_INDEX = "债券指数型"
    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2089#note_322550
    COMMODITIES_FUTURES_INDEX = "商品期货指数型"
    COMMODITIES_FUTURES = "商品期货型"
    STOCK = "股票型"
    INDEX = "指数型"


class SpecialTypeEnum(MultiValueEnum, MixinEnum):
    """
    港股:    基金名称包含：港股   # 名称包含港股是特殊场景，在规则790中要和投资范围的港股配合使用，可以和本特殊类型的其他类型共存
    FOF:    基金名称包含：FOF、基金中基金
    LOF:    上市型开放式基金，基金名称包含：LOF
    商品期货ETF:    基金名称包含：期货交易型开放式指数证券投资基金
    黄金ETF联接:  基金名称包含：黄金交易型开放式证券投资基金联接基金
    黄金ETF:  基金名称包含：黄金交易型开放式指数证券投资基金
    分级基金:  基金名称包含：分级
    联接基金:   基金名称包含：联接
    ETF:    基金名称包含：交易型开放式指数证券投资基金
    """

    HK_STOCK = "港股", PatternCollection(r"港股")
    FOF = "FOF", PatternCollection(r"FOF|基金中基金")
    LOF = "LOF", PatternCollection(r"LOF")
    FEATURES_ETF = "商品期货ETF", PatternCollection(r"期货交易型开放式(指数)?证券投资基金")
    GOLD_ETF_LINKED = "黄金ETF联接", PatternCollection(r"黄金交易型开放式(指数)?证券投资基金联接基金")
    GOLD_ETF = "黄金ETF", PatternCollection("黄金交易型开放式(指数)?证券投资基金(?!联接)")
    CLASSIFICATION = "分级基金", PatternCollection(r"分级")
    LINKED_FUND = "联接基金", PatternCollection(r"联接")
    # 交易型开放式指数证券投资基金和联接 同时出现，只处理联接基金, 所以优先处理联接基金
    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1825#note_307531
    ETF = "ETF", PatternCollection(r"交易型开放式指数证券投资基金")


class InvestmentScopeEnum(MultiValueEnum, MixinEnum):
    """
    不互斥
    投资范围包含：港股
    投资范围包含：信用衍生品
    投资范围包含：股指期货
    投资范围包含：国债期货
    投资范围包含：商品期货
    投资范围包含：股票期权
    投资范围包含：转融通、转融通证券出借
    投资范围包含：资产支持证券
    投资范围包含：存托凭证
    投资范围包含：融资
    投资范围包含：融券
    投资范围包含：科创板
    投资范围包含：权证
    投资范围包含：同业存单
    投资范围包含：股票
    投资范围包含：债券
    投资范围包含：期货合约
    """

    HK_STOCK = "港股通", PatternCollection(r"港股")
    CREDIT = "信用衍生品", PatternCollection(r"信用衍生品")
    STOCK_INDEX_FEATURES = "股指期货", PatternCollection(r"股指期货")
    DEBT_FEATURES = "国债期货", PatternCollection(r"国债期货")
    COMMODITY_FEATURES = "商品期货", PatternCollection(r"商品期货")
    STOCK_FEATURES = "股票期权", PatternCollection(r"股票期权")
    RE_FINANCE = "转融通", PatternCollection(r"转融通")
    ABS = "资产支持证券", PatternCollection(r"资产支持证券")
    DR = "存托凭证", PatternCollection(r"存托凭证")
    FINANCING = "融资", PatternCollection(r"融资")
    SECURITIES_LENDING = "融券", PatternCollection(r"融券")
    STAR_MARKET = "科创板", PatternCollection(r"科创板")
    WARRANT = "权证", PatternCollection(r"权证")
    NCD = "同业存单", PatternCollection(r"同业存单")
    STOCK = "股票", PatternCollection(r"股票(?!期权)")
    BOND = "债券", PatternCollection(r"债券")
    FUTURES_CONTRACT = "期货合约", PatternCollection(r"期货合约")


class FundSubscriptionSubChapterEnum(Enum):
    """
    申购与赎回章节子章节
    """

    CONVERT = "转换"
    PERIOD_INVEST = "定期定额投资"
    TRANSFER_CUSTODY = "转托管"
    NON_TRANSACTION_TRANSFER = "非交易过户"


class FundStockBourseNameEnum(Enum):
    """
    证券交易所名词
    """

    SHANGHAI = "上交所"
    SHENZHEN = "深交所"


class CustodySettleAccountsMode(Enum):
    """
    托管协议结算模式
    """

    SECURITIES_TRADER_MODE = "券商结算模式"
    TRUSTEE_MODE = "托管人结算模式"


class ShareCategoryEnum(MultiValueEnum, MixinEnum):
    """
    释义章节披露的份额分类类型 A/C类/...
    """

    MODE_A = "A", PatternCollection(r"A类(?:基金)?份额")
    MODE_C = "C", PatternCollection(r"C类(?:基金)?份额")


@dataclass
class CustodyClassifyName:
    # 托管协议 基金分类
    OPERATE_MODE = PublicFundClassifyName.OPERATE_MODE  # 运作方式
    FUND_TYPE = PublicFundClassifyName.FUND_TYPE  # 基金类型
    SPECIAL_TYPE = PublicFundClassifyName.SPECIAL_TYPE  # 特殊类别
    SIDE_POCKET = PublicFundClassifyName.SIDE_POCKET  # 侧袋机制
    INVESTMENT_SCOPE = PublicFundClassifyName.INVESTMENT_SCOPE  # 基金投资范围
    SETTLE_ACCOUNTS_MODE = "结算模式"

    @classmethod
    def answer_field_map(cls) -> dict:
        return {
            cls.OPERATE_MODE: ["基金名称"],
            cls.FUND_TYPE: ["基金名称"],
            cls.SPECIAL_TYPE: ["基金名称"],
            cls.INVESTMENT_SCOPE: ["托管人对管理人的监督"],
        }


@dataclass
class AssetClassifyName:
    PROJECT_NAME = "计划名称"
    PROJECT_TYPE = "计划类别"
    PROJECT_GENERAL_MEETING = "持有人大会"
    OPERATE_MODE = "运作方式"
    INVESTMENT_ADVISER = "投资顾问"
    NON_STANDARD_INVESTMENT = "非标投资"
    STOCK_RIGHT = "股权"

    @classmethod
    def answer_field_map(cls) -> dict:
        return {
            cls.PROJECT_TYPE: ["计划的类别、类型"],
            cls.PROJECT_NAME: ["计划名称"],
            cls.OPERATE_MODE: ["运作方式"],
            cls.INVESTMENT_ADVISER: ["投资顾问"],
            cls.NON_STANDARD_INVESTMENT: ["计划投资范围"],
            cls.STOCK_RIGHT: ["计划投资范围"],
        }


class AssetProjectNameEnum(MultiValueEnum, MixinEnum):
    """
    资产管理合同
    单一:	基金名称包含“单一”
    集合:	基金名称包含“集合”
    """

    SINGLE = "单一", PatternCollection(r"单一")
    POOLED = "集合", PatternCollection(r"集合")


class AssetFundTypeEnum(MultiValueEnum, MixinEnum):
    """
    FOF:	基金的类别包含“基金中基金”或“FOF”
    权益类:	基金的类别包含“权益类”
    固定收益类:	基金的类别包含“固定收益类”
    期货和衍生品类:	基金的类别包含“期货和衍生品类”
    混合类:	基金的类别包含“混合类”
    """

    FOF = "FOF", PatternCollection(r"基金中基金|FOF")
    EQUITIES = "权益类", PatternCollection(r"权益类")
    FIXED_INCOME_CATEGORY = "固定收益类", PatternCollection(r"固定收益类")
    FUTURES_AND_DERIVATIVES = "期货和衍生品类", PatternCollection(rf"期货[{R_CONJUNCTION}]衍生品类")
    MIXED_CLASS = "混合类", PatternCollection(r"混合类")


class AssetManagementOperateModeEnum(MixinEnum):
    CLOSE = "封闭式"
