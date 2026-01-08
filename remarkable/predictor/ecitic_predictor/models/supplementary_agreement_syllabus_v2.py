from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.ecitic_predictor.models.scope_investment import ScopeSplitter
from remarkable.predictor.ecitic_predictor.models.splitter_mixin import ParaSplitterMixin
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import OutlineResult


class SupplementaryAgreementSyllabusEltV2(ParaSplitterMixin, SyllabusEltV2, ScopeSplitter):
    """补充协议-投资范围"""

    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super().__init__(options, schema, predictor=predictor)
        self.segmentation_regs = PatternCollection(self.get_config("segmentation_regs"))

    def predict_schema_answer(self, elements):
        parent_answers, _, predict_elements = super().get_predict_elements(elements)
        if not predict_elements:
            return parent_answers
        find_flag_index = -1
        outline_elements = []
        if self.segmentation_regs:
            for element in predict_elements:
                if self.segmentation_regs.nexts(clean_txt(element["text"])) and element["index"] > find_flag_index:
                    find_flag_index = element["index"]
            if find_flag_index != -1:
                outline_elements = [element for element in predict_elements if element["index"] > find_flag_index]
        else:
            outline_elements = predict_elements

        answer_results = []
        if outline_elements:
            outline_result = [
                OutlineResult(self.pdfinsight.elements_outline(outline_elements), element=outline_elements[0])
            ]
            answer_result = self.create_result(outline_result, column="原文")
            answer_results.append(answer_result)
            element_results = self.split(outline_elements)
            answer_results.extend([self.create_result(element_results, column="拆分")])
        return answer_results if answer_results else parent_answers
