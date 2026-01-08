# -*- coding: utf-8 -*-
from remarkable.predictor.models.base_model import BaseModel


class EmptyAnswer(BaseModel):
    def train(self, dataset, **kwargs):
        return None

    def predict_schema_answer(self, elements):
        answer_results = []
        for column in self.columns:
            answer_results.append(self.create_result([], column=column))
        return answer_results
