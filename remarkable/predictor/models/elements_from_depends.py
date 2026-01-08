from typing import Generator

from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import PredictorResult


class ElementsFromDepends(BaseModel):
    """
    从另一个字段的答案确定elements

    此模型需与 elements_collector_based 搭配使用

    {
        "name": "elements_collector_based",
        "elements_collect_model": "elements_from_depends",
        "elements_collect_config": {
            "depends": ["债项全称"],
        },
        "paragraph_model": "para_match",
        "para_config": {
            "paragraph_pattern": [r".*"],
        }
    }
    """

    def train(self, dataset, **kwargs):
        pass

    def get_depend_predictors(self):
        depends = self.get_config("depends", [])
        if not depends:
            return []
        for predictor in self.predictor.prophet.predictors:
            if predictor.schema.name in depends:
                yield predictor

    def gen_depend_answers(self, predictors) -> Generator[PredictorResult, None, None]:
        for predictor in predictors:
            elements = self.predictor.get_candidate_elements(predictor.schema.path[1:])
            for answers in predictor.predict_answer_from_models(elements) or []:
                for answer in (a for ans in answers.values() for a in ans):
                    yield answer

    def collect_elements(self, elements) -> list[list[dict]]:
        depend_predictors = self.get_depend_predictors()
        depend_answer = next(self.gen_depend_answers(depend_predictors), None)
        if not depend_answer:
            return []

        eles = self.get_elements_from_answer_results(depend_answer.element_results)
        ret = []
        for ele in eles:
            # 部分element_result里的element有被修改过,比如MiddleParas
            _, element = self.pdfinsight.find_element_by_index(ele["index"])
            if element:
                ret.append(element)
        return [ret]

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        raise NotImplementedError
