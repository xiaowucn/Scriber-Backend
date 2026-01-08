"""
主承销商
"""

import re

from remarkable.predictor.models.partial_text import PartialText


class MainConsignee(PartialText):
    CONSIGNEE = "主承销商"
    p_punctuation = re.compile(r"[;；。，]")
    p_black = re.compile(r"^公司")

    def predict_schema_answer(self, elements):
        new_answer_results = []
        answer_results = super(MainConsignee, self).predict_schema_answer(elements)
        exist_name = []
        for answer_result in answer_results:
            new_answer_result = {}
            distinct_element_results = []
            for element_result in answer_result[self.CONSIGNEE][0].element_results:
                if self.p_black.search(element_result.text):
                    continue
                clean_name = self.p_punctuation.sub("", element_result.text)
                if clean_name in exist_name:
                    continue
                exist_name.append(clean_name)
                distinct_element_results.append(element_result)
            if not distinct_element_results:
                continue
            new_answer_result[self.CONSIGNEE] = [
                self.create_result(distinct_element_results, schema=self.schema, column=self.CONSIGNEE)
            ]
            new_answer_results.append(new_answer_result)
        return new_answer_results
