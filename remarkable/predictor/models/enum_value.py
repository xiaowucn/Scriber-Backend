# -*- coding: utf-8 -*-

from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import PredictorResult


class EnumValue(BaseModel):
    def extract_feature(self, attr, dataset, workers=None):
        pass

    def train(self, dataset, **kwargs):
        model_data = {}
        self.model_data = model_data

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        answer_results = []
        for column in self.columns:
            answer_result = {}
            simple_config = self.get_config("simple", column=column)
            if simple_config:  # 只需要枚举值
                column_result = self.create_result([], value=simple_config, column=column)
                answer_result[column] = [column_result]
            if answer_result:
                answer_results.append(answer_result)
        return answer_results
