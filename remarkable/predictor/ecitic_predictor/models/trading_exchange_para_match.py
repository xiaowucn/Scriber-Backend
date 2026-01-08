from remarkable.common.pattern import PatternCollection
from remarkable.predictor.ecitic_predictor.models.scope_investment import ParaMatchSplitter


class TradingExchangeParaMatch(ParaMatchSplitter):
    P_PREFIX = PatternCollection(r"指|[:：]")
    P_LINK_SENTENCE = PatternCollection(
        r"[、，,.。;；:：和或]|以?及|指|/|(?<!不)(?<!不均|不包)[均包]?[括含](但?不限于)?"
    )
    P_EXCLUDE_SENTENCE_TEXT = PatternCollection([r"国务院或"])
    P_SPLITTER_NUMBERING = None
