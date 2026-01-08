# -*- coding: utf-8 -*-
"""按照正则过滤"""

from remarkable.common.pattern import PatternCollection
from remarkable.predictor.models.score_filter import ScoreFilter


class TopFiveCustomersNotes(ScoreFilter):
    base_all_elements = True

    def train(self, dataset, **kwargs):
        pass

    def predict_schema_answer(self, elements):
        answer_results = super(TopFiveCustomersNotes, self).predict_schema_answer(elements)
        ret = []
        patterns = self.config.get("patterns", [])
        for answer_result in answer_results:
            if not PatternCollection(patterns).nexts(answer_result.text):
                continue
            ret.append(answer_result)
        return ret
