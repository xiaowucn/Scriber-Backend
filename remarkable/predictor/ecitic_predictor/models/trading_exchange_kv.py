from remarkable.common.pattern import PatternCollection
from remarkable.predictor.ecitic_predictor.models.scope_investment import KeyValueTableSplitter


class TradingExchangeTableKV(KeyValueTableSplitter):
    P_PREFIX = PatternCollection(r"指")
    P_EXCLUDE_SENTENCE_TEXT = PatternCollection([r"国务院或"])
