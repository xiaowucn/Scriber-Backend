from .details_of_ssc import DetailsOfSSC
from .extra_date_info import ExtraDateInfo
from .fund_trans import FundTrans
from .investment_ratio import InvestmentRatioMiddleParas, InvestmentRatioSyllabus
from .investment_restrictions import (
    InvestmentRestrictionsMiddle,
    InvestmentRestrictionsSyllabus,
    InvestmentRestrictionsTupleTable,
)
from .performance import Performance
from .re_buy_date import ReBuyDate
from .scope_investment import (
    RowMatchSplitter,
    ScopeInvestmentMiddle,
    ScopeInvestmentSyllabus,
    ScopeInvestmentSyllabusBased,
)
from .scope_investment_gpt import ScopeInvestmentGPT
from .supplementary_agreement_syllabus_v2 import SupplementaryAgreementSyllabusEltV2
from .trading_exchange_from_merged_kv import TradingExchangeFromMergedTableKV
from .trading_exchange_kv import TradingExchangeTableKV
from .trading_exchange_para_match import TradingExchangeParaMatch
from .trading_exchange_syllabus import TradingExchangeSyllabus

model_config = {
    "re_buy_date": ReBuyDate,
    "found_trans": FundTrans,
    "extra_date_info": ExtraDateInfo,
    "performance": Performance,
    "scope_investment_middle": ScopeInvestmentMiddle,
    "scope_investment_gpt": ScopeInvestmentGPT,
    "investment_restrictions": InvestmentRestrictionsSyllabus,
    "investment_restrictions_middle": InvestmentRestrictionsMiddle,
    "investment_restrictions_tuple_table": InvestmentRestrictionsTupleTable,
    "details_of_ssc": DetailsOfSSC,
    "supplementary_agreement_elt_v2": SupplementaryAgreementSyllabusEltV2,
    "scope_investment_syllabus_based": ScopeInvestmentSyllabusBased,
    "scope_investment_syllabus": ScopeInvestmentSyllabus,
    "trading_exchange_syllabus": TradingExchangeSyllabus,
    "trading_exchange_kv": TradingExchangeTableKV,
    "trading_exchange_from_merged_kv": TradingExchangeFromMergedTableKV,
    "trading_exchange_para_match": TradingExchangeParaMatch,
    "investment_ratio_syllabus": InvestmentRatioSyllabus,
    "investment_ratio_middle_paras": InvestmentRatioMiddleParas,
    "row_match_splitter": RowMatchSplitter,
}
