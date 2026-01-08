import re
from itertools import groupby
from operator import itemgetter

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import OutlineResult
from remarkable.predictor.utils import classify_by_kmeans


class KmeansClassification(BaseModel):
    base_all_elements = True

    def train(self, dataset, **kwargs):
        pass

    @property
    def remedy_low_score_element(self):
        return self.get_config("remedy_low_score_element", False)

    @property
    def neglect_remedy_pattern(self):
        return PatternCollection(self.get_config("neglect_remedy_pattern", []))

    @property
    def para_pattern(self):
        return PatternCollection(self.get_config("para_pattern", []), re.IGNORECASE)

    @property
    def threshold(self):
        return self.get_config("threshold")

    @property
    def high_score_elements_count(self):
        return self.get_config("high_score_elements_count")

    @property
    def filter_by_types(self):
        return self.get_config("filter_by_types", [])

    def predict_schema_answer(self, elements):
        if self.threshold:
            elements = [e for e in elements if e["score"] > self.threshold]
        answer_results = []
        if not elements:
            return answer_results
        high_score_elements = classify_by_kmeans(elements)
        if self.high_score_elements_count and len(high_score_elements) != self.high_score_elements_count:
            return []
        if self.remedy_low_score_element:
            high_score_elements = self.fill_in_answer(high_score_elements, elements)
        high_score_elements.sort(key=lambda x: x["index"])
        elements_dict = {i["index"]: i for i in high_score_elements}
        answer_groups = []
        for _, value in groupby(enumerate(list(elements_dict.keys())), lambda x: x[1] - x[0]):
            answer_groups.append([v for i, v in value])

        # 整体计算枚举值
        page_box = self.pdfinsight.elements_outline(high_score_elements)
        element_results = [
            OutlineResult(page_box=page_box, element=high_score_elements[0], origin_elements=high_score_elements)
        ]
        summary_answer_result = self.create_result(element_results, column=self.schema.name)
        summary_enum_value = summary_answer_result.answer_value

        for answer_group in answer_groups:
            answer_elements = []
            for i in answer_group:
                if self.filter_by_types and elements_dict[i].get("type", "") not in self.filter_by_types:
                    continue
                if self.para_pattern.patterns:
                    if not self.para_pattern.nexts(elements_dict[i].get("text", "")):
                        continue
                answer_elements.append(elements_dict[i])
            if not answer_elements:
                continue
            page_box = self.pdfinsight.elements_outline(answer_elements)
            answer_elements.sort(key=itemgetter("index"))
            if not page_box:
                continue
            element_results = [
                OutlineResult(page_box=page_box, element=answer_elements[0], origin_elements=answer_elements)
            ]
            answer_result = self.create_result(element_results, column=self.schema.name, value=summary_enum_value)
            answer_results.append(answer_result)
        return answer_results

    def fill_in_answer(self, high_score_elements, all_elements):
        # 有一些元素块的分数较低， 但是存在于高分的元素块index之间，那么这样的元素块也很可能是答案，这里将其添加到答案中
        if not high_score_elements:
            return high_score_elements
        high_score_indexes = [i["index"] for i in high_score_elements]
        high_score_indexes.sort()
        if len(high_score_indexes) > 1 and high_score_indexes[-1] - high_score_indexes[0] > 5:
            return high_score_elements
        lower_score_elements = {i["index"]: i for i in all_elements if i["index"] not in high_score_indexes}
        high_score_range = list(range(high_score_indexes[0], high_score_indexes[-1] + 1))
        for index, element in lower_score_elements.items():
            if index in high_score_range:
                if element.get("text") and self.neglect_remedy_pattern.nexts(clean_txt(element["text"])):
                    continue
                high_score_elements.append(element)
        return high_score_elements

    @staticmethod
    def collect_elements(elements):
        high_score_elements = classify_by_kmeans(elements)
        return [high_score_elements]
