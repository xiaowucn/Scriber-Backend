import re
from copy import copy

from remarkable.predictor.models.fixed_position import FixedPosition
from remarkable.predictor.schema_answer import PredictorResult


class CompanyStamp(FixedPosition):
    p_invalid = re.compile(r"[^\u4e00-\u9fa5(（）)]")

    def collect_elements(self, elements, column=None):
        elements_block = super().collect_elements(elements)
        eles = elements_block[0]
        ret = []
        for ele in eles:
            if "text" not in ele:
                continue
            new_ele = copy(ele)
            new_ele["text"] = self.p_invalid.sub("", new_ele["text"])
            ret.append(new_ele)
        return [ret]

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        answer_results = super().predict_schema_answer(elements)
        for answer_result in answer_results:
            for _, items in answer_result.items():
                for predictor_result in items:
                    for tail, fixed_tail in [
                        ("股份有限", "股份有限公司"),
                        ("股份", "股份有限公司"),
                        ("有限", "有限公司"),
                    ]:
                        if predictor_result.text.endswith(tail):
                            predictor_result.element_results[0].text = predictor_result.text.replace(tail, fixed_tail)
                            break
        return answer_results
