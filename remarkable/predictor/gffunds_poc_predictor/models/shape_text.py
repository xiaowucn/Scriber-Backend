from collections import defaultdict

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt, index_in_space_string
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import CharResult, PredictorResult


class ShapeText(BaseModel):
    @property
    def regs(self):
        return PatternCollection(self.get_config("regs"))

    def train(self, dataset, **kwargs):
        pass

    def predict_schema_answer(self, elements):
        answer_results = []
        elements = self.get_elements_from_pdfinsight()
        if not elements:
            return []
        for element in elements:
            element_results = self.extract_by_element(element)
            if element_results:
                answer_results.append(element_results)
                if not self.multi_elements:
                    break
        return answer_results

    def get_elements_from_pdfinsight(self):
        ret = []
        for eles in self.pdfinsight.element_dict.values():
            for ele in eles:
                if ele.data["class"] != "SHAPE":
                    continue
                _, element = self.pdfinsight.find_element_by_index(ele.data["index"])
                ret.append(element)
        return ret

    def extract_by_element(self, element) -> dict[str, list[PredictorResult]]:
        answer_result = {}
        for column in self.columns:
            column_answer_result = self.extract_for_column(element, column)
            if column_answer_result:
                answer_result.update(column_answer_result)
        return answer_result

    def extract_for_column(self, element, column) -> dict[str, list[PredictorResult]]:
        answer_results = defaultdict(list)
        element_results = self.extract_by_regs(element)
        if element_results:
            for element_result in element_results:
                answer_results[column].append(self.create_result([element_result], column=column))
        return answer_results

    def extract_by_regs(self, element) -> list[CharResult]:
        element_results = []
        clean_element_text = clean_txt(element.get("text", ""))
        matchers = self.regs.finditer(clean_element_text)
        for match in matchers:
            if "dst" in match.groupdict():
                c_start, c_end = match.span("dst")
            else:
                c_start, c_end = match.span()
            sp_start, sp_end = c_start, c_end
            if not self.is_english:
                sp_start, sp_end = index_in_space_string(element["text"], (c_start, c_end))
            chars = element["chars"][sp_start:sp_end]
            if not chars:
                continue
            element_results.append(self.create_content_result(element, chars))
            if not self.multi:
                break
        return element_results

    @staticmethod
    def create_content_result(element, chars) -> CharResult:
        return CharResult(element, chars)
