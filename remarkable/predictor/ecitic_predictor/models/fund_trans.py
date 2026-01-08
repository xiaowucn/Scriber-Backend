import re

from remarkable.plugins.predict.common import is_paragraph_elt
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.schema_answer import CharResult, ParagraphResult, PredictorResult


class FundTrans(SyllabusEltV2):
    pattern = re.compile(r"(?P<dst>.*?。.*)循环购买[^。]+如下[:：].*?$")

    def predict_schema_answer(self, elements):
        answer_results: list[PredictorResult] = super(FundTrans, self).predict_schema_answer(elements)
        results = {}
        for result in answer_results:
            for element in (e for elt in result.element_results for e in elt.origin_elements if is_paragraph_elt(e)):
                chars = element.get("chars", [])
                match = self.pattern.search(element.get("text", ""))
                if not match:
                    results.setdefault(element["index"], ParagraphResult(element, chars))
                else:
                    start, end = match.span("dst")
                    chars = chars[start:end]
                    results.setdefault(element["index"], CharResult(element, chars))
                    result.element_results = list(results.values())
                    return [result]
        return answer_results
