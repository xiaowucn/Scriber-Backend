import copy

from remarkable.predictor.models.empty_answer import EmptyAnswer
from remarkable.predictor.models.middle_paras import MiddleParas
from remarkable.predictor.models.para_match import ParaMatch
from remarkable.predictor.models.partial_text import PartialText


class ParagraphSelector(MiddleParas):
    def __init__(self, options, schema, predictor=None):
        super(ParagraphSelector, self).__init__(options, schema, predictor=predictor)
        self.para_model = self.gen_paragraph_model()

    def select_paragraph_elements(self, elements):
        answer_results = []
        for element in elements:
            if element.get("class") == "PARAGRAPH" and not element.get("fragment"):
                answer_results.extend(self.para_model.predict([element]))
        return answer_results

    def gen_paragraph_model(self):
        para_options = copy.deepcopy(self.config)
        para_model_name = self.config.get("paragraph_model")
        if para_model_name:
            para_options["name"] = para_model_name
            para_config = self.config.get("para_config", {})
            para_options.update(para_config)

            if para_model_name == "partial_text":
                return PartialText(para_options, self.schema, predictor=self.predictor)
            if para_model_name == "para_match":
                return ParaMatch(para_options, self.schema, predictor=self.predictor)
        return None

    def predict_schema_answer(self, elements):
        answer_results = []
        elements_blocks = super(ParagraphSelector, self).collect_elements(elements)
        if not elements_blocks:
            return answer_results

        if self.para_model and not isinstance(self.para_model, EmptyAnswer):
            for elements_block in elements_blocks:
                answer_results.extend(self.select_paragraph_elements(elements_block))
        else:
            for elements_block in elements_blocks:
                answer_results.append(self.build_answer(elements_block, self.schema.name))
        return answer_results
