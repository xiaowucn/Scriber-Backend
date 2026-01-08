from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.ccxi_predictor.models import QualificationCriteria
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import CharResult


class SubChiefMember(QualificationCriteria):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(SubChiefMember, self).__init__(options, schema, predictor=predictor)

    def predict_schema_answer(self, elements):
        answer_results = []
        parent_answer_results = super(SubChiefMember, self).predict_schema_answer(elements)
        if not parent_answer_results:
            return answer_results
        for answer_result in parent_answer_results:
            paragraph_pattern = PatternCollection(self.get_config("paragraph_pattern", column=self.schema.name))
            element_result = answer_result.element_results[0]
            all_elements = element_result.origin_elements or []
            processed_elts = []
            for element in all_elements:
                if element["class"] != "PARAGRAPH":
                    continue
                if element["index"] in processed_elts:
                    continue
                matcher = paragraph_pattern.nexts(clean_txt(element["text"]))
                if matcher:
                    dst_chars = self.get_dst_chars_from_matcher(matcher, element)
                    if not dst_chars:
                        continue
                    dst_chars = self.remove_serial_chars(element, dst_chars)
                    answer_result = self.create_result([CharResult(element, dst_chars)], column=self.schema.name)
                    answer_results.append(answer_result)
                    processed_elts.append(element["index"])
                    if not self.multi:
                        break
                if answer_results and not self.multi:
                    break
        return answer_results
