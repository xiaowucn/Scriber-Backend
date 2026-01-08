import re
from dataclasses import dataclass
from re import Pattern

from remarkable.plugins.cgs.common.patterns_util import (
    R_CONJUNCTION,
    R_NOT_CONJUNCTION_PUNCTUATION,
)


@dataclass
class RegularChapter:
    name: str
    pattern: Pattern


@dataclass
class ChapterRule:
    chapters: list[RegularChapter]
    is_continued_chapter: bool = True

    def convert2dict(self):
        chapter_name = [f"《{chapter.name}》" for chapter in self.chapters]
        join_name = "->".join(chapter_name)
        return {
            "chapters": [chapter.pattern for chapter in self.chapters],
            "is_continued_chapter": self.is_continued_chapter,
            "miss_detail": {"reason_text": f"章节{join_name}不存在", "miss_content": join_name},
        }


@dataclass
class CatalogsPattern:
    # 基金份额的申购与赎回
    FUND_SUBSCRIPTION = RegularChapter(
        "基金份额的申购与赎回", re.compile(rf"基金份额的(?:(?:申购|赎回)[{R_CONJUNCTION}]?){{2}}$")
    )
    FUND_SUBSCRIPTION_PLACE = RegularChapter(
        "申购和赎回的场所", re.compile(rf"(?:(?:申购|赎回)[{R_CONJUNCTION}]?){{2}}的?场所$")
    )
    FUND_SUBSCRIPTION_CONVERSION = RegularChapter("基金转换", re.compile(r"基金的?转换$"))
    FUND_SUBSCRIPTION_OPENDAY = RegularChapter(
        "申购和赎回的开放日及时间", re.compile(rf"(?:(?:申购|赎回)[{R_CONJUNCTION}]?){{2}}的开放日及时间$")
    )
    FUND_SUBSCRIPTION_PRINCIPLE = RegularChapter(
        "申购与赎回的原则", re.compile(rf"(?:(?:申购|赎回)[{R_CONJUNCTION}]?){{2}}的原则$")
    )
    FUND_SUBSCRIPTION_COUNT_LIMIT = RegularChapter(
        "申购和赎回的数量限制", re.compile(rf"(?:(?:申购|赎回)[{R_CONJUNCTION}]?){{2}}的数量限制$")
    )
    FUND_SUBSCRIPTION_PAUSE_OR_REOPEN = RegularChapter(
        "暂停申购或赎回的公告和重新开放申购或赎回的公告",
        re.compile(r"暂停(?:(?:申购|赎回)[或/]?){2}的公告和重新开放(?:(?:申购|赎回)[或/]?){2}的公告$"),
    )
    FUND_SUBSCRIPTION_IMPLEMENT = RegularChapter(
        "实施侧袋机制期间本基金的申购与赎回",
        re.compile(rf"实施侧袋机制期间本基金的(?:(?:申购|赎回)[{R_CONJUNCTION}]?){{2}}$"),
    )
    FUND_SUBSCRIPTION_PROCEDURE = RegularChapter(
        "申购与赎回的程序", re.compile(rf"(?:(?:申购|赎回)[{R_CONJUNCTION}]?){{2}}的程序$")
    )
    FUND_SUBSCRIPTION_TRANSFER_CUSTODY = RegularChapter("基金的转托管", re.compile(r"基金的转托管$"))
    FUND_SUBSCRIPTION_NON_TRANSACTION_TRANSFER = RegularChapter("基金的非交易过户", re.compile(r"基金的非交易过户$"))
    FUND_SUBSCRIPTION_PRICE_EXPENSE_PURPOSE = RegularChapter(
        "申购和赎回的价格、费用及其用途", re.compile(r"申购和赎回的价格、费用及其用途$")
    )
    FUND_SUBSCRIPTION_REJECT_SUSPEND_SUBSCRIBE = RegularChapter(
        "拒绝或暂停申购的情形", re.compile(rf"拒绝[{R_CONJUNCTION}]?暂停申购的情形$")
    )
    FUND_SUBSCRIPTION_SUSPEND_RANSOM_PAY = RegularChapter(
        "暂停赎回或延缓支付赎回款项的情形", re.compile(rf"暂停(接受)?赎回[{R_CONJUNCTION}]?延缓支付赎回款项的情形$")
    )
    FUND_SUBSCRIPTION_HUGE_REDEMPTION = RegularChapter(
        "巨额赎回的情形及处理方式", re.compile(rf"巨额赎回的情形[{R_CONJUNCTION}]?处理方式$")
    )

    # 基金合同当事人权利与义务
    FUND_RIGHT_OBLIGATION = RegularChapter(
        "基金合同当事人权利与义务",
        re.compile(
            rf"(?:(基金合同)?当事人|(?:(?:基金)?(?:份额持有人|管理人|托管人)[{R_CONJUNCTION}]?){{3}})[的及]?权利[{R_CONJUNCTION}]?义务$"
        ),
    )
    FUND_RIGHT_OBLIGATION_TRUSTEE = RegularChapter("基金托管人", re.compile(r"托管人$"))
    FUND_RIGHT_OBLIGATION_TRUSTEE_RIGHT_DUTY = RegularChapter(
        "托管人的权利与义务", re.compile(rf"托管人的权利[{R_CONJUNCTION}]?义务$")
    )
    FUND_RIGHT_OBLIGATION_SHARE_HOLDER_RIGHT_DUTY = RegularChapter(
        "份额持有人的权利与义务", re.compile(rf"份额持有人的权利[{R_CONJUNCTION}]?义务$")
    )
    FUND_RIGHT_OBLIGATION_MANAGER = RegularChapter("基金管理人", re.compile(r"管理人$"))
    FUND_RIGHT_OBLIGATION_MANAGER_RIGHT_DUTY = RegularChapter(
        "管理人的权利与义务", re.compile(rf"管理人的权利[{R_CONJUNCTION}]?义务$")
    )
    FUND_RIGHT_OBLIGATION_SHARE_HOLDER_DUTY = RegularChapter("份额持有人的义务", re.compile(r"份额持有人的义务"))
    FUND_RIGHT_OBLIGATION_SHARE_HOLDER = RegularChapter("基金份额持有人", re.compile(r"份额持有人$"))
    FUND_RIGHT_OBLIGATION_MANAGER_DUTY = RegularChapter(
        "管理人的义务", re.compile(rf"管理人的权利[{R_CONJUNCTION}]?义务$")
    )
    # 基金份额持有人大会
    FUND_SHARE_HOLDER = RegularChapter(
        "基金份额持有人大会",
        re.compile(
            rf"基金份额持有人(?:大会|会议)(?:(?:(?:召集|议事|表决)[{R_CONJUNCTION}]?)*的(?:(?:程序|规则)[{R_CONJUNCTION}]?){{2}})?$"
        ),
    )
    FUND_SHARE_HOLDER_CONVENING_MODE = RegularChapter(
        "召集人及召集方式", re.compile(rf"召集人[{R_CONJUNCTION}]召集方式$")
    )
    FUND_SHARE_HOLDER_VOTE = RegularChapter("表决", re.compile(r"表决$"))
    FUND_SHARE_HOLDER_COUNT_VOTE = RegularChapter("计票", re.compile(r"计票(?:程序)?$"))
    FUND_SHARE_HOLDER_NOTIFY = RegularChapter("召开通知", re.compile(r"召开基金份额持有人大会的通知时间"))
    FUND_SHARE_HOLDER_SUPPLEMENTARY_AGREEMENT = RegularChapter("出席方式的补充约定", re.compile(r"出席方式的补充约定"))
    FUND_SHARE_HOLDER_CAUSE = RegularChapter("召开事由", re.compile(r"召开事由$"))
    FUND_SHARE_HOLDER_ATTEND = RegularChapter("出席方式", re.compile(r"基金份额持有人出席会议的方式"))
    FUND_SHARE_HOLDER_GENERAL_PROVISIONS = RegularChapter("一般规定", re.compile(r"一般规定"))
    FUND_SHARE_HOLDER_CONTENT_PROCEDURE = RegularChapter("议事内容与程序", re.compile(r"议事内容与程序"))
    FUND_SHARE_HOLDER_SIDE_POCKET_CONVENTION = RegularChapter(
        "实施侧袋机制期间基金份额持有人大会的特殊约定", re.compile(r"实施侧袋机制期间基金份额持有人大会的特殊约定$")
    )
    FUND_SHARE_HOLDER_HOLD = RegularChapter(
        "无需召开基金份额持有人大会的情形", re.compile(r"无需召开基金份额持有人大会的情形$")
    )

    FUND_SHARE_HOLDER_TAKE_EFFECT_NOTICE = RegularChapter(
        "份额持有人大会决议的生效和公告", re.compile(rf"生效[{R_CONJUNCTION}]公告$")
    )

    # 基金的托管
    FUND_TRUSTEESHIP = RegularChapter("基金的托管", re.compile(r"基金的托管$"))
    # 基金的投资
    FUND_INVEST = RegularChapter(
        "基金的投资", re.compile(rf"基金(?:财产)?的投资(?:范围|方向)?(?:[{R_CONJUNCTION}]投资限制)?$")
    )
    FUND_INVEST_PRINCIPLE = RegularChapter(
        "基金管理人代表基金行使股东或债权人权利的处理原则及方法",
        re.compile(r"基金管理人代表基金行使股东或债权人权利的处理原则及方法$"),
    )
    FUND_INVEST_SCOPE_TARGET = RegularChapter("投资目标", re.compile(r"投资目标$"))
    FUND_INVEST_SCOPE_INVESTMENT = RegularChapter("投资范围", re.compile(r"投资范围$"))
    FUND_INVEST_SCOPE_INVESTMENT_RESTRICTION = RegularChapter("投资比例、投资限制", re.compile(r"(投资比例|投资限制)"))
    FUND_INVEST_SCOPE_COMBINATORIAL_RESTRICTION = RegularChapter("组合限制", re.compile(r"组合限制$"))
    FUND_INVEST_SCOPE_FORBIDDING_ACT = RegularChapter("禁止行为", re.compile(r"禁止行为$"))
    FUND_INVEST_PERFORMANCE_COMPARISON_BASIS = RegularChapter("业绩比较基准", re.compile(r"业绩比较基准$"))
    FUND_INVEST_SIDE_POCKET_MECHANISM_OPERATION = RegularChapter(
        "侧袋机制的实施和投资运作安排", re.compile(r"侧袋机制的实施和投资运作安排$")
    )
    FUND_INVEST_RISK_RETURN_CHARACTERISTICS = RegularChapter("风险收益特征", re.compile(r"风险收益特征$"))
    FUND_INVEST_INVESTMENT_STRATEGY = RegularChapter("投资策略", re.compile(r"投资策略$"))

    # 基金管理人、基金托管人的更换条件和程序
    FUND_REPLACEMENT_PROCEDURE = RegularChapter(
        "基金管理人、基金托管人的更换条件和程序",
        re.compile(rf"(?:(?:基金管理人|基金托管人)[{R_CONJUNCTION}]?){{2}}的更换条件和程序$"),
    )
    # 基金份额的发售
    FUND_SELL = RegularChapter("基金份额的发售", re.compile(r"基金份额的发售$"))
    FUND_SELL_MODE = RegularChapter(
        "基金份额的发售时间、发售方式、发售对象",
        re.compile(rf"基金份额的(?:(?:发售时间|发售方式|发售对象)[{R_CONJUNCTION}]?){{3}}$"),
    )
    FUND_SELL_SUBSCRIPTION = RegularChapter("基金份额的认购", re.compile(r"基金份额的认购$"))
    FUND_SELL_LIMIT = RegularChapter("基金份额认购金额的限制", re.compile(r"基金份额认购金额的限制$"))
    # 基金备案
    FUND_RECORD = RegularChapter("基金备案", re.compile(r"基金的?备案$"))
    FUND_RECORD_FAILURE_PROCESS_MODE = RegularChapter(
        "基金合同不能生效时募集资金的处理方式", re.compile(r"基金合同不能生效时募集资金的处理方式$")
    )
    FUND_RECORD_CONDITIONS = RegularChapter("基金备案的条件", re.compile(r"基金备案的条件$"))
    FUND_RECORD_HOLDER_NUMBER_ASSET_SIZE = RegularChapter(
        "基金存续期内的基金份额持有人数量和资产规模", re.compile(r"基金存续期内的?基金份额持有人数量和资产规模$")
    )
    # 基金的上市交易
    FUND_LISTED_LISTED_TRANSACTION = RegularChapter("基金份额的上市交易", re.compile(r"基金(?:份额)?的上市交易$"))

    # 基金的基本情况
    FUND_BASIC_INFORMATION = RegularChapter("基金的基本情况", re.compile(r"基金的基本情况$"))
    FUND_BASIC_INFORMATION_FACE_VALUE_SUBSCRIBE = RegularChapter(
        "基金份额面值和认购费用", re.compile(r"基金份额面值和认购费用$")
    )
    FUND_BASIC_INFORMATION_MINIMUM_TOTAL_AMOUNT_RAISED = RegularChapter(
        "基金的最低募集份额总额", re.compile(r"基金的最低募集份额总额$")
    )
    FUND_BASIC_INFORMATION_STANDARD_INDEX = RegularChapter("基金的标的指数", re.compile(r"标的指数$"))
    FUND_BASIC_INFORMATION_INVESTMENT_OBJECTIVE = RegularChapter("基金的投资目标", re.compile(r"基金的投资目标$"))
    FUND_TYPES_OF_FUNDS = RegularChapter("基金的类别", re.compile(r"基金的?类别$"))
    FUND_INVESTMENT_RESTRICTION = RegularChapter("投资比例、投资限制", re.compile(r"投资(比例|限制)"))

    # 基金份额折算与变更登记
    FUND_BASIC_CONVERSION_CHANGE = RegularChapter(
        "基金份额折算与变更登记", re.compile(rf"基金份额折算[{R_CONJUNCTION}]?变更登记$")
    )

    # 基金费用与税收
    FUND_BASIC_COST_REVENUE = RegularChapter("基金费用与税收", re.compile(rf"基金的?费用[{R_CONJUNCTION}]?税收$"))
    FUND_BASIC_REVENUE = RegularChapter("基金的税收", re.compile(r"基金的?税收$"))
    FUND_BASIC_EXPENSE_TYPES = RegularChapter("基金费用的种类", re.compile(r"基金费用的?种类$"))
    FUND_BASIC_ITEMS_NOT_INCLUDED_FUND_COSTS = RegularChapter(
        "不列入基金费用的项目", re.compile(r"不列入基金费用的?项目$")
    )
    FUND_EXPENSES_DURING_IMPLEMENTATION_SIDE_POCKET_MECHANISM = RegularChapter(
        "实施侧袋机制期间的基金费用", re.compile(r"实施侧袋机制期间的?基金费用$")
    )
    FUND_EXPENSES_STANDARD_METHOD_CALCULATION_MODE_PAYMENT = RegularChapter(
        "基金费用计提方法、计提标准和支付方式",
        re.compile(rf"基金费用(?:(?:计提方法|计提标准|支付方式)[{R_CONJUNCTION}]?){{3}}$"),
    )
    FUND_C_CLASS_SALES_SERVICE_FEE = RegularChapter("C类基金份额的销售服务费", re.compile(r"C类.{2,10}服务费$"))
    FUND_MANAGER_TRUSTEE_FEE = RegularChapter("托管费", re.compile(r"基金托管人的?托管费$"))
    FUND_MANAGER_ADMINISTRATIVE_FEE = RegularChapter("管理费", re.compile(r"基金管理人的?管理费$"))

    # 基金的收益与分配
    FUND_INCOME_ALLOCATION = RegularChapter(
        "基金的收益与分配",
        re.compile(rf"基金的?收益的?[{R_CONJUNCTION}]?分配(?:原则)?(?:[{R_CONJUNCTION}]?执行方式)?$"),
    )
    FUND_INCOME_ALLOCATION_PRINCIPLE = RegularChapter("货币基金的收益分配原则", re.compile(r"(基金)?的?收益分配原则$"))

    # 基金的会计与审计
    FUND_ACCOUNTING_AND_AUDITING = RegularChapter("基金的会计与审计", re.compile(r"基金的会计与审计$"))

    # 基金的信息披露
    FUND_INFORMATION_DISCLOSURE = RegularChapter("基金的信息披露", re.compile(r"基金的信息披露$"))
    FUND_BASIC_INVESTMENT_VARIETY = RegularChapter("投资品种相关公告", re.compile(r"投资品种相关公告$"))
    FUND_INFORMATION_DISCLOSURE_PAUSE = RegularChapter(
        "暂停或延迟信息披露的情形", re.compile(r"(?:(?:暂停|延迟)[或、/]?){2}信息披露的情形$")
    )
    FUND_INFORMATION_DISCLOSURE_PROVISIONAL_REPORT = RegularChapter("临时报告", re.compile(r"临时报告$"))
    FUND_PUBLICLY_DISCLOSED_FUND_INFORMATION = RegularChapter("公开披露的基金信息", re.compile(r"公开披露的基金信息$"))

    # 基金份额折算与变更登记
    FUND_PROPERTY_LIQUIDATION = RegularChapter(
        "基金合同的变更、终止与基金财产的清算",
        re.compile(
            rf"《?基金合同》?的?(?:(?:变更|终止|解除)[^{R_NOT_CONJUNCTION_PUNCTUATION}]*?){{2}}基金财产的?清算(?:方式)?$"
        ),
    )
    FUND_PROPERTY_LIQUIDATION_TERMINATION_CONTRACT = RegularChapter(
        "基金合同的终止事由", re.compile(r"《?基金合同》?的终止事由$")
    )
    FUND_PROPERTY_LIQUIDATION_CHANGE_CONTRACT = RegularChapter("基金合同的变更", re.compile(r"《?基金合同》?的?变更$"))

    # 违约责任
    FUND_BREAK_CONTACT_DUTY = RegularChapter("违约责任", re.compile(r"违约责任$"))

    # 基金合同的效力
    FUND_CONTRACT_VALIDITY = RegularChapter("基金合同的效力", re.compile(r"基金合同的效力$"))

    # 摘要章节：基金合同的效力/合同存放地和取得合同的方式
    FUND_CONTRACT_VALIDITY_OR_PLACE = RegularChapter(
        "基金合同的效力",
        re.compile(rf"(?:基金合同的效力|合同存放地[^{R_NOT_CONJUNCTION_PUNCTUATION}]*[获取]得(?:基金)?合同的方式)$"),
    )

    # 基金资产估值
    FUND_ASSET_VALUATION = RegularChapter("基金资产估值", re.compile(r"基金资产估值$"))
    FUND_SITUATION_VALUATION_SUSPENDED = RegularChapter("暂停估值的情形", re.compile(r"暂停估值的情形$"))
    FUND_ASSET_VALUATION_PROCEDURE = RegularChapter("估值程序", re.compile(r"估值程序$"))
    FUND_ASSET_VALUATION_OBJECT = RegularChapter("估值对象", re.compile(r"估值对象$"))
    FUND_ASSET_VALUATION_METHOD = RegularChapter("估值方法", re.compile(r"估值方法$"))
    FUND_ASSET_VALUATION_ERROR_HANDLING = RegularChapter("估值错误的处理", re.compile(r"估值错误的处理$"))
    FUND_ASSET_VALUATION_SIDE_ASSET_VALUATION = RegularChapter(
        "实施侧袋机制期间的基金资产估值", re.compile(r"实施侧袋机制期间的基金资产估值$")
    )
    FUND_ASSET_VALUATION_NET_VALUE = RegularChapter("基金净值的确认", re.compile(r"基金净值的确认$"))
    FUND_HANDLING_OF_SPECIAL_CASES = RegularChapter("特殊情况的处理", re.compile(r"特殊情况的处理$"))

    # 基金份额的登记
    FUND_REGISTER_PORTION = RegularChapter("基金份额的登记", re.compile(r"基金份额的登记$"))
    FUND_REGISTER_PORTION_INSTITUTION_RIGHT = RegularChapter("基金登记机构的权利", re.compile(r"基金登记机构的权利$"))

    # 释义
    FUND_PARAPHRASE = RegularChapter("释义", re.compile(r"释义$"))

    # 争议的处理和适用的法律
    FUND_PROCESSING_APPLICATION_LAW = RegularChapter(
        "争议的处理和适用的法律", re.compile(rf"争议的?(?:处理|解决方式)(?:[{R_CONJUNCTION}]适用的?法律)?$")
    )

    # 前言
    FUND_FOREWORD = RegularChapter("前言", re.compile(r"前言$"))
    FUND_FOREWORD_PURPOSE_BASED_PRINCIPLE = RegularChapter(
        "订立本基金合同的目的、依据和原则", re.compile(r"订立本基金合同的目的、依据和原则$")
    )

    # 基金的财产
    FUND_PROPERTY = RegularChapter("基金的财产", re.compile(r"基金的财产$"))

    FUND_PROPERTY_TOTAL_ASSETS = RegularChapter("基金资产总值", re.compile(r"(?:基金)?资产总值$"))
    FUND_PROPERTY_NET_ASSET_VALUE = RegularChapter("基金资产净值", re.compile(r"(?:基金)?资产净值$"))

    # 其他事项
    FUND_OTHER_MATTERS = RegularChapter("其他事项", re.compile(r"其他事项$"))

    # 基金合同摘要
    FUND_CONTRACT_DIGEST = RegularChapter("基金合同内容摘要", re.compile(r"合同(?:内容)?摘要$"))

    # 基金费用与税收（仅针对摘要中的费用与税收）
    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2138
    FUND_CONTRACT_DIGEST_BASIC_COST_REVENUE = RegularChapter(
        "基金费用与税收",
        re.compile(
            rf"基金的?(?:(?:(?:费用|税收)[{R_CONJUNCTION}]?){{1,2}}|(?:[^{R_NOT_CONJUNCTION_PUNCTUATION}]*?(?:费用的?提取|支付方式|比例)){{2,3}})$"
        ),
    )

    # 基金资产净值
    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1590#note_321462
    FUND_DIGEST_VALUE_CALCULATION_ANNOUNCEMENT_MODE = RegularChapter(
        "基金资产净值",
        re.compile(rf"(?:基金)?资产净值(?:的?计算方[法式][^{R_NOT_CONJUNCTION_PUNCTUATION}]*?公告方式)?$"),
    )

    # 基金资产净值计算方法和公告方式
    FUND_VALUE_CALCULATION_ANNOUNCEMENT_MODE = RegularChapter(
        "基金资产净值计算方法和公告方式",
        re.compile(rf"(?:基金)?资产净值的?计算方[法式][^{R_NOT_CONJUNCTION_PUNCTUATION}]*?公告方式$"),
    )

    # 基金资产估值/基金资产净值计算方法和公告方式
    FUND_ASSET_VALUATION_OR_VALUE_CALCULATION_ANNOUNCEMENT_MODE = RegularChapter(
        "基金资产估值",
        re.compile(
            rf"(?:基金)?资产净值的?计算方[法式][^{R_NOT_CONJUNCTION_PUNCTUATION}]*?公告方式$|(?:基金)?资产估值$"
        ),
    )

    # 承诺与声明
    FUND_COMMITMENTS_STATEMENTS = RegularChapter("承诺与声明", re.compile(rf"(?:(?:承诺|声明)[{R_CONJUNCTION}]?){{2}}"))

    # 资产管理计划的成立与备案
    ASSET_MANAGE_PLAN_ESTABLISHMENT_FILING = RegularChapter(
        "资产管理计划的成立与备案", re.compile(rf"资产管理计划的?成立{[R_CONJUNCTION]}备案")
    )

    # 资产管理计划的参与、退出与转让
    ASSET_MANAGE_PLAN_PARTICIPATION_WITHDRAWAL_TRANSFER = RegularChapter(
        "资产管理计划的参与、退出与转让", re.compile(rf"资产管理计划的?(?:(?:参与|退出|转让){[R_CONJUNCTION]}?){{3}}")
    )

    # 份额持有人大会及日常机构
    GENERAL_ASSEMBLY_DAILY_INSTITUTIONS = RegularChapter(
        "份额持有人大会及日常机构", re.compile(rf"份额持有人大会{[R_CONJUNCTION]}日常机构")
    )

    # 资产管理计划份额的登记
    ASSET_MANAGEMENT_PLAN_REGISTRATION = RegularChapter(
        "资产管理计划份额的登记", re.compile(r"资产管理计划份额的?登记")
    )

    # 资产管理计划的投资
    ASSET_MANAGEMENT_PLAN_INVEST = RegularChapter("资产管理计划的投资", re.compile(r"(资产)?管理计划的?投资$"))

    # 投资顾问（如有）
    ASSET_INVESTMENT_COUNSELOR = RegularChapter("投资顾问", re.compile(r"投资顾问(?:[（(]如有[）)])?$"))

    # 利益冲突及关联交易
    ASSET_CONFLICTS_INTEREST_RELATED_PARTY_TRANSACTIONS = RegularChapter(
        "利益冲突及关联交易", re.compile(r"利益冲突|关联交易")
    )

    # 资产管理计划的财产
    ASSET_MANAGEMENT_PLAN_PROPERTY = RegularChapter("资产管理计划的财产", re.compile(r"资产管理计划的?财产"))

    # 资产管理计划的募集
    ASSET_MANAGEMENT_PLAN_RAISE = RegularChapter("资产管理计划的募集", re.compile(r"资产管理计划的?募集$"))

    # 资产管理计划的基本情况
    ASSET_MANAGEMENT_PLAN_BASIC_INFO = RegularChapter(
        "资产管理计划的基本情况", re.compile(r"(资产)?管理计划的?基本情况$")
    )

    # 越权交易的界定
    ASSET_DEFINITION_ULTRA_VIRES_TRANSACTION = RegularChapter("越权交易的界定", re.compile(r"越权交易的?(处理|界定)$"))

    # 资产管理计划财产的估值和会计核算
    ASSET_MANAGEMENT_PLAN_VALUATION_ACCOUNTING_SETTLEMENT = RegularChapter(
        "资产管理计划财产的估值和会计核算", re.compile(r"资产管理计划财产的?(估值|会计核算)")
    )

    # 资产管理计划的费用与税收
    ASSET_MANAGEMENT_PLAN_FEES_TAXES = RegularChapter(
        r"资产管理计划的费用与税收", re.compile(rf"资产管理计划的?(?:(?:费用|税收)[{R_CONJUNCTION}]?){{2}}$")
    )

    # 当事人及权利义务
    ASSET_MANAGEMENT_PLAN_DUTY_POWER = RegularChapter(
        "当事人及权利义务", re.compile(rf"当事人[的{R_CONJUNCTION}](?:(权利|义务)[{R_CONJUNCTION}]?){{2}}")
    )

    # 信息披露与报告
    ASSET_DISCLOSURE_REPORTING = RegularChapter("信息披露与报告", re.compile(r"信息(披露|报告)$"))

    # 资产管理计划的收益分配
    ASSET_MANAGEMENT_PLAN_INCOME_DISTRIBUTION = RegularChapter(
        "资产管理计划的收益分配", re.compile(r"资产管理计划的?收益分配$")
    )

    # 投资指令的发送、确认和执行
    ASSET_ORDER_SEND_CONFIRMATION_EXECUTION = RegularChapter(
        "投资指令的发送、确认和执行", re.compile(rf"投资指令的?(?:(?:发送|确认|执行)[{R_CONJUNCTION}]?){{3}}")
    )

    # 风险揭示
    ASSET_DISCLOSURE_RISK = RegularChapter("风险揭示", re.compile(r"风险揭示$"))


@dataclass
class ChapterPattern:
    # 基金份额持有人大会
    CHAPTER_FUND_SHARE_HOLDER = ChapterRule([CatalogsPattern.FUND_SHARE_HOLDER]).convert2dict()

    # 基金份额持有人大会 -> 召集人及召集方式
    CHAPTER_FUND_SHARE_HOLDER_CONVENING_MODE = ChapterRule(
        [CatalogsPattern.FUND_SHARE_HOLDER, CatalogsPattern.FUND_SHARE_HOLDER_CONVENING_MODE]
    ).convert2dict()

    # 基金份额持有人大会 -> 计票
    CHAPTER_FUND_SHARE_HOLDER_COUNT_VOTE = ChapterRule(
        [CatalogsPattern.FUND_SHARE_HOLDER, CatalogsPattern.FUND_SHARE_HOLDER_COUNT_VOTE]
    ).convert2dict()

    # 基金份额持有人大会 -> 表决
    CHAPTER_FUND_SHARE_HOLDER_VOTE = ChapterRule(
        [CatalogsPattern.FUND_SHARE_HOLDER, CatalogsPattern.FUND_SHARE_HOLDER_VOTE]
    ).convert2dict()

    # 基金份额持有人大会 -> 份额持有人大会-召开通知
    CHAPTER_FUND_HOLDERS_MEETING = ChapterRule(
        [CatalogsPattern.FUND_SHARE_HOLDER, CatalogsPattern.FUND_SHARE_HOLDER_NOTIFY]
    ).convert2dict()

    # 基金份额持有人大会 -> 出席方式的补充约定
    CHAPTER_FUND_SHARE_HOLDER_SUPPLEMENTARY_AGREEMENT = ChapterRule(
        [CatalogsPattern.FUND_SHARE_HOLDER, CatalogsPattern.FUND_SHARE_HOLDER_SUPPLEMENTARY_AGREEMENT]
    ).convert2dict()

    # 基金份额持有人大会 -> 召开事由
    CHAPTER_FUND_SHARE_HOLDER_CAUSE = ChapterRule(
        [CatalogsPattern.FUND_SHARE_HOLDER, CatalogsPattern.FUND_SHARE_HOLDER_CAUSE]
    ).convert2dict()

    # 基金份额持有人大会 -> 份额持有人大会-出席方式
    CHAPTER_FUND_HOLDERS_ATTEND_MEETING = ChapterRule(
        [CatalogsPattern.FUND_SHARE_HOLDER, CatalogsPattern.FUND_SHARE_HOLDER_ATTEND]
    ).convert2dict()

    # 基金份额持有人大会 -> 份额持有人大会-一般规定
    CHAPTER_FUND_HOLDERS_GENERAL_PROVISIONS = ChapterRule(
        [CatalogsPattern.FUND_SHARE_HOLDER, CatalogsPattern.FUND_SHARE_HOLDER_GENERAL_PROVISIONS]
    ).convert2dict()

    # 基金份额持有人大会 -> 实施侧袋机制期间基金份额持有人大会的特殊约定
    CHAPTER_FUND_SHARE_HOLDER_SIDE_POCKET_CONVENTION = ChapterRule(
        [CatalogsPattern.FUND_SHARE_HOLDER, CatalogsPattern.FUND_SHARE_HOLDER_SIDE_POCKET_CONVENTION]
    ).convert2dict()

    # 基金份额持有人大会 -> 生效与公告
    CHAPTER_FUND_SHARE_HOLDER_TAKE_EFFECT_NOTICE = ChapterRule(
        [CatalogsPattern.FUND_SHARE_HOLDER, CatalogsPattern.FUND_SHARE_HOLDER_TAKE_EFFECT_NOTICE]
    ).convert2dict()

    # 基金份额持有人大会 -> 议事内容与程序
    CHAPTER_FUND_SHARE_HOLDER_CONTENT_PROCEDURE = ChapterRule(
        [CatalogsPattern.FUND_SHARE_HOLDER, CatalogsPattern.FUND_SHARE_HOLDER_CONTENT_PROCEDURE]
    ).convert2dict()

    # 基金的托管
    CHAPTER_FUND_TRUSTEESHIP = ChapterRule([CatalogsPattern.FUND_TRUSTEESHIP]).convert2dict()

    # 基金的投资
    CHAPTER_FUND_INVEST = ChapterRule([CatalogsPattern.FUND_INVEST]).convert2dict()

    # 基金的投资 -> 基金管理人代表基金行使股东或债权人权利的处理原则及方法
    CHAPTER_FUND_INVEST_PRINCIPLE = ChapterRule(
        [CatalogsPattern.FUND_INVEST, CatalogsPattern.FUND_INVEST_PRINCIPLE]
    ).convert2dict()

    # 基金的投资 -> 投资范围
    CHAPTER_FUND_INVEST_SCOPE_INVESTMENT = ChapterRule(
        [CatalogsPattern.FUND_INVEST, CatalogsPattern.FUND_INVEST_SCOPE_INVESTMENT]
    ).convert2dict()

    # 基金的投资 -> 投资限制
    CHAPTER_FUND_INVEST_SCOPE_INVESTMENT_RESTRICTION = ChapterRule(
        [CatalogsPattern.FUND_INVEST, CatalogsPattern.FUND_INVEST_SCOPE_INVESTMENT_RESTRICTION]
    ).convert2dict()

    # 基金的投资 -> 禁止行为
    CHAPTER_FUND_INVEST_SCOPE_FORBIDDING_ACT = ChapterRule(
        [CatalogsPattern.FUND_INVEST, CatalogsPattern.FUND_INVEST_SCOPE_FORBIDDING_ACT],
        is_continued_chapter=False,
    ).convert2dict()

    # 基金的投资 -> 业绩比较基准
    CHAPTER_FUND_INVEST_PERFORMANCE_COMPARISON_BASIS = ChapterRule(
        [CatalogsPattern.FUND_INVEST, CatalogsPattern.FUND_INVEST_PERFORMANCE_COMPARISON_BASIS]
    ).convert2dict()

    # 基金的投资 -> 侧袋机制的实施和投资运作安排
    CHAPTER_FUND_INVEST_SIDE_POCKET_MECHANISM_OPERATION = ChapterRule(
        [CatalogsPattern.FUND_INVEST, CatalogsPattern.FUND_INVEST_SIDE_POCKET_MECHANISM_OPERATION]
    ).convert2dict()

    # 基金的投资 -> 风险收益特征
    CHAPTER_FUND_INVEST_RISK_RETURN_CHARACTERISTICS = ChapterRule(
        [CatalogsPattern.FUND_INVEST, CatalogsPattern.FUND_INVEST_RISK_RETURN_CHARACTERISTICS]
    ).convert2dict()

    # 基金的投资 -> 投资策略
    CHAPTER_FUND_INVEST_INVESTMENT_STRATEGY = ChapterRule(
        [CatalogsPattern.FUND_INVEST, CatalogsPattern.FUND_INVEST_INVESTMENT_STRATEGY]
    ).convert2dict()

    # 基金管理人、基金托管人的更换条件和程序
    CHAPTER_FUND_REPLACEMENT_PROCEDURE = ChapterRule([CatalogsPattern.FUND_REPLACEMENT_PROCEDURE]).convert2dict()

    # 基金合同当事人权利与义务
    CHAPTER_FUND_RIGHT_OBLIGATION = ChapterRule([CatalogsPattern.FUND_RIGHT_OBLIGATION]).convert2dict()

    # 基金合同当事人权利与义务 -> 管理人的权利与义务
    CHAPTER_FUND_RIGHT_OBLIGATION_MANAGER_DUTY = ChapterRule(
        [CatalogsPattern.FUND_RIGHT_OBLIGATION, CatalogsPattern.FUND_RIGHT_OBLIGATION_MANAGER_DUTY],
        is_continued_chapter=False,
    ).convert2dict()

    # 基金合同当事人权利与义务 -> 托管人
    CHAPTER_FUND_RIGHT_OBLIGATION_TRUSTEE = ChapterRule(
        [CatalogsPattern.FUND_RIGHT_OBLIGATION, CatalogsPattern.FUND_RIGHT_OBLIGATION_TRUSTEE],
        is_continued_chapter=False,
    ).convert2dict()

    # 基金合同当事人权利与义务 -> 托管人的权利与义务
    CHAPTER_FUND_RIGHT_OBLIGATION_TRUSTEE_RIGHT_DUTY = ChapterRule(
        [CatalogsPattern.FUND_RIGHT_OBLIGATION, CatalogsPattern.FUND_RIGHT_OBLIGATION_TRUSTEE_RIGHT_DUTY],
        is_continued_chapter=False,
    ).convert2dict()

    # 基金合同当事人权利与义务 -> 份额持有人的义务
    CHAPTER_FUND_RIGHT_OBLIGATION_SHARE_HOLDER_DUTY = ChapterRule(
        [CatalogsPattern.FUND_RIGHT_OBLIGATION, CatalogsPattern.FUND_RIGHT_OBLIGATION_SHARE_HOLDER_DUTY],
        is_continued_chapter=False,
    ).convert2dict()

    # 基金合同当事人权利与义务 -> 份额持有人
    CHAPTER_FUND_RIGHT_OBLIGATION_SHARE_HOLDER = ChapterRule(
        [CatalogsPattern.FUND_RIGHT_OBLIGATION, CatalogsPattern.FUND_RIGHT_OBLIGATION_SHARE_HOLDER],
        is_continued_chapter=False,
    ).convert2dict()

    # 基金份额的发售
    CHAPTER_FUND_SELL = ChapterRule([CatalogsPattern.FUND_SELL]).convert2dict()

    # 基金份额的发售 -> 基金份额的发售时间、发售方式、发售对象
    CHAPTER_FUND_SELL_MODE = ChapterRule([CatalogsPattern.FUND_SELL, CatalogsPattern.FUND_SELL_MODE]).convert2dict()

    # 基金份额的发售 -> 基金份额的认购
    CHAPTER_FUND_SELL_SUBSCRIPTION = ChapterRule(
        [CatalogsPattern.FUND_SELL, CatalogsPattern.FUND_SELL_SUBSCRIPTION]
    ).convert2dict()

    # 基金份额的发售 -> 基金份额认购金额的限制
    CHAPTER_FUND_SELL_LIMIT = ChapterRule([CatalogsPattern.FUND_SELL, CatalogsPattern.FUND_SELL_LIMIT]).convert2dict()

    # 基金备案 -> 基金合同不能生效时募集资金的处理方式
    CHAPTER_FUND_RECORD_FAILURE_PROCESS_MODE = ChapterRule(
        [CatalogsPattern.FUND_RECORD, CatalogsPattern.FUND_RECORD_FAILURE_PROCESS_MODE]
    ).convert2dict()

    # 基金备案 -> 基金备案的条件
    CHAPTER_FUND_RECORD_CONDITIONS = ChapterRule(
        [CatalogsPattern.FUND_RECORD, CatalogsPattern.FUND_RECORD_CONDITIONS]
    ).convert2dict()

    # 基金备案 -> 基金存续期内的基金份额持有人数量和资产规模
    CHAPTER_FUND_RECORD_HOLDER_NUMBER_ASSET_SIZE = ChapterRule(
        [CatalogsPattern.FUND_RECORD, CatalogsPattern.FUND_RECORD_HOLDER_NUMBER_ASSET_SIZE]
    ).convert2dict()

    # 基金份额的申购与赎回
    CHAPTER_FUND_SUBSCRIPTION = ChapterRule([CatalogsPattern.FUND_SUBSCRIPTION]).convert2dict()

    # 基金份额的申购与赎回 -> 基金转换
    CHAPTER_FUND_SUBSCRIPTION_CONVERSION = ChapterRule(
        [CatalogsPattern.FUND_SUBSCRIPTION, CatalogsPattern.FUND_SUBSCRIPTION_CONVERSION]
    ).convert2dict()

    # 基金份额的申购与赎回 -> 申购和赎回的开放日及时间
    CHAPTER_FUND_SUBSCRIPTION_OPENDAY = ChapterRule(
        [CatalogsPattern.FUND_SUBSCRIPTION, CatalogsPattern.FUND_SUBSCRIPTION_OPENDAY]
    ).convert2dict()

    # 基金份额的申购与赎回 -> 申购和赎回的场所
    CHAPTER_FUND_SUBSCRIPTION_PLACE = ChapterRule(
        [CatalogsPattern.FUND_SUBSCRIPTION, CatalogsPattern.FUND_SUBSCRIPTION_PLACE]
    ).convert2dict()

    # 基金份额的申购与赎回 -> 申购与赎回的原则
    CHAPTER_FUND_SUBSCRIPTION_PRINCIPLE = ChapterRule(
        [CatalogsPattern.FUND_SUBSCRIPTION, CatalogsPattern.FUND_SUBSCRIPTION_PRINCIPLE]
    ).convert2dict()

    # 基金份额的申购与赎回 -> 申购和赎回的数量限制
    CHAPTER_FUND_SUBSCRIPTION_COUNT_LIMIT = ChapterRule(
        [CatalogsPattern.FUND_SUBSCRIPTION, CatalogsPattern.FUND_SUBSCRIPTION_COUNT_LIMIT]
    ).convert2dict()

    # 基金份额的申购与赎回 -> 暂停申购或赎回的公告和重新开放申购或赎回的公告
    CHAPTER_FUND_SUBSCRIPTION_PAUSE_OR_REOPEN = ChapterRule(
        [CatalogsPattern.FUND_SUBSCRIPTION, CatalogsPattern.FUND_SUBSCRIPTION_PAUSE_OR_REOPEN]
    ).convert2dict()

    # 基金份额的申购与赎回 -> 实施侧袋机制期间本基金的申购与赎回
    CHAPTER_FUND_SUBSCRIPTION_IMPLEMENT = ChapterRule(
        [CatalogsPattern.FUND_SUBSCRIPTION, CatalogsPattern.FUND_SUBSCRIPTION_IMPLEMENT]
    ).convert2dict()

    # 基金份额的申购与赎回 -> 申购与赎回的程序
    CHAPTER_FUND_SUBSCRIPTION_PROCEDURE = ChapterRule(
        [CatalogsPattern.FUND_SUBSCRIPTION, CatalogsPattern.FUND_SUBSCRIPTION_PROCEDURE]
    ).convert2dict()

    # 基金份额的申购与赎回 -> 基金的转托管
    CHAPTER_FUND_SUBSCRIPTION_TRANSFER_CUSTODY = ChapterRule(
        [CatalogsPattern.FUND_SUBSCRIPTION, CatalogsPattern.FUND_SUBSCRIPTION_TRANSFER_CUSTODY]
    ).convert2dict()

    # 基金份额的申购与赎回 -> 基金的非交易过户
    CHAPTER_FUND_SUBSCRIPTION_NON_TRANSACTION_TRANSFER = ChapterRule(
        [CatalogsPattern.FUND_SUBSCRIPTION, CatalogsPattern.FUND_SUBSCRIPTION_NON_TRANSACTION_TRANSFER]
    ).convert2dict()

    # 基金份额的申购与赎回 -> 申购和赎回的价格、费用及其用途
    CHAPTER_FUND_SUBSCRIPTION_PRICE_EXPENSE_PURPOSE = ChapterRule(
        [CatalogsPattern.FUND_SUBSCRIPTION, CatalogsPattern.FUND_SUBSCRIPTION_PRICE_EXPENSE_PURPOSE]
    ).convert2dict()

    # 基金份额的申购与赎回 -> 拒绝或暂停申购的情形
    CHAPTER_FUND_SUBSCRIPTION_REJECT_SUSPEND_SUBSCRIBE = ChapterRule(
        [CatalogsPattern.FUND_SUBSCRIPTION, CatalogsPattern.FUND_SUBSCRIPTION_REJECT_SUSPEND_SUBSCRIBE]
    ).convert2dict()

    # 基金份额的申购与赎回 -> 暂停赎回或延缓支付赎回款项的情形
    CHAPTER_FUND_SUBSCRIPTION_SUSPEND_RANSOM_PAY = ChapterRule(
        [CatalogsPattern.FUND_SUBSCRIPTION, CatalogsPattern.FUND_SUBSCRIPTION_SUSPEND_RANSOM_PAY]
    ).convert2dict()

    # 基金份额的申购与赎回 -> 巨额赎回的情形及处理方式
    CHAPTER_FUND_SUBSCRIPTION_HUGE_REDEMPTION = ChapterRule(
        [CatalogsPattern.FUND_SUBSCRIPTION, CatalogsPattern.FUND_SUBSCRIPTION_HUGE_REDEMPTION]
    ).convert2dict()

    # 基金份额折算与变更登记 -> 基金份额折算与变更登记
    CHAPTER_FUND_BASIC_CONVERSION_CHANGE = ChapterRule([CatalogsPattern.FUND_BASIC_CONVERSION_CHANGE]).convert2dict()

    # 基金的基本情况
    CHAPTER_FUND_BASIC_INFORMATION = ChapterRule([CatalogsPattern.FUND_BASIC_INFORMATION]).convert2dict()

    # 基金的基本情况 -> 基金份额面值和认购费用
    CHAPTER_FUND_BASIC_INFORMATION_FACE_VALUE_SUBSCRIBE = ChapterRule(
        [CatalogsPattern.FUND_BASIC_INFORMATION, CatalogsPattern.FUND_BASIC_INFORMATION_FACE_VALUE_SUBSCRIBE]
    ).convert2dict()

    # 基金的基本情况 -> 基金份额面值和认购费用
    CHAPTER_FUND_BASIC_INFORMATION_MINIMUM_TOTAL_AMOUNT_RAISED = ChapterRule(
        [CatalogsPattern.FUND_BASIC_INFORMATION, CatalogsPattern.FUND_BASIC_INFORMATION_MINIMUM_TOTAL_AMOUNT_RAISED]
    ).convert2dict()

    # 基金的基本情况 -> 基金的标的指数
    CHAPTER_FUND_BASIC_INFORMATION_STANDARD_INDEX = ChapterRule(
        [CatalogsPattern.FUND_BASIC_INFORMATION, CatalogsPattern.FUND_BASIC_INFORMATION_STANDARD_INDEX]
    ).convert2dict()

    # 基金的基本情况 -> 联接基金
    CHAPTER_FUND_BASIC_INFORMATION_INVESTMENT_OBJECTIVE = ChapterRule(
        [CatalogsPattern.FUND_BASIC_INFORMATION, CatalogsPattern.FUND_BASIC_INFORMATION_INVESTMENT_OBJECTIVE]
    ).convert2dict()

    # 基金的基本情况 -> 基金的类别
    CHAPTER_FUND_TYPES_OF_FUNDS = ChapterRule(
        [CatalogsPattern.FUND_BASIC_INFORMATION, CatalogsPattern.FUND_TYPES_OF_FUNDS]
    ).convert2dict()

    # 基金的基本情况 -> 投资比例、投资限制
    CHAPTER_FUND_INVESTMENT_RESTRICTION = ChapterRule(
        [CatalogsPattern.FUND_BASIC_INFORMATION, CatalogsPattern.FUND_INVESTMENT_RESTRICTION]
    ).convert2dict()

    # 基金费用与税收
    CHAPTER_FUND_BASIC_COST_REVENUE = ChapterRule([CatalogsPattern.FUND_BASIC_COST_REVENUE]).convert2dict()

    # 基金费用与税收 -> 基金的税收
    CHAPTER_FUND_BASIC_REVENUE = ChapterRule(
        [CatalogsPattern.FUND_BASIC_COST_REVENUE, CatalogsPattern.FUND_BASIC_REVENUE]
    ).convert2dict()

    # 基金费用与税收 -> 基金费用的种类
    CHAPTER_FUND_BASIC_EXPENSE_TYPES = ChapterRule(
        [CatalogsPattern.FUND_BASIC_COST_REVENUE, CatalogsPattern.FUND_BASIC_EXPENSE_TYPES]
    ).convert2dict()

    # 基金费用与税收 -> 不列入基金费用的项目
    CHAPTER_FUND_BASIC_ITEMS_NOT_INCLUDED_FUND_COSTS = ChapterRule(
        [CatalogsPattern.FUND_BASIC_COST_REVENUE, CatalogsPattern.FUND_BASIC_ITEMS_NOT_INCLUDED_FUND_COSTS]
    ).convert2dict()

    # 基金费用与税收 -> 实施侧袋机制期间的基金费用
    CHAPTER_FUND_EXPENSES_DURING_IMPLEMENTATION_SIDE_POCKET_MECHANISM = ChapterRule(
        [
            CatalogsPattern.FUND_BASIC_COST_REVENUE,
            CatalogsPattern.FUND_EXPENSES_DURING_IMPLEMENTATION_SIDE_POCKET_MECHANISM,
        ]
    ).convert2dict()

    # 基金费用与税收 -> 基金费用计提方法、计提标准和支付方式
    CHAPTER_FUND_EXPENSES_STANDARD_METHOD_CALCULATION_MODE_PAYMENT = ChapterRule(
        [
            CatalogsPattern.FUND_BASIC_COST_REVENUE,
            CatalogsPattern.FUND_EXPENSES_STANDARD_METHOD_CALCULATION_MODE_PAYMENT,
        ]
    ).convert2dict()

    # 基金费用与税收 -> C类基金份额的销售服务费
    CHAPTER_FUND_C_CLASS_SALES_SERVICE_FEE = ChapterRule(
        [CatalogsPattern.FUND_BASIC_COST_REVENUE, CatalogsPattern.FUND_C_CLASS_SALES_SERVICE_FEE],
        is_continued_chapter=False,
    ).convert2dict()

    # 基金费用与税收 -> 基金管理人的托管费
    CHAPTER_FUND_MANAGER_TRUSTEE_FEE = ChapterRule(
        [CatalogsPattern.FUND_BASIC_COST_REVENUE, CatalogsPattern.FUND_MANAGER_TRUSTEE_FEE],
        is_continued_chapter=False,
    ).convert2dict()

    # 基金费用与税收 -> 基金管理人的管理费
    CHAPTER_FUND_MANAGER_ADMINISTRATIVE_FEE = ChapterRule(
        [CatalogsPattern.FUND_BASIC_COST_REVENUE, CatalogsPattern.FUND_MANAGER_ADMINISTRATIVE_FEE],
        is_continued_chapter=False,
    ).convert2dict()

    # 基金的信息披露
    CHAPTER_FUND_INFORMATION_DISCLOSURE = ChapterRule([CatalogsPattern.FUND_INFORMATION_DISCLOSURE]).convert2dict()

    # 基金的信息披露 -> 投资品种相关公告
    CHAPTER_FUND_BASIC_INVESTMENT_VARIETY = ChapterRule(
        [CatalogsPattern.FUND_INFORMATION_DISCLOSURE, CatalogsPattern.FUND_BASIC_INVESTMENT_VARIETY]
    ).convert2dict()

    # 基金的信息披露 -> 暂停或延迟信息披露的情形
    CHAPTER_FUND_INFORMATION_DISCLOSURE_PAUSE = ChapterRule(
        [CatalogsPattern.FUND_INFORMATION_DISCLOSURE, CatalogsPattern.FUND_INFORMATION_DISCLOSURE_PAUSE]
    ).convert2dict()

    # 基金的信息披露 -> 临时报告
    CHAPTER_FUND_INFORMATION_DISCLOSURE_PROVISIONAL_REPORT = ChapterRule(
        [CatalogsPattern.FUND_INFORMATION_DISCLOSURE, CatalogsPattern.FUND_INFORMATION_DISCLOSURE_PROVISIONAL_REPORT],
        is_continued_chapter=False,
    ).convert2dict()

    # 基金的信息披露 -> 公开披露的基金信息
    CHAPTER_FUND_PUBLICLY_DISCLOSED_FUND_INFORMATION = ChapterRule(
        [CatalogsPattern.FUND_INFORMATION_DISCLOSURE, CatalogsPattern.FUND_PUBLICLY_DISCLOSED_FUND_INFORMATION],
        is_continued_chapter=False,
    ).convert2dict()

    # 基金的收益与分配
    CHAPTER_FUND_INCOME_ALLOCATION = ChapterRule([CatalogsPattern.FUND_INCOME_ALLOCATION]).convert2dict()

    # 基金的收益与分配 -> 货币基金的收益分配原则
    CHAPTER_FUND_INCOME_ALLOCATION_PRINCIPLE = ChapterRule(
        [CatalogsPattern.FUND_INCOME_ALLOCATION, CatalogsPattern.FUND_INCOME_ALLOCATION_PRINCIPLE]
    ).convert2dict()

    # 基金的会计与审计
    CHAPTER_FUND_ACCOUNTING_AND_AUDITING = ChapterRule([CatalogsPattern.FUND_ACCOUNTING_AND_AUDITING]).convert2dict()

    # 基金合同的变更、终止与基金财产的清算 -> 基金合同的终止事由
    CHAPTER_FUND_PROPERTY_LIQUIDATION_TERMINATION_CONTRACT = ChapterRule(
        [CatalogsPattern.FUND_PROPERTY_LIQUIDATION, CatalogsPattern.FUND_PROPERTY_LIQUIDATION_TERMINATION_CONTRACT]
    ).convert2dict()

    # 基金合同的变更、终止与基金财产的清算 -> 基金合同的变更
    CHAPTER_FUND_PROPERTY_LIQUIDATION_CHANGE_CONTRACT = ChapterRule(
        [CatalogsPattern.FUND_PROPERTY_LIQUIDATION, CatalogsPattern.FUND_PROPERTY_LIQUIDATION_CHANGE_CONTRACT]
    ).convert2dict()

    # 基金合同的变更、终止与基金财产的清算
    CHAPTER_FUND_PROPERTY_LIQUIDATION = ChapterRule([CatalogsPattern.FUND_PROPERTY_LIQUIDATION]).convert2dict()

    # 违约责任
    CHAPTER_FUND_BREAK_CONTACT_DUTY = ChapterRule([CatalogsPattern.FUND_BREAK_CONTACT_DUTY]).convert2dict()

    # 基金合同的效力
    CHAPTER_FUND_CONTRACT_VALIDITY = ChapterRule([CatalogsPattern.FUND_CONTRACT_VALIDITY]).convert2dict()

    # 基金份额的上市交易
    CHAPTER_FUND_LISTED_LISTED_TRANSACTION = ChapterRule(
        [CatalogsPattern.FUND_LISTED_LISTED_TRANSACTION]
    ).convert2dict()

    # 基金资产估值
    CHAPTER_FUND_ASSET_VALUATION = ChapterRule([CatalogsPattern.FUND_ASSET_VALUATION]).convert2dict()

    # 基金资产估值 -> 估值程序
    CHAPTER_FUND_ASSET_VALUATION_PROCEDURE = ChapterRule(
        [CatalogsPattern.FUND_ASSET_VALUATION, CatalogsPattern.FUND_ASSET_VALUATION_PROCEDURE]
    ).convert2dict()

    # 基金资产估值 -> 估值方法
    CHAPTER_FUND_ASSET_VALUATION_METHOD = ChapterRule(
        [CatalogsPattern.FUND_ASSET_VALUATION, CatalogsPattern.FUND_ASSET_VALUATION_METHOD]
    ).convert2dict()

    # 基金资产估值 -> 估值错误的处理
    CHAPTER_FUND_ASSET_VALUATION_ERROR_HANDLING = ChapterRule(
        [CatalogsPattern.FUND_ASSET_VALUATION, CatalogsPattern.FUND_ASSET_VALUATION_ERROR_HANDLING]
    ).convert2dict()

    # 基金资产估值 -> 暂停估值的情形
    CHAPTER_FUND_SITUATION_VALUATION_SUSPENDED = ChapterRule(
        [CatalogsPattern.FUND_ASSET_VALUATION, CatalogsPattern.FUND_SITUATION_VALUATION_SUSPENDED]
    ).convert2dict()

    # 基金资产估值 -> 实施侧袋机制期间的基金资产估值
    CHAPTER_FUND_ASSET_VALUATION_SIDE_ASSET_VALUATION = ChapterRule(
        [CatalogsPattern.FUND_ASSET_VALUATION, CatalogsPattern.FUND_ASSET_VALUATION_SIDE_ASSET_VALUATION]
    ).convert2dict()

    # 基金资产估值 -> 基金净值的确认
    CHAPTER_FUND_ASSET_VALUATION_NET_VALUE = ChapterRule(
        [CatalogsPattern.FUND_ASSET_VALUATION, CatalogsPattern.FUND_ASSET_VALUATION_NET_VALUE]
    ).convert2dict()

    # 基金资产估值 -> 特殊情况的处理
    CHAPTER_FUND_HANDLING_OF_SPECIAL_CASES = ChapterRule(
        [CatalogsPattern.FUND_ASSET_VALUATION, CatalogsPattern.FUND_HANDLING_OF_SPECIAL_CASES]
    ).convert2dict()

    # 基金的份额登记
    CHAPTER_FUND_REGISTER_PORTION = ChapterRule([CatalogsPattern.FUND_REGISTER_PORTION]).convert2dict()
    # 基金的份额登记 -> 基金登记机构的权利
    CHAPTER_FUND_REGISTER_PORTION_INSTITUTION_RIGHT = ChapterRule(
        [CatalogsPattern.FUND_REGISTER_PORTION, CatalogsPattern.FUND_REGISTER_PORTION_INSTITUTION_RIGHT]
    ).convert2dict()

    # 释义
    CHAPTER_FUND_PARAPHRASE = ChapterRule([CatalogsPattern.FUND_PARAPHRASE]).convert2dict()

    # 争议的处理和适用的法律
    CHAPTER_FUND_PROCESSING_APPLICATION_LAW = ChapterRule(
        [CatalogsPattern.FUND_PROCESSING_APPLICATION_LAW]
    ).convert2dict()

    # 前言
    CHAPTER_FUND_FOREWORD = ChapterRule([CatalogsPattern.FUND_FOREWORD]).convert2dict()

    # 前言 -> 订立本基金合同的目的、依据和原则
    CHAPTER_FUND_FOREWORD_PURPOSE_BASED_PRINCIPLE = ChapterRule(
        [CatalogsPattern.FUND_FOREWORD, CatalogsPattern.FUND_FOREWORD_PURPOSE_BASED_PRINCIPLE]
    ).convert2dict()

    # 基金的财产
    CHAPTER_FUND_PROPERTY = ChapterRule([CatalogsPattern.FUND_PROPERTY]).convert2dict()

    # 其他事项
    CHAPTER_FUND_OTHER_MATTERS = ChapterRule([CatalogsPattern.FUND_OTHER_MATTERS]).convert2dict()

    # 合同摘要-基金的收益与分配
    CHAPTER_FUND_CONTRACT_DIGEST_INCOME_ALLOCATION = ChapterRule(
        [CatalogsPattern.FUND_CONTRACT_DIGEST, CatalogsPattern.FUND_INCOME_ALLOCATION]
    ).convert2dict()

    # 合同摘要-基金的费用与税收
    CHAPTER_FUND_CONTRACT_DIGEST_COST_REVENUE = ChapterRule(
        [CatalogsPattern.FUND_CONTRACT_DIGEST, CatalogsPattern.FUND_CONTRACT_DIGEST_BASIC_COST_REVENUE]
    ).convert2dict()

    # 合同摘要-基金合同的变更、终止与基金财产的清算
    CHAPTER_FUND_CONTRACT_DIGEST_PROPERTY_LIQUIDATION = ChapterRule(
        [CatalogsPattern.FUND_CONTRACT_DIGEST, CatalogsPattern.FUND_PROPERTY_LIQUIDATION]
    ).convert2dict()

    # 合同摘要-争议的处理
    CHAPTER_FUND_CONTRACT_DIGEST_PROCESSING_APPLICATION_LAW = ChapterRule(
        [CatalogsPattern.FUND_CONTRACT_DIGEST, CatalogsPattern.FUND_PROCESSING_APPLICATION_LAW]
    ).convert2dict()

    # 合同摘要-基金份额持有人大会召集、议事及表决的程序和规则
    CHAPTER_FUND_CONTRACT_DIGEST_SHARE_HOLDER = ChapterRule(
        [CatalogsPattern.FUND_CONTRACT_DIGEST, CatalogsPattern.FUND_SHARE_HOLDER]
    ).convert2dict()

    # 合同摘要-基金合同的效力/合同存放地和取得合同的方式
    CHAPTER_FUND_CONTRACT_DIGEST_CONTRACT_VALIDITY = ChapterRule(
        [CatalogsPattern.FUND_CONTRACT_DIGEST, CatalogsPattern.FUND_CONTRACT_VALIDITY_OR_PLACE]
    ).convert2dict()

    # 承诺与声明
    CHAPTER_FUND_COMMITMENTS_STATEMENTS = ChapterRule([CatalogsPattern.FUND_COMMITMENTS_STATEMENTS]).convert2dict()

    # 资产管理计划的成立与备案
    CHAPTER_ASSET_MANAGE_PLAN_ESTABLISHMENT_FILING = ChapterRule(
        [CatalogsPattern.ASSET_MANAGE_PLAN_ESTABLISHMENT_FILING]
    ).convert2dict()

    # 资产管理计划的参与、退出与转让
    CHAPTER_ASSET_MANAGE_PLAN_PARTICIPATION_WITHDRAWAL_TRANSFER = ChapterRule(
        [CatalogsPattern.ASSET_MANAGE_PLAN_PARTICIPATION_WITHDRAWAL_TRANSFER]
    ).convert2dict()

    # 份额持有人大会及日常机构
    CHAPTER_GENERAL_ASSEMBLY_DAILY_INSTITUTIONS = ChapterRule(
        [CatalogsPattern.GENERAL_ASSEMBLY_DAILY_INSTITUTIONS]
    ).convert2dict()

    # 资产管理计划份额的登记
    CHAPTER_ASSET_MANAGEMENT_PLAN_REGISTRATION = ChapterRule(
        [CatalogsPattern.ASSET_MANAGEMENT_PLAN_REGISTRATION]
    ).convert2dict()

    # 资产管理计划的投资
    CHAPTER_ASSET_MANAGEMENT_PLAN_INVEST = ChapterRule([CatalogsPattern.ASSET_MANAGEMENT_PLAN_INVEST]).convert2dict()

    # 投资顾问（如有）
    CHAPTER_ASSET_INVESTMENT_COUNSELOR = ChapterRule([CatalogsPattern.ASSET_INVESTMENT_COUNSELOR]).convert2dict()

    # 利益冲突及关联交易
    CHAPTER_ASSET_CONFLICTS_INTEREST_RELATED_PARTY_TRANSACTIONS = ChapterRule(
        [CatalogsPattern.ASSET_CONFLICTS_INTEREST_RELATED_PARTY_TRANSACTIONS]
    ).convert2dict()

    # 资产管理计划的财产
    CHAPTER_ASSET_MANAGEMENT_PLAN_PROPERTY = ChapterRule(
        [CatalogsPattern.ASSET_MANAGEMENT_PLAN_PROPERTY]
    ).convert2dict()

    # 越权交易的界定
    CHAPTER_ASSET_DEFINITION_ULTRA_VIRES_TRANSACTION = ChapterRule(
        [CatalogsPattern.ASSET_DEFINITION_ULTRA_VIRES_TRANSACTION]
    ).convert2dict()

    # 资产管理计划财产的估值和会计核算
    CHAPTER_ASSET_MANAGEMENT_PLAN_VALUATION_ACCOUNTING_SETTLEMENT = ChapterRule(
        [CatalogsPattern.ASSET_MANAGEMENT_PLAN_VALUATION_ACCOUNTING_SETTLEMENT]
    ).convert2dict()

    # 资产管理计划的费用与税收
    CHAPTER_ASSET_MANAGEMENT_PLAN_FEES_TAXES = ChapterRule(
        [CatalogsPattern.ASSET_MANAGEMENT_PLAN_FEES_TAXES]
    ).convert2dict()

    # 当事人及权利义务
    CHAPTER_ASSET_MANAGEMENT_PLAN_DUTY_POWER = ChapterRule(
        [CatalogsPattern.ASSET_MANAGEMENT_PLAN_DUTY_POWER]
    ).convert2dict()

    # 信息披露与报告
    CHAPTER_ASSET_DISCLOSURE_REPORTING = ChapterRule([CatalogsPattern.ASSET_DISCLOSURE_REPORTING]).convert2dict()

    # 资产管理计划的募集
    CHAPTER_ASSET_MANAGEMENT_PLAN_RAISE = ChapterRule([CatalogsPattern.ASSET_MANAGEMENT_PLAN_RAISE]).convert2dict()

    # 资产管理计划的基本情况
    CHAPTER_ASSET_MANAGEMENT_PLAN_BASIC_INFO = ChapterRule(
        [CatalogsPattern.ASSET_MANAGEMENT_PLAN_BASIC_INFO]
    ).convert2dict()


@dataclass
class CustodyCatalogsPattern:
    """
    托管协议目录正则
    """

    FUND_CUSTODY_PARTIES = RegularChapter("基金托管协议当事人", re.compile(r"基金托管协议当事人$"))
    FUND_CUSTODY_FUND_TRUSTEE = RegularChapter("基金托管人", re.compile(r"基金托管人$"))

    FUND_CUSTODY_BASIS_PURPOSE_PRINCIPLE = RegularChapter(
        "基金托管协议的依据、目的和原则", re.compile(rf"基金托管协议的(?:(?:依据|目的|原则)[{R_CONJUNCTION}]?){{3}}$")
    )

    # 基金托管人对基金管理人的业务监督和核查
    FUND_TRUSTEE_CONDUCTOR_INSPECT_SUPERVISION = RegularChapter(
        "基金托管人对基金管理人的业务监督和核查",
        re.compile(rf"基金托管人对基金管理人的业务(?:(?:监督|核查)[{R_CONJUNCTION}]?){{2}}$"),
    )
    FUND_INVEST_SCOPE_INVESTMENT = RegularChapter("投资范围", re.compile(r"投资范围"))

    FUND_TRUSTEE_OPERATIONAL_VERIFICATION = RegularChapter(
        "基金管理人对基金托管人的业务核查", re.compile(r"基金管理人对基金托管人的业务核查$")
    )

    FUND_CUSTODY_PROPERTY = RegularChapter("基金财产的保管", re.compile(r"基金财产的?保管$"))

    FUND_INSTRUCTIONS_SEND_VERIFY_EXECUTE = RegularChapter(
        "指令的发送、确认和执行", re.compile(rf"指令?(?:(?:发送|确认|执行)[{R_CONJUNCTION}]?){{3}}$")
    )

    FUND_TRADING_CLEARING_SETTLEMENT_ARRANGEMENT = RegularChapter(
        "交易及清算交收安排", re.compile(rf"交易[{R_CONJUNCTION}]清算交收安排$")
    )

    # 基金资产净值计算和会计核算
    FUND_NET_ASSET_VALUE_CALCULATION_ACCOUNTING = RegularChapter(
        "基金资产净值计算和会计核算", re.compile(rf"基金(?:(?:资产净值计算|会计核算)[{R_CONJUNCTION}]?){{2}}$")
    )
    FUND_OBJECT_VALUATION = RegularChapter("估值对象", re.compile(r"估值对象"))

    # 基金收益分配
    FUND_INCOME_DISTRIBUTION = RegularChapter("基金收益分配", re.compile(r"基金收益分配$"))

    # 基金费用
    FUND_EXPENSES = RegularChapter("基金费用", re.compile(r"基金费用$"))

    # 基金份额持有人名册的保管
    FUND_UNIT_HOLDER_LIST_CUSTODY = RegularChapter(
        "基金份额持有人名册的保管", re.compile(r"基金份额持有人名册的?保管$")
    )

    # 基金有关文件档案的保存
    FUND_DOCUMENT_SAVING = RegularChapter("基金有关文件档案的保存", re.compile(r"基金有关文件档案的?保存$"))

    # 基金管理人和基金托管人的更换
    FUND_ADMINISTRATOR_CUSTODIAN_CHANGE = RegularChapter(
        "基金管理人和基金托管人的更换", re.compile(rf"(?:(?:基金管理人|基金托管人)[{R_CONJUNCTION}]?){{2}}的?更换$")
    )

    # 禁止行为
    FUND_PROHIBITED_ACTIONS = RegularChapter("禁止行为", re.compile(r"禁止行为$"))

    # 基金托管协议的变更、终止与基金财产的清算
    FUND_CUSTODY_CHANGE_DISCHARGE_LIQUIDATION_OF_PROPERTY = RegularChapter(
        "基金托管协议的变更、终止与基金财产的清算",
        re.compile(rf"基金托管协议的(?:(?:变更|终止)[{R_CONJUNCTION}]?){{2}}[{R_CONJUNCTION}]基金财产的清算$"),
    )

    # 违约责任
    FUND_RESPONSIBILITY_FOR_BREACH_OF_CONTRACT = RegularChapter("违约责任", re.compile(r"违约责任$"))

    # 争议解决方式
    FUND_DISPUTE_RESOLUTION = RegularChapter("争议解决方式", re.compile(r"争议解决方式$"))

    # 基金托管协议的效力
    FUND_VALIDITY_CUSTODY_AGREEMENT = RegularChapter("基金托管协议的效力", re.compile(r"基金托管协议的?效力$"))

    # 其他事项
    FUND_OTHER_BUSINESS = RegularChapter("其他事项", re.compile(r"其他事项$"))

    # 基金托管协议的签订
    FUND_SIGNING_OF_CUSTODY_AGREEMENT = RegularChapter("基金托管协议的签订", re.compile(r"基金托管协议的签订$"))


@dataclass
class CustodyChapterPattern:
    # 基金托管协议当事人 -> 基金托管人
    CHAPTER_FUND_CUSTODY_FUND_TRUSTEE = ChapterRule(
        [CustodyCatalogsPattern.FUND_CUSTODY_PARTIES, CustodyCatalogsPattern.FUND_CUSTODY_FUND_TRUSTEE]
    ).convert2dict()

    # 基金托管协议的依据、目的和原则
    CHAPTER_FUND_CUSTODY_BASIS_PURPOSE_PRINCIPLE = ChapterRule(
        [CustodyCatalogsPattern.FUND_CUSTODY_BASIS_PURPOSE_PRINCIPLE]
    ).convert2dict()

    # 基金托管人对基金管理人的业务监督和核查
    CHAPTER_FUND_TRUSTEE_CONDUCTOR_INSPECT_SUPERVISION = ChapterRule(
        [CustodyCatalogsPattern.FUND_TRUSTEE_CONDUCTOR_INSPECT_SUPERVISION]
    ).convert2dict()

    # 基金托管人对基金管理人的业务监督和核查 -> 投资范围
    CHAPTER_FUND_INVEST_SCOPE_INVESTMENT = ChapterRule(
        [
            CustodyCatalogsPattern.FUND_TRUSTEE_CONDUCTOR_INSPECT_SUPERVISION,
            CustodyCatalogsPattern.FUND_INVEST_SCOPE_INVESTMENT,
        ]
    ).convert2dict()

    # 基金管理人对基金托管人的业务核查
    CHAPTER_FUND_TRUSTEE_OPERATIONAL_VERIFICATION = ChapterRule(
        [CustodyCatalogsPattern.FUND_TRUSTEE_OPERATIONAL_VERIFICATION]
    ).convert2dict()

    # 基金财产的保管
    CHAPTER_FUND_CUSTODY_PROPERTY = ChapterRule([CustodyCatalogsPattern.FUND_CUSTODY_PROPERTY]).convert2dict()

    # 指令的发送、确认和执行
    CHAPTER_FUND_INSTRUCTIONS_SEND_VERIFY_EXECUTE = ChapterRule(
        [CustodyCatalogsPattern.FUND_INSTRUCTIONS_SEND_VERIFY_EXECUTE]
    ).convert2dict()

    # 交易及清算交收安排
    CHAPTER_FUND_TRADING_CLEARING_SETTLEMENT_ARRANGEMENT = ChapterRule(
        [CustodyCatalogsPattern.FUND_TRADING_CLEARING_SETTLEMENT_ARRANGEMENT]
    ).convert2dict()

    # 基金资产净值计算和会计核算
    CHAPTER_FUND_NET_ASSET_VALUE_CALCULATION_ACCOUNTING = ChapterRule(
        [CustodyCatalogsPattern.FUND_NET_ASSET_VALUE_CALCULATION_ACCOUNTING]
    ).convert2dict()

    # 估值对象
    CHAPTER_FUND_OBJECT_VALUATION = ChapterRule(
        [
            CustodyCatalogsPattern.FUND_NET_ASSET_VALUE_CALCULATION_ACCOUNTING,
            CustodyCatalogsPattern.FUND_OBJECT_VALUATION,
        ],
        is_continued_chapter=False,
    ).convert2dict()

    # 基金收益分配
    CHAPTER_FUND_INCOME_DISTRIBUTION = ChapterRule([CustodyCatalogsPattern.FUND_INCOME_DISTRIBUTION]).convert2dict()

    # 基金费用
    CHAPTER_FUND_EXPENSES = ChapterRule([CustodyCatalogsPattern.FUND_EXPENSES]).convert2dict()

    # 基金份额持有人名册的保管
    CHAPTER_FUND_UNIT_HOLDER_LIST_CUSTODY = ChapterRule(
        [CustodyCatalogsPattern.FUND_UNIT_HOLDER_LIST_CUSTODY]
    ).convert2dict()

    # 基金有关文件档案的保存
    CHAPTER_FUND_DOCUMENT_SAVING = ChapterRule([CustodyCatalogsPattern.FUND_DOCUMENT_SAVING]).convert2dict()

    # 基金管理人和基金托管人的更换
    CHAPTER_FUND_ADMINISTRATOR_CUSTODIAN_CHANGE = ChapterRule(
        [CustodyCatalogsPattern.FUND_ADMINISTRATOR_CUSTODIAN_CHANGE]
    ).convert2dict()

    # 禁止行为
    CHAPTER_FUND_PROHIBITED_ACTIONS = ChapterRule([CustodyCatalogsPattern.FUND_PROHIBITED_ACTIONS]).convert2dict()

    # 基金托管协议的变更、终止与基金财产的清算
    CHAPTER_FUND_CUSTODY_CHANGE_DISCHARGE_LIQUIDATION_OF_PROPERTY = ChapterRule(
        [CustodyCatalogsPattern.FUND_CUSTODY_CHANGE_DISCHARGE_LIQUIDATION_OF_PROPERTY]
    ).convert2dict()

    # 违约责任
    CHAPTER_FUND_RESPONSIBILITY_FOR_BREACH_OF_CONTRACT = ChapterRule(
        [CustodyCatalogsPattern.FUND_RESPONSIBILITY_FOR_BREACH_OF_CONTRACT]
    ).convert2dict()

    # 争议解决方式
    CHAPTER_FUND_DISPUTE_RESOLUTION = ChapterRule([CustodyCatalogsPattern.FUND_DISPUTE_RESOLUTION]).convert2dict()

    # 基金托管协议的效力
    CHAPTER_FUND_VALIDITY_CUSTODY_AGREEMENT = ChapterRule(
        [CustodyCatalogsPattern.FUND_VALIDITY_CUSTODY_AGREEMENT]
    ).convert2dict()

    # 其他事项
    CHAPTER_FUND_OTHER_BUSINESS = ChapterRule([CustodyCatalogsPattern.FUND_OTHER_BUSINESS]).convert2dict()

    # 基金托管协议的签订
    CHAPTER_FUND_SIGNING_OF_CUSTODY_AGREEMENT = ChapterRule(
        [CustodyCatalogsPattern.FUND_SIGNING_OF_CUSTODY_AGREEMENT]
    ).convert2dict()
