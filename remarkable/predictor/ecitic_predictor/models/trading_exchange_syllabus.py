from remarkable.common.pattern import PatternCollection
from remarkable.predictor.ecitic_predictor.models.scope_investment import ScopeInvestmentSyllabus


class TradingExchangeSyllabus(ScopeInvestmentSyllabus):
    P_PREFIX = PatternCollection(r"指")
    P_EXCLUDE_SENTENCE_TEXT = PatternCollection([r"国务院或"])
