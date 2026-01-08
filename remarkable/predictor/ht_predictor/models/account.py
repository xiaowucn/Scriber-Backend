from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.models.partial_text import PartialText
from remarkable.predictor.mold_schema import SchemaItem


class Account(PartialText):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(Account, self).__init__(options, schema, predictor=predictor)

    def predict_schema_answer(self, elements):
        ret = []
        answer_results = super(Account, self).predict_schema_answer(elements)
        anchor_regs = PatternCollection(self.config.get("anchor_regs", []))
        must_preset = self.config.get("must_preset", True)
        if not anchor_regs:
            return answer_results
        if not answer_results:
            return ret
        for answer_result in answer_results:
            element = list(answer_result.values())[0][0].relative_elements[0]
            above_elements = self.get_above_elements(element)
            for above_element in above_elements:
                if anchor_regs.nexts(clean_txt(above_element["text"])):
                    ret.append(answer_result)
                    break
        if must_preset and not ret:
            return answer_results
        return ret
