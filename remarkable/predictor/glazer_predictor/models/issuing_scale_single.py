"""
本期最终发行规模（单品种）
"""

import re

from remarkable.predictor.models.partial_text import PartialText


class IssuingScaleSingle(PartialText):
    def predict_schema_answer(self, elements):
        answer_results = []
        is_multi = False
        for element in elements:
            if re.compile(r"品种二").search(element.get("text", "")):
                is_multi = True
                break
        if is_multi:
            return answer_results

        answer_results = super(IssuingScaleSingle, self).predict_schema_answer(elements)

        return answer_results
