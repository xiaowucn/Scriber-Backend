# -*- coding: utf-8 -*-
"""按阈值取值"""

from remarkable.config import get_config
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import ParagraphResult, TableResult
from remarkable.service.predictor import is_paragraph_elt

DEFAULT_THRESHOLD = get_config("web.score_filter_threshold", 0.5)


class ScoreFilter(BaseModel):
    base_all_elements = True

    def __init__(self, options, schema, predictor=None):
        super(ScoreFilter, self).__init__(options, schema, predictor=predictor)
        self.threshold = float(self.get_config("threshold", default=DEFAULT_THRESHOLD))  # 阈值下限
        self.sort_by_index = self.get_config("sort_by_index")
        aim_types = self.get_config("aim_types")
        if isinstance(aim_types, str):
            aim_types = [aim_types]
        self.aim_types = aim_types  # 元素块类型

    @property
    def multi_elements(self):
        return self.get_config("multi_elements", True)

    def train(self, dataset, **kwargs):
        pass

    def predict_schema_answer(self, elements):
        answer_results = []
        for element in elements:
            if element["score"] < self.threshold:
                continue
            if self.aim_types and element["class"] not in self.aim_types:
                continue

            answer_result = None
            if self.schema.name == "币种" or (self.schema.name.startswith("<") and "单位" in self.schema.name):
                answer_result = self.find_special_attr(self.schema.name, element)

            elif is_paragraph_elt(element):
                answer_result = self.create_result(
                    [ParagraphResult(element, element["chars"])], column=self.schema.name
                )
            elif element["class"] == "TABLE":
                answer_result = self.create_result([TableResult(element, [])], column=self.schema.name)

            if answer_result:
                answer_results.append(answer_result)
            if not self.multi_elements and answer_results:
                break
        if self.multi_elements and self.sort_by_index:
            answer_results.sort(key=lambda x: x.element_results[0].element["index"])
        return answer_results
