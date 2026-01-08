# -*- coding: utf-8 -*-
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import CharResult


class DefaultAnswer(BaseModel):
    def train(self, dataset, **kwargs):
        return None

    def predict_schema_answer(self, elements):
        default_text = self.get_config("default_text")
        answer_result = self.create_result([CharResult(None, [], default_text)])

        return [answer_result]
