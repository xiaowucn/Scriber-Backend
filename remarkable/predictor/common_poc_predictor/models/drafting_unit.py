"""
起草单位
"""

from remarkable.common.pattern import PatternCollection
from remarkable.predictor.models.partial_text import PartialText
from remarkable.predictor.schema_answer import CharResult

P_TWO_UNIT = PatternCollection(
    [
        r"(?P<dst>[\u4e00-\u9fa5（）()!]+)[与和及]",
        r"[与和及](?P<dst>[\u4e00-\u9fa5（）()!]+)",
    ]
)


class DraftingUnit(PartialText):
    def predict_schema_answer(self, elements):
        answer_results = []
        parent_answers = super().predict_schema_answer(elements)
        if not parent_answers:
            return answer_results
        predictor_result = parent_answers[0]["起草单位"]
        element_results = predictor_result[0].element_results
        last_answer = element_results[-1]
        matchers = list(P_TWO_UNIT.finditer(last_answer.text))
        if not matchers:
            return parent_answers
        element_results = element_results[:-1]
        fake_element = {
            "chars": last_answer.chars,
            "text": last_answer.text,
        }
        for matcher in matchers:
            dst_chars = self.get_dst_chars_from_matcher(matcher, fake_element)
            element_result = CharResult(last_answer.element, dst_chars)
            element_results.append(element_result)

        answer_results = [self.create_result(element_results, column="起草单位")]
        return answer_results
