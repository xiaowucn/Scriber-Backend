# _*_ coding: utf-8 _*_

from remarkable.config import get_config
from remarkable.plugins.predict.predictor import AIAnswerPredictor


class CommonPredictor(AIAnswerPredictor):
    """
    缺省预测类
    """

    def __init__(self, *args, **kwargs):
        mold = args[0]
        predictors = []
        if get_config("web.model_manage", True) and mold.predictors:
            predictors = mold.predictors
        for config in predictors:
            config.setdefault("threshold", 0)
        kwargs["predictors"] = predictors
        kwargs["default_model"] = "score_filter"
        self.formatter = None
        super().__init__(*args, **kwargs)
