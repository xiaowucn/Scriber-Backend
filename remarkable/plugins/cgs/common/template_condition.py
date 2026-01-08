from dataclasses import dataclass

from aenum import Enum

from remarkable.common.convert_number_util import NumberUtil, PercentageUtil
from remarkable.common.pattern import PatternCollection
from remarkable.plugins.cgs.common.fund_classification import (
    AssetClassifyName,
    AssetFundTypeEnum,
    AssetManagementOperateModeEnum,
    AssetProjectNameEnum,
    ContentValueTypeEnum,
    CustodySettleAccountsMode,
    DisclosureEnum,
    FundStockBourseNameEnum,
    FundSubscriptionSubChapterEnum,
    FundTypeEnum,
    InvestmentScopeEnum,
    OperateModeEnum,
    PublicFundClassifyName,
    RelationEnum,
    ShareCategoryEnum,
    SpecialTypeEnum,
)
from remarkable.plugins.cgs.common.patterns_util import (
    R_CN_NUMBER,
    R_CONJUNCTION,
    R_FEES_PAYMENT_DATE,
    R_INTERVAL,
    R_MULTIPLICATION_SYMBOL,
    R_NOT_CONJUNCTION_PUNCTUATION,
    R_PERCENTAGE,
    R_PERCENTAGE_IGNORE_UNIT,
    R_PUNCTUATION,
)


@dataclass
class FundTypeRelation:
    value: Enum
    name: str = ""
    relation: RelationEnum = RelationEnum.EQUAL


@dataclass
class AllMatchRelation:
    values: list[FundTypeRelation]  # 全匹配, 关系为与


@dataclass
class TemplateRelation:
    name: str
    values: list[FundTypeRelation | AllMatchRelation]  # 同一个name所对应的多个value, 关系为或


@dataclass
class TemplateName:
    LAW_NAME = "法规"
    LAW_TITLE = "法规条款"
    EDITING_NAME = "范文"
    EDITING_TITLE = "合同范文"


@dataclass
class TemplateConditional:
    # 有份额分类
    SHARE_CLASSIFY_YES = TemplateRelation(
        name=PublicFundClassifyName.SHARE_CLASSIFY, values=[FundTypeRelation(value=DisclosureEnum.YES)]
    )
    # 无份额分类
    SHARE_CLASSIFY_NO = TemplateRelation(
        name=PublicFundClassifyName.SHARE_CLASSIFY, values=[FundTypeRelation(value=DisclosureEnum.NO)]
    )
    # 上市交易
    LISTED_TRANSACTION_YES = TemplateRelation(
        name=PublicFundClassifyName.LISTED_TRANSACTION, values=[FundTypeRelation(value=DisclosureEnum.YES)]
    )
    # 非上市交易
    LISTED_TRANSACTION_NO = TemplateRelation(
        name=PublicFundClassifyName.LISTED_TRANSACTION, values=[FundTypeRelation(value=DisclosureEnum.NO)]
    )
    # LOF
    SPECIAL_TYPE_LOF = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.LOF)],
    )
    # 非LOF
    SPECIAL_TYPE_LOF_NO = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(
                name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.LOF, relation=RelationEnum.UNEQUAL
            )
        ],
    )
    # ETF
    SPECIAL_TYPE_ETF = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.ETF)],
    )

    # 非ETF
    SPECIAL_TYPE_ETF_NO = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(
                name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.ETF, relation=RelationEnum.UNEQUAL
            )
        ],
    )

    # 黄金ETF
    SPECIAL_TYPE_GOLD_ETF = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.GOLD_ETF)],
    )

    # 非黄金ETF
    SPECIAL_TYPE_GOLD_ETF_NO = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(
                name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.GOLD_ETF, relation=RelationEnum.UNEQUAL
            )
        ],
    )

    # 黄金ETF联接
    SPECIAL_TYPE_GOLD_ETF_LINKED = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.GOLD_ETF_LINKED)],
    )

    # 商品期货ETF
    SPECIAL_TYPE_FEATURES_ETF = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.FEATURES_ETF)],
    )

    # ETF/封闭式
    SPECIAL_TYPE_ETF_OR_CLOSE = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.ETF),
            FundTypeRelation(name=PublicFundClassifyName.OPERATE_MODE, value=OperateModeEnum.CLOSE),
        ],
    )

    # ETF/封闭式/LOF/分级
    SPECIAL_TYPE_ETF_LOF_CLOSE_CLASSIFY = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.ETF),
            FundTypeRelation(name=PublicFundClassifyName.OPERATE_MODE, value=OperateModeEnum.CLOSE),
            FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.CLASSIFICATION),
            FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.LOF),
        ],
    )

    # ETF/LOF/上市
    SPECIAL_TYPE_ETF_LOF_TRANSACTION_YES = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.ETF),
            FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.LOF),
            FundTypeRelation(name=PublicFundClassifyName.LISTED_TRANSACTION, value=DisclosureEnum.YES),
        ],
    )

    # ETF/LOF
    SPECIAL_TYPE_ETF_LOF = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.ETF),
            FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.LOF),
        ],
    )

    # 发起式
    SPECIAL_TYPE_INITIATE = TemplateRelation(
        name=PublicFundClassifyName.OPERATE_MODE, values=[FundTypeRelation(value=OperateModeEnum.INITIATE)]
    )
    # 非发起式
    SPECIAL_TYPE_INITIATE_NO = TemplateRelation(
        name=PublicFundClassifyName.OPERATE_MODE,
        values=[FundTypeRelation(value=OperateModeEnum.INITIATE, relation=RelationEnum.UNEQUAL)],
    )

    # 非定期开放式
    SPECIAL_REGULAR_OPEN_NO = TemplateRelation(
        name=PublicFundClassifyName.OPERATE_MODE,
        values=[FundTypeRelation(value=OperateModeEnum.REGULAR_OPEN, relation=RelationEnum.UNEQUAL)],
    )

    # 指数型
    FUND_TYPE_INDEX = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(value=FundTypeEnum.INDEX)],
    )

    # 非指数型
    FUND_TYPE_INDEX_NO = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(value=FundTypeEnum.INDEX, relation=RelationEnum.UNEQUAL)],
    )

    # 股票指数型
    FUND_TYPE_STOCK_INDEX = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(value=FundTypeEnum.STOCK_INDEX)],
    )

    # 债券指数型
    FUND_TYPE_BOND_INDEX = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(value=FundTypeEnum.BOND_INDEX)],
    )

    # 指数增强型
    FUND_TYPE_ENHANCE_INDEX = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(value=FundTypeEnum.ENHANCE_INDEX)],
    )

    # 商品期货指数型
    FUND_TYPE_COMMODITIES_FUTURES_INDEX = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(value=FundTypeEnum.COMMODITIES_FUTURES_INDEX)],
    )

    # 指数增强型/非指数型
    FUND_TYPE_ENHANCE_INDEX_OR_NO_INDEX = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(value=FundTypeEnum.ENHANCE_INDEX),
            FundTypeRelation(value=FundTypeEnum.INDEX, relation=RelationEnum.UNEQUAL),
        ],
    )

    # 指数型/债券指数/股票指数
    FUND_TYPE_BOND_OR_STOCK_INDEX = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(value=FundTypeEnum.INDEX),
            FundTypeRelation(value=FundTypeEnum.STOCK_INDEX),
            FundTypeRelation(value=FundTypeEnum.BOND_INDEX),
        ],
    )

    # 指数型/债券/股票/混合/FOF/联接
    FUND_TYPE_INVESTMENT_RATIO_CONDITIONS = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(value=FundTypeEnum.INDEX),
            FundTypeRelation(value=FundTypeEnum.STOCK),
            FundTypeRelation(value=FundTypeEnum.BOND),
            FundTypeRelation(value=FundTypeEnum.MIXTURE),
            FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.FOF),
            FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.LINKED_FUND),
        ],
    )

    # 非指数增强型
    FUND_TYPE_ENHANCE_INDEX_NO = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(value=FundTypeEnum.ENHANCE_INDEX, relation=RelationEnum.UNEQUAL)],
    )

    # 股票型
    FUND_TYPE_STOCK = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(value=FundTypeEnum.STOCK)],
    )

    # 债券型
    FUND_TYPE_BOND = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(value=FundTypeEnum.BOND)],
    )

    # 混合型
    FUND_MIXTURE = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(value=FundTypeEnum.MIXTURE)],
    )

    # 股票型/债券型
    FUND_TYPE_STOCK_BOND = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(value=FundTypeEnum.STOCK),
            FundTypeRelation(value=FundTypeEnum.BOND),
        ],
    )

    # 股票型/混合型
    FUND_TYPE_STOCK_MIXTURE = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(value=FundTypeEnum.STOCK),
            FundTypeRelation(value=FundTypeEnum.MIXTURE),
        ],
    )

    # 股票型/混合型/债券型
    FUND_TYPE_STOCK_MIXTURE_BOND = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(value=FundTypeEnum.STOCK),
            FundTypeRelation(value=FundTypeEnum.MIXTURE),
            FundTypeRelation(value=FundTypeEnum.BOND),
        ],
    )

    # 股票型/混合型/债券型/指数型
    FUND_TYPE_STOCK_MIXTURE_BOND_INDEX = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(value=FundTypeEnum.STOCK),
            FundTypeRelation(value=FundTypeEnum.MIXTURE),
            FundTypeRelation(value=FundTypeEnum.BOND),
            FundTypeRelation(value=FundTypeEnum.INDEX),
        ],
    )

    # 股票型/混合型/开放式股票型指数基金/ETF/ETF联接基金
    FUND_TYPE_STOCK_MIXTURE_ETF_LINKED = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            AllMatchRelation(
                values=[
                    FundTypeRelation(
                        name=PublicFundClassifyName.FUND_TYPE, value=FundTypeEnum.INDEX, relation=RelationEnum.UNEQUAL
                    ),
                    FundTypeRelation(name=PublicFundClassifyName.FUND_TYPE, value=FundTypeEnum.STOCK),
                ]
            ),
            FundTypeRelation(value=FundTypeEnum.MIXTURE),
            AllMatchRelation(
                values=[
                    FundTypeRelation(name=PublicFundClassifyName.OPERATE_MODE, value=OperateModeEnum.OPEN),
                    FundTypeRelation(name=PublicFundClassifyName.FUND_TYPE, value=FundTypeEnum.STOCK_INDEX),
                ]
            ),
            FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.ETF),
            FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.LINKED_FUND),
        ],
    )

    # 非债券指数型
    FUND_TYPE_BOND_INDEX_NO = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(value=FundTypeEnum.BOND_INDEX, relation=RelationEnum.UNEQUAL),
        ],
    )

    # 非股票指数型
    FUND_TYPE_STOCK_INDEX_NO = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(value=FundTypeEnum.STOCK_INDEX, relation=RelationEnum.UNEQUAL),
        ],
    )

    # 联接基金
    SPECIAL_TYPE_LINKED_FUND = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.LINKED_FUND)],
    )

    # 非联接基金
    SPECIAL_TYPE_LINKED_FUND_NO = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(
                name=PublicFundClassifyName.SPECIAL_TYPE,
                value=SpecialTypeEnum.LINKED_FUND,
                relation=RelationEnum.UNEQUAL,
            )
        ],
    )

    # 存托凭证
    SPECIAL_TYPE_DR = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[FundTypeRelation(value=InvestmentScopeEnum.DR)],
    )

    # 资产支持证券
    SPECIAL_TYPE_ABS = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[FundTypeRelation(value=InvestmentScopeEnum.ABS)],
    )

    # 股指期货/国债期货/股票期权
    SPECIAL_TYPE_STOCK_INDEX_DEBT_FEATURES = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[
            FundTypeRelation(value=InvestmentScopeEnum.STOCK_INDEX_FEATURES),
            FundTypeRelation(value=InvestmentScopeEnum.DEBT_FEATURES),
            FundTypeRelation(value=InvestmentScopeEnum.STOCK_FEATURES),
        ],
    )

    # 股指期货/国债期货/股票期权/商品期货
    SPECIAL_TYPE_STOCK_INDEX_DEBT_COMMODITY_FEATURES = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[
            FundTypeRelation(value=InvestmentScopeEnum.STOCK_INDEX_FEATURES),
            FundTypeRelation(value=InvestmentScopeEnum.DEBT_FEATURES),
            FundTypeRelation(value=InvestmentScopeEnum.STOCK_FEATURES),
            FundTypeRelation(value=InvestmentScopeEnum.COMMODITY_FEATURES),
        ],
    )

    # 股指期货
    SPECIAL_TYPE_STOCK_INDEX_FEATURES = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[FundTypeRelation(value=InvestmentScopeEnum.STOCK_INDEX_FEATURES)],
    )

    # 国债期货
    SPECIAL_TYPE_DEBT_FEATURES = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[FundTypeRelation(value=InvestmentScopeEnum.DEBT_FEATURES)],
    )

    # 股票期权
    SPECIAL_TYPE_STOCK_FEATURES = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[FundTypeRelation(value=InvestmentScopeEnum.STOCK_FEATURES)],
    )

    # 投资范围-港股通
    INVESTMENT_SCOPE_HK_STOCK = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[FundTypeRelation(value=InvestmentScopeEnum.HK_STOCK)],
    )

    # 投资范围-非港股通
    INVESTMENT_SCOPE_HK_STOCK_NO = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[FundTypeRelation(value=InvestmentScopeEnum.HK_STOCK, relation=RelationEnum.UNEQUAL)],
    )

    # 基金名称-港股通
    SPECIAL_TYPE_HK_STOCK = TemplateRelation(
        name=PublicFundClassifyName.SPECIAL_TYPE,
        values=[FundTypeRelation(value=SpecialTypeEnum.HK_STOCK)],
    )

    # 基金名称-非港股通
    SPECIAL_TYPE_HK_STOCK_NO = TemplateRelation(
        name=PublicFundClassifyName.SPECIAL_TYPE,
        values=[FundTypeRelation(value=SpecialTypeEnum.HK_STOCK, relation=RelationEnum.UNEQUAL)],
    )

    # 投资范围-信用衍生品
    SPECIAL_TYPE_CREDIT = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[FundTypeRelation(value=InvestmentScopeEnum.CREDIT)],
    )
    # 投资范围-融资
    SPECIAL_TYPE_FINANCING = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[FundTypeRelation(value=InvestmentScopeEnum.FINANCING)],
    )

    # 投资范围-融券
    SPECIAL_TYPE_SECURITIES_LENDING = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[FundTypeRelation(value=InvestmentScopeEnum.SECURITIES_LENDING)],
    )

    # 投资范围-转融通
    SPECIAL_TYPE_RE_FINANCE = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[FundTypeRelation(value=InvestmentScopeEnum.RE_FINANCE)],
    )

    # 投资范围-转融通/融资
    SPECIAL_TYPE_FINANCING_OR_RE_FINANCE = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[
            FundTypeRelation(value=InvestmentScopeEnum.FINANCING),
            FundTypeRelation(value=InvestmentScopeEnum.RE_FINANCE),
        ],
    )

    # 投资范围-融券/融资
    SPECIAL_TYPE_FINANCING_OR_SECURITIES_LENDING = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[
            FundTypeRelation(value=InvestmentScopeEnum.FINANCING),
            FundTypeRelation(value=InvestmentScopeEnum.SECURITIES_LENDING),
        ],
    )

    # 投资范围-商品期货
    SPECIAL_TYPE_COMMODITY_FEATURES = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[FundTypeRelation(value=InvestmentScopeEnum.COMMODITY_FEATURES)],
    )

    # 有侧袋机制
    SIDE_POCKET_YES = TemplateRelation(
        name=PublicFundClassifyName.SIDE_POCKET,
        values=[FundTypeRelation(value=DisclosureEnum.YES)],
    )
    # 无侧袋机制
    SIDE_POCKET_NO = TemplateRelation(
        name=PublicFundClassifyName.SIDE_POCKET,
        values=[FundTypeRelation(value=DisclosureEnum.NO)],
    )

    # 货币基金
    SIDE_TYPE_MONEY = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(value=FundTypeEnum.MONEY)],
    )

    # 货币基金/联接基金
    SIDE_TYPE_MONEY_LINKED_FUND = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(value=FundTypeEnum.MONEY),
            FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.LINKED_FUND),
        ],
    )

    # 非货币基金
    SIDE_TYPE_MONEY_NO = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(value=FundTypeEnum.MONEY, relation=RelationEnum.UNEQUAL)],
    )

    # 定期开放
    SIDE_TYPE_REGULAR_OPEN = TemplateRelation(
        name=PublicFundClassifyName.OPERATE_MODE,
        values=[FundTypeRelation(value=OperateModeEnum.REGULAR_OPEN)],
    )

    # 非定期开放
    SIDE_TYPE_REGULAR_OPEN_NO = TemplateRelation(
        name=PublicFundClassifyName.OPERATE_MODE,
        values=[FundTypeRelation(value=OperateModeEnum.REGULAR_OPEN, relation=RelationEnum.UNEQUAL)],
    )

    # 开放式
    SIDE_TYPE_OPEN = TemplateRelation(
        name=PublicFundClassifyName.OPERATE_MODE,
        values=[FundTypeRelation(value=OperateModeEnum.OPEN)],
    )

    # 非开放式
    SIDE_TYPE_OPEN_NO = TemplateRelation(
        name=PublicFundClassifyName.OPERATE_MODE,
        values=[FundTypeRelation(value=OperateModeEnum.OPEN, relation=RelationEnum.UNEQUAL)],
    )

    # 开放式/定期开放
    SIDE_TYPE_OPEN_REGULAR_OPEN = TemplateRelation(
        name=PublicFundClassifyName.OPERATE_MODE,
        values=[FundTypeRelation(value=OperateModeEnum.REGULAR_OPEN), FundTypeRelation(value=OperateModeEnum.OPEN)],
    )
    # 非发起式/（非货币基金&非ETF）
    SIDE_TYPE_OPEN_REGULAR_OPEN_ETF_NO = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            AllMatchRelation(
                values=[
                    FundTypeRelation(
                        name=PublicFundClassifyName.FUND_TYPE, value=FundTypeEnum.MONEY, relation=RelationEnum.UNEQUAL
                    ),
                    FundTypeRelation(
                        name=PublicFundClassifyName.SPECIAL_TYPE,
                        value=SpecialTypeEnum.ETF,
                        relation=RelationEnum.UNEQUAL,
                    ),
                ]
            ),
            AllMatchRelation(
                values=[
                    FundTypeRelation(
                        name=PublicFundClassifyName.OPERATE_MODE,
                        value=OperateModeEnum.OPEN,
                        relation=RelationEnum.UNEQUAL,
                    ),
                    FundTypeRelation(
                        name=PublicFundClassifyName.OPERATE_MODE,
                        value=OperateModeEnum.REGULAR_OPEN,
                        relation=RelationEnum.UNEQUAL,
                    ),
                ]
            ),
        ],
    )

    # 封闭式/货币基金
    SIDE_TYPE_CLOSE_MONEY = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(name=PublicFundClassifyName.OPERATE_MODE, value=OperateModeEnum.CLOSE),
            FundTypeRelation(name=PublicFundClassifyName.FUND_TYPE, value=FundTypeEnum.MONEY),
        ],
    )

    # 封闭式/货币基金/ETF
    SIDE_TYPE_CLOSE_MONEY_ETF = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[
            FundTypeRelation(name=PublicFundClassifyName.OPERATE_MODE, value=OperateModeEnum.CLOSE),
            FundTypeRelation(name=PublicFundClassifyName.FUND_TYPE, value=FundTypeEnum.MONEY),
            FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.ETF),
        ],
    )

    # ETF/货币基金
    SIDE_TYPE_ETF_MONEY = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(value=SpecialTypeEnum.ETF), FundTypeRelation(value=FundTypeEnum.MONEY)],
    )

    # 发起式/定期开放式
    SIDE_TYPE_INITIATE_REGULAR_OPEN = TemplateRelation(
        name=PublicFundClassifyName.OPERATE_MODE,
        values=[
            FundTypeRelation(value=OperateModeEnum.INITIATE),
            FundTypeRelation(value=OperateModeEnum.REGULAR_OPEN),
        ],
    )

    # 发起式/开放式
    SIDE_TYPE_INITIATE_OPEN = TemplateRelation(
        name=PublicFundClassifyName.OPERATE_MODE,
        values=[
            FundTypeRelation(value=OperateModeEnum.INITIATE),
            FundTypeRelation(value=OperateModeEnum.OPEN),
        ],
    )

    # 封闭式/定期开放式
    SIDE_TYPE_CLOSE_REGULAR_OPEN = TemplateRelation(
        name=PublicFundClassifyName.OPERATE_MODE,
        values=[
            FundTypeRelation(value=OperateModeEnum.CLOSE),
            FundTypeRelation(value=OperateModeEnum.REGULAR_OPEN),
        ],
    )

    # FOF
    SIDE_TYPE_FOF = TemplateRelation(
        name=PublicFundClassifyName.FUND_TYPE,
        values=[FundTypeRelation(name=PublicFundClassifyName.SPECIAL_TYPE, value=SpecialTypeEnum.FOF)],
    )

    # 非封闭式
    SIDE_TYPE_CLOSE_NO = TemplateRelation(
        name=PublicFundClassifyName.OPERATE_MODE,
        values=[FundTypeRelation(value=OperateModeEnum.CLOSE, relation=RelationEnum.UNEQUAL)],
    )

    # 封闭式
    SIDE_TYPE_CLOSE = TemplateRelation(
        name=PublicFundClassifyName.OPERATE_MODE,
        values=[FundTypeRelation(value=OperateModeEnum.CLOSE)],
    )

    # 申购与赎回->转换
    DISCLOSURE_FUND_SUBSCRIPTION_CONVERT = TemplateRelation(
        name=PublicFundClassifyName.FUND_SUBSCRIPTION,
        values=[FundTypeRelation(value=FundSubscriptionSubChapterEnum.CONVERT)],
    )

    # 申购与赎回->定期定额投资
    DISCLOSURE_FUND_SUBSCRIPTION_PERIOD_INVEST = TemplateRelation(
        name=PublicFundClassifyName.FUND_SUBSCRIPTION,
        values=[FundTypeRelation(value=FundSubscriptionSubChapterEnum.PERIOD_INVEST)],
    )

    # 申购与赎回->转托管
    DISCLOSURE_FUND_SUBSCRIPTION_TRANSFER_CUSTODY = TemplateRelation(
        name=PublicFundClassifyName.FUND_SUBSCRIPTION,
        values=[FundTypeRelation(value=FundSubscriptionSubChapterEnum.TRANSFER_CUSTODY)],
    )

    # 申购与赎回->非交易过户
    DISCLOSURE_FUND_SUBSCRIPTION_NON_TRANSACTION_TRANSFER = TemplateRelation(
        name=PublicFundClassifyName.FUND_SUBSCRIPTION,
        values=[FundTypeRelation(value=FundSubscriptionSubChapterEnum.NON_TRANSACTION_TRANSFER)],
    )

    # 上交所
    STOCK_BOURSE_SH = TemplateRelation(
        name=PublicFundClassifyName.STOCK_BOURSE,
        values=[FundTypeRelation(value=FundStockBourseNameEnum.SHANGHAI)],
    )

    # 深交所
    STOCK_BOURSE_SZ = TemplateRelation(
        name=PublicFundClassifyName.STOCK_BOURSE,
        values=[FundTypeRelation(value=FundStockBourseNameEnum.SHENZHEN)],
    )

    #  深交所/上交所
    STOCK_BOURSE_SZ_OR_SH = TemplateRelation(
        name=PublicFundClassifyName.STOCK_BOURSE,
        values=[
            FundTypeRelation(value=FundStockBourseNameEnum.SHENZHEN),
            FundTypeRelation(value=FundStockBourseNameEnum.SHANGHAI),
        ],
    )

    # 科创板
    SPECIAL_TYPE_STAR_MARKET = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[FundTypeRelation(value=InvestmentScopeEnum.STAR_MARKET)],
    )

    # 权证
    SPECIAL_TYPE_WARRANT = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[FundTypeRelation(value=InvestmentScopeEnum.WARRANT)],
    )

    # 同业存单
    SPECIAL_TYPE_NCD = TemplateRelation(
        name=PublicFundClassifyName.INVESTMENT_SCOPE,
        values=[FundTypeRelation(value=InvestmentScopeEnum.NCD)],
    )

    # 券商结算模式
    MODE_SECURITIES_TRADER = TemplateRelation(
        name=PublicFundClassifyName.SETTLE_ACCOUNTS_MODE,
        values=[FundTypeRelation(value=CustodySettleAccountsMode.SECURITIES_TRADER_MODE)],
    )

    # 托管人结算模式
    MODE_TRUSTEE = TemplateRelation(
        name=PublicFundClassifyName.SETTLE_ACCOUNTS_MODE,
        values=[FundTypeRelation(value=CustodySettleAccountsMode.TRUSTEE_MODE)],
    )

    # A类份额
    SHARE_CATEGORY_A = TemplateRelation(
        name=PublicFundClassifyName.SHARE_CATEGORY,
        values=[FundTypeRelation(value=ShareCategoryEnum.MODE_A)],
    )
    # C类份额
    SHARE_CATEGORY_C = TemplateRelation(
        name=PublicFundClassifyName.SHARE_CATEGORY,
        values=[FundTypeRelation(value=ShareCategoryEnum.MODE_C)],
    )


@dataclass
class AssetTemplateConditional:
    # 单一
    NAME_SINGLE = TemplateRelation(
        name=AssetClassifyName.PROJECT_NAME, values=[FundTypeRelation(value=AssetProjectNameEnum.SINGLE)]
    )

    # 集合
    NAME_POOLED = TemplateRelation(
        name=AssetClassifyName.PROJECT_NAME, values=[FundTypeRelation(value=AssetProjectNameEnum.POOLED)]
    )

    # 单一/集合
    NAME_SINGLE_POOLED = TemplateRelation(
        name=AssetClassifyName.PROJECT_NAME,
        values=[
            FundTypeRelation(value=AssetProjectNameEnum.SINGLE),
            FundTypeRelation(value=AssetProjectNameEnum.POOLED),
        ],
    )

    # FOF
    FOF = TemplateRelation(name=AssetClassifyName.PROJECT_TYPE, values=[FundTypeRelation(value=AssetFundTypeEnum.FOF)])

    # 封闭式
    OPERATE_CLOSE = TemplateRelation(
        name=AssetClassifyName.OPERATE_MODE, values=[FundTypeRelation(value=AssetManagementOperateModeEnum.CLOSE)]
    )

    # 投资顾问
    INVESTMENT_ADVISER = TemplateRelation(
        name=AssetClassifyName.INVESTMENT_ADVISER, values=[FundTypeRelation(value=DisclosureEnum.YES)]
    )

    # 有大会
    HOLDER_MEETING_YES = TemplateRelation(
        name=AssetClassifyName.PROJECT_GENERAL_MEETING, values=[FundTypeRelation(value=DisclosureEnum.YES)]
    )

    # 股权
    STOCK_RIGHT_YES = TemplateRelation(
        name=AssetClassifyName.STOCK_RIGHT, values=[FundTypeRelation(value=DisclosureEnum.YES)]
    )

    # 非标投资
    NON_STANDARD_INVESTMENT_YES = TemplateRelation(
        name=AssetClassifyName.NON_STANDARD_INVESTMENT, values=[FundTypeRelation(value=DisclosureEnum.YES)]
    )

    # 无非标投资
    NON_STANDARD_INVESTMENT_NO = TemplateRelation(
        name=AssetClassifyName.NON_STANDARD_INVESTMENT, values=[FundTypeRelation(value=DisclosureEnum.NO)]
    )

    # 固定收益类
    FIXED_INCOME_CATEGORY = TemplateRelation(
        name=AssetClassifyName.PROJECT_TYPE,
        values=[
            FundTypeRelation(value=AssetFundTypeEnum.FIXED_INCOME_CATEGORY),
        ],
    )

    # 权益类
    EQUITIES = TemplateRelation(
        name=AssetClassifyName.PROJECT_TYPE,
        values=[
            FundTypeRelation(value=AssetFundTypeEnum.EQUITIES),
        ],
    )

    # 期货和衍生品类
    FUTURES_AND_DERIVATIVES = TemplateRelation(
        name=AssetClassifyName.PROJECT_TYPE,
        values=[
            FundTypeRelation(value=AssetFundTypeEnum.FUTURES_AND_DERIVATIVES),
        ],
    )

    # 混合类
    MIXED_CLASS = TemplateRelation(
        name=AssetClassifyName.PROJECT_TYPE,
        values=[
            FundTypeRelation(value=AssetFundTypeEnum.MIXED_CLASS),
        ],
    )

    # 固定收益类/权益类/期货和衍生品类
    EQUITIES_FIXED_INCOME_CATEGORY_FUTURES_DERIVATIVES = TemplateRelation(
        name=AssetClassifyName.PROJECT_TYPE,
        values=[
            FundTypeRelation(value=AssetFundTypeEnum.EQUITIES),
            FundTypeRelation(value=AssetFundTypeEnum.FIXED_INCOME_CATEGORY),
            FundTypeRelation(value=AssetFundTypeEnum.FUTURES_AND_DERIVATIVES),
        ],
    )

    # 权益类/期货和衍生品类
    EQUITIES_FUTURES_DERIVATIVES = TemplateRelation(
        name=AssetClassifyName.PROJECT_TYPE,
        values=[
            FundTypeRelation(value=AssetFundTypeEnum.EQUITIES),
            FundTypeRelation(value=AssetFundTypeEnum.FUTURES_AND_DERIVATIVES),
        ],
    )


@dataclass
class Content:
    key: str
    name: str
    rules: list[dict]
    valid_keys: dict | None = None
    content_type: ContentValueTypeEnum = ContentValueTypeEnum.NUMBER


@dataclass
class ContentValueRelation:
    patterns: dict[str, PatternCollection | str | int]
    conditions: list[Content]


@dataclass
class ContentConditional:
    # 支付赎回款项日期
    PAYMENT_OF_REDEMPTION = ContentValueRelation(
        patterns={
            "X": PatternCollection(
                rf"在T[＋+](?P<val>[{R_CN_NUMBER}]+)日[^{R_NOT_CONJUNCTION_PUNCTUATION}]*?支付赎回款项"
            ),
            "X1": PatternCollection(
                rf"在T[＋+](?P<val>[{R_CN_NUMBER}]+)日[^{R_NOT_CONJUNCTION_PUNCTUATION}]*?交易的?有效性进行确认"
            ),
            "X2": PatternCollection(
                rf"在T[＋+](?P<val>[{R_CN_NUMBER}]+)日[^{R_NOT_CONJUNCTION_PUNCTUATION}]*?查询申请的确认情况"
            ),
            "X3": 7,
            "X4": 3,
        },
        conditions=[
            Content(key="X", name="支付赎回款项时间", rules=[{"X3": {"name": "", "relation": RelationEnum.LTE}}]),
            Content(
                key="X1",
                name="交易有效性进行确认时间",
                rules=[
                    {"X2": {"name": "查询申请的确认时间", "relation": RelationEnum.LTE}},
                    {"X4": {"name": "", "relation": RelationEnum.LTE}},
                ],
            ),
        ],
    )

    # 出现前述情形,无需召开份额持有人大会
    WORKING_DAY_OF_FOREGOING = ContentValueRelation(
        patterns={
            "X": PatternCollection(rf"(?P<val>[{R_CN_NUMBER}]+)[^，,。；;]*?工作日出现[上前]述情形"),
            "X1": 20,
            "X2": 60,
        },
        conditions=[
            Content(
                key="X",
                name="连续出现前述情形的工作日数",
                rules=[
                    {"X1": {"name": "", "relation": RelationEnum.GTE}},
                    {"X2": {"name": "", "relation": RelationEnum.LTE}},
                ],
            ),
        ],
    )

    # 单个基金份额持有人申请赎回的基金份额超过前一开放日的基金总份额的xx%
    PERCENTAGE_REDEMPTION_SHARE_FOR_TOTAL_SHARE = ContentValueRelation(
        patterns={
            "X": PatternCollection(
                [
                    rf"单个基金份额持有人[^，,。；;]*?(?:申请赎回的基金份额|赎回申请)(?:[\(（].*?[）\)])?超过[^，,。；;]*?基金总份额[^{R_CN_NUMBER}]?(?P<val>{R_PERCENTAGE})",
                    rf"基金管理人.*接受赎回.*上一开放日基金总份额的?[^{R_CN_NUMBER}]?(?P<val>{R_PERCENTAGE})",
                ]
            ),
            "X1": 10,
            "X2": PatternCollection(rf"(?P<val>[{R_CN_NUMBER}]+)[^，,。；;：:]*?发生巨额赎回"),
            "X3": PatternCollection(rf"延缓支付赎回款项.*?超过(?P<val>[{R_CN_NUMBER}]+)"),
            "X4": 0,
        },
        conditions=[
            Content(
                key="X",
                name="申请赎回基金份额超过前一开放日基金总份额的比例",
                content_type=ContentValueTypeEnum.PERCENTAGE,
                rules=[
                    {"X1": {"name": "", "relation": RelationEnum.GTE}},
                ],
            ),
            Content(
                key="X2",
                name="连续发生巨额赎回的天数",
                rules=[
                    {"X4": {"name": "", "relation": RelationEnum.GTE}},
                ],
            ),
            Content(
                key="X3",
                name="延缓支付赎回款项的最大天数",
                rules=[
                    {"X4": {"name": "", "relation": RelationEnum.GTE}},
                ],
            ),
        ],
    )
    # 封闭期内股票资产占基金资产的比例
    THE_PROPORTION_OF_STOCK_ASSETS_TO_FUND_ASSETS = ContentValueRelation(
        patterns={
            "X": PatternCollection(
                [
                    rf"封闭期内股票资产占基金资产的比例为(?P<val>{R_PERCENTAGE})",
                    rf"封闭期内股票资产占基金资产的比例(?:不低|高)于(?P<val>{R_PERCENTAGE})",
                ]
            ),
            "X1": 60,
        },
        conditions=[
            Content(
                key="X",
                name="封闭期内股票资产占基金资产的比例",
                content_type=ContentValueTypeEnum.PERCENTAGE,
                rules=[
                    {"X1": {"name": "", "relation": RelationEnum.GTE}},
                ],
            ),
        ],
    )

    # C类销售服务费年费率
    C_CLASS_SALES_SERVICE_FEE = ContentValueRelation(
        patterns={
            "X": PatternCollection(
                [
                    rf"C类基金份额的销售服务费年费率为?(?P<val>{R_PERCENTAGE})",
                    rf"C类基金份额的销售服务费.*?按前一日C类基金份额的基金资产净值的?(?P<val>{R_PERCENTAGE})",
                ]
            ),
            "X1": PatternCollection(rf"H[＝=]E[a-zA-Z]?[{R_MULTIPLICATION_SYMBOL}](?P<val>{R_PERCENTAGE})÷当年天数"),
            "X2": PatternCollection(
                R_FEES_PAYMENT_DATE.format(**{"name": "服务费", "punctuation": R_PUNCTUATION, "num": R_CN_NUMBER})
            ),
            "X3": 0,
        },
        conditions=[
            Content(
                key="X",
                name="基金资产净值年费率",
                content_type=ContentValueTypeEnum.PERCENTAGE,
                rules=[
                    {"X1": {"name": "年服务费率", "relation": RelationEnum.EQUAL}},
                ],
            ),
            Content(
                key="X2",
                name="销售服务费工作日",
                content_type=ContentValueTypeEnum.PERCENTAGE,
                rules=[
                    {"X3": {"name": "", "relation": RelationEnum.GTE}},
                ],
            ),
        ],
    )

    # 托管费
    TRUSTEE_FEE = ContentValueRelation(
        patterns={
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2125#note_326954
            "X": PatternCollection(
                [
                    rf"托管费按前一日基金资产净值.*?(?P<val>{R_PERCENTAGE})的?年费率计提",
                    rf"基金份额的?年托管费率为(?P<val>{R_PERCENTAGE})",
                ]
            ),
            "X1": PatternCollection(rf"H[＝=]E[a-zA-Z]?[{R_MULTIPLICATION_SYMBOL}](?P<val>{R_PERCENTAGE})÷当年天数"),
            "X2": PatternCollection(
                R_FEES_PAYMENT_DATE.format(**{"name": "托管费", "punctuation": R_PUNCTUATION, "num": R_CN_NUMBER})
            ),
            "X3": 0,
        },
        conditions=[
            Content(
                key="X",
                name="基金资产净值年费率",
                content_type=ContentValueTypeEnum.PERCENTAGE,
                rules=[
                    {"X1": {"name": "年托管费率", "relation": RelationEnum.EQUAL}},
                ],
            ),
            Content(
                key="X2",
                name="托管费计提工作日",
                content_type=ContentValueTypeEnum.PERCENTAGE,
                rules=[
                    {"X3": {"name": "", "relation": RelationEnum.GTE}},
                ],
            ),
        ],
    )

    # 管理费
    # 提示未找到对应费率，讨论见：https://mm.paodingai.com/cheftin/pl/e9qjomorefnmzxk5n7yrqiheow
    ADMINISTRATIVE_FEE = ContentValueRelation(
        patterns={
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2125#note_326954
            "X": PatternCollection(
                [
                    rf"管理费按前一日基金资产净值.*?(?P<val>{R_PERCENTAGE})的?年费率计提",
                    rf"基金份额的?年管理费率为(?P<val>{R_PERCENTAGE})",
                ]
            ),
            "X1": PatternCollection(rf"H[＝=]E[a-zA-Z]?[{R_MULTIPLICATION_SYMBOL}](?P<val>{R_PERCENTAGE})÷当年天数"),
            "X2": PatternCollection(
                R_FEES_PAYMENT_DATE.format(**{"name": "管理费", "punctuation": R_PUNCTUATION, "num": R_CN_NUMBER})
            ),
            "X3": 0,
        },
        conditions=[
            Content(
                key="X",
                name="基金资产净值年费率",
                content_type=ContentValueTypeEnum.PERCENTAGE,
                rules=[
                    {"X1": {"name": "年管理费率", "relation": RelationEnum.EQUAL}},
                ],
            ),
            Content(
                key="X2",
                name="管理费计提工作日",
                content_type=ContentValueTypeEnum.PERCENTAGE,
                rules=[
                    {"X3": {"name": "", "relation": RelationEnum.GTE}},
                ],
            ),
        ],
    )

    # 基金的投资组合比例 投资组合比例.*?
    PROPORTION_OF_FUND_PORTFOLIO = ContentValueRelation(
        patterns={
            "X0": PatternCollection(
                [
                    rf"(股票|债券)(?:[{R_CONJUNCTION}](?:[^{R_NOT_CONJUNCTION_PUNCTUATION}])+)?(?:投资)?(?:比例)?(?:应当不|不应|应?不)(?:低于|少于)基金资产的?(?:比例)?[^{R_CN_NUMBER}]?(?P<val>{R_PERCENTAGE})",
                    rf"(股票|债券)(?:[{R_CONJUNCTION}](?:[^{R_NOT_CONJUNCTION_PUNCTUATION}])+)?(?:投资)?(?:比例)?占基金资产的?(?:比例)(?:应当不|不应|应?不)(?:低于|少于)(?P<val>{R_PERCENTAGE})",
                ]
            ),
            "X1": PatternCollection(
                rf"股票(?:(?:资产|投资)的?){{1,2}}(?:比例)?占基金资产的?(?:比例)[^{R_CN_NUMBER}]?(?:{R_PERCENTAGE_IGNORE_UNIT})[{R_INTERVAL}](?P<val>{R_PERCENTAGE})"
            ),
            "X2": PatternCollection(
                rf"股票(?:(?:资产|投资)的?){{1,2}}(?:比例)?占基金资产的?(?:比例)[^{R_CN_NUMBER}]?(?P<val>{R_PERCENTAGE_IGNORE_UNIT})[{R_INTERVAL}](?:{R_PERCENTAGE})"
            ),
            "X3": PatternCollection(
                rf"股票(?:(?:资产|投资)的?){{1,2}}(?:比例)?占基金资产的?(?:比例)[^{R_CN_NUMBER}]?(?:{R_PERCENTAGE_IGNORE_UNIT})[{R_INTERVAL}](?P<val>{R_PERCENTAGE})"
            ),
            "X4": PatternCollection(
                rf"股票.*?基金资产[^{R_CN_NUMBER}]*?(?P<val>{R_PERCENTAGE}).*?(?:指数成份股|备选成份股|指数成份券|备选成份券)"
            ),
            "X5": PatternCollection(
                rf"债券.*?基金资产[^{R_CN_NUMBER}]*?(?P<val>{R_PERCENTAGE}).*?(?:指数成份券|备选成份券)"
            ),
            "X6": PatternCollection(rf"证券投资基金.*?基金资产[^{R_CN_NUMBER}]*?(?P<val>{R_PERCENTAGE})"),
            "X7": PatternCollection(
                rf"(?:证监会依法核准|注册公开募集)的基金份额.*?基金资产[^{R_CN_NUMBER}]*?(?P<val>{R_PERCENTAGE})"
            ),
            "D0": 80,
            "D1": 100,
            "D2": 0,
        },
        conditions=[
            Content(
                key="X0",
                name="投资组合比例下限阈值",
                content_type=ContentValueTypeEnum.PERCENTAGE,
                rules=[
                    {"D0": {"name": "", "relation": RelationEnum.GTE}},
                ],
            ),
            Content(
                key="X1",
                name="投资组合比例上限阈值",
                content_type=ContentValueTypeEnum.PERCENTAGE,
                rules=[
                    {"D1": {"name": "", "relation": RelationEnum.LTE}},
                    {"D0": {"name": "", "relation": RelationEnum.GT}},
                ],
            ),
            Content(
                key="X2",
                name="投资组合比例下限阈值",
                content_type=ContentValueTypeEnum.PERCENTAGE,
                rules=[
                    {"D2": {"name": "", "relation": RelationEnum.GTE}},
                ],
            ),
            Content(
                key="X3",
                name="投资组合比例上限阈值",
                content_type=ContentValueTypeEnum.PERCENTAGE,
                rules=[
                    {"D1": {"name": "", "relation": RelationEnum.LTE}},
                    {"X2": {"name": "投资组合比例下限阈值", "relation": RelationEnum.GT}},
                ],
            ),
            Content(
                key="X4",
                name="投资组合比例下限阈值",
                content_type=ContentValueTypeEnum.PERCENTAGE,
                rules=[
                    {"D0": {"name": "", "relation": RelationEnum.GTE}},
                ],
            ),
            Content(
                key="X5",
                name="投资组合比例下限阈值",
                content_type=ContentValueTypeEnum.PERCENTAGE,
                rules=[
                    {"D0": {"name": "", "relation": RelationEnum.GTE}},
                ],
            ),
            Content(
                key="X6",
                name="投资组合比例下限阈值",
                content_type=ContentValueTypeEnum.PERCENTAGE,
                rules=[
                    {"D0": {"name": "", "relation": RelationEnum.GTE}},
                ],
            ),
            Content(
                key="X7",
                name="投资组合比例下限阈值",
                content_type=ContentValueTypeEnum.PERCENTAGE,
                rules=[
                    {"D0": {"name": "", "relation": RelationEnum.GTE}},
                ],
            ),
        ],
    )

    # 港股通-投资组合比例
    HK_STOCK_INVESTMENT_RATIO = ContentValueRelation(
        patterns={
            # 投资于港股通标的股票占股票资产/非现金基金资产的比例为X0%-X%；
            "X0": PatternCollection(
                rf"港股通[\u4e00-\u9fa5]*?占[^{R_PUNCTUATION}]*?(?:股票资产|非现金基金资产)的?比例.?(?P<val>{R_PERCENTAGE_IGNORE_UNIT})[{R_INTERVAL}](?:{R_PERCENTAGE})"
            ),
            "X": PatternCollection(
                [
                    # 投资于港股通标的股票占股票资产/非现金基金资产的比例为X0%-X%；
                    rf"港股通[\u4e00-\u9fa5]*?占[^{R_PUNCTUATION}]*?(?:股票资产|非现金基金资产)的?比例.?(?:{R_PERCENTAGE_IGNORE_UNIT})[{R_INTERVAL}](?P<val>{R_PERCENTAGE})",
                    # 投资于港股通标的股票占股票资产的比例不超过X%；
                    rf"港股通[\u4e00-\u9fa5]*?占股票资产的?比例.?[\u4e00-\u9fa5]*?(?P<val>{R_PERCENTAGE})",
                    # 非现金资产中不低于X%的资产将投资于港股通股票；
                    rf"(?P<val>{R_PERCENTAGE})[\u4e00-\u9fa5]*?投资于港股通股票",
                    # 港股通股票不超过股票资产的X% / 投资于港股通股票的比例不低于非现金基金资产的X%；/ 投资于港股通标的股票的比例不低于非现金基金资产的X%；
                    rf"港股通(?:标的)?股票[\u4e00-\u9fa5]*?(?:基金|股票)资产的?(?P<val>{R_PERCENTAGE})",
                ]
            ),
            "X1": 80,
            "X2": 50,
        },
        conditions=[
            Content(
                key="X",
                name="港股通股票的投资比例限制",
                content_type=ContentValueTypeEnum.PERCENTAGE,
                valid_keys={
                    "X1": [TemplateConditional.SPECIAL_TYPE_HK_STOCK],
                    "X2": [TemplateConditional.SPECIAL_TYPE_HK_STOCK_NO],
                },
                rules=[
                    {"X1": {"name": "", "relation": RelationEnum.GTE}},
                    {"X2": {"name": "", "relation": RelationEnum.LTE}},
                ],
            ),
        ],
    )

    # 交易日
    TRADING_DAY = ContentValueRelation(
        patterns={
            "X1": PatternCollection(
                rf"管理人[^{R_NOT_CONJUNCTION_PUNCTUATION}]*?在流动性受限资产可?(出售|转让|恢复交易).*?的(?P<val>[{R_CN_NUMBER}]+)个交易日内调整至符合相关要求"
            ),
            "X2": 20,
        },
        conditions=[
            Content(
                key="X1",
                name="比例限制被动超限处理日",
                content_type=ContentValueTypeEnum.NUMBER,
                rules=[
                    {"X2": {"name": "", "relation": RelationEnum.LTE}},
                ],
            )
        ],
    )

    @staticmethod
    def compare_value_with_relation(
        first_val, second_val, relation: RelationEnum, content_type: ContentValueTypeEnum = ContentValueTypeEnum.NUMBER
    ):
        if content_type == ContentValueTypeEnum.NUMBER:
            first_val = int(NumberUtil.cn_number_2_digit(str(first_val)))
            second_val = int(NumberUtil.cn_number_2_digit(str(second_val)))
        elif content_type == ContentValueTypeEnum.PERCENTAGE:
            first_val = PercentageUtil.convert_2_division(str(first_val))
            second_val = PercentageUtil.convert_2_division(str(second_val))

        if first_val is None or second_val is None:
            return False
        if relation == RelationEnum.EQUAL:
            return first_val == second_val
        if relation == RelationEnum.UNEQUAL:
            return first_val != second_val
        if relation == RelationEnum.GTE:
            return first_val >= second_val
        if relation == RelationEnum.LTE:
            return first_val <= second_val
        if relation == RelationEnum.LT:
            return first_val < second_val
        if relation == RelationEnum.GT:
            return first_val > second_val
        return False
