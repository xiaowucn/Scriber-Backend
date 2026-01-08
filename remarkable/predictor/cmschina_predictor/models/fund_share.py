from typing import Generator

from remarkable.predictor.fullgoal_predictor.models.product_abb import get_depend_predictors
from remarkable.predictor.models.partial_text import PartialText
from remarkable.predictor.schema_answer import PredictorResult


class FundShare(PartialText):
    def train(self, dataset, **kwargs):
        pass

    def gen_depend_answers(self, predictors) -> Generator[PredictorResult, None, None]:
        for predictor in predictors:
            elements = self.predictor.get_candidate_elements(predictor.schema.path[1:])
            for answers in predictor.predict_answer_from_models(elements) or []:
                for answer in (a for ans in answers.values() for a in ans):
                    yield answer

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        depend_predictors = get_depend_predictors(self.predictor.prophet.predictors, self.get_config("depends", []))
        depend_answer = next(self.gen_depend_answers(depend_predictors), None)
        if not depend_answer:
            return []

        elements = []
        for element_result in depend_answer.element_results:
            elements.extend(element_result.origin_elements)

        return super().predict_schema_answer(elements)
