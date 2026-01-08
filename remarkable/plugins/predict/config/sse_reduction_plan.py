# _*_ coding: utf-8 _*_
from copy import deepcopy

from remarkable.plugins.predict.models.model_base import NOTICE_BASE_PREDICTORS
from remarkable.plugins.predict.predictor import AIAnswerPredictor

predictors = deepcopy(NOTICE_BASE_PREDICTORS)
predictors.extend(
    [
        {
            "path": ["（二级）"],
            "model": "table_row",
        },
    ]
)


class ReductionPlan(AIAnswerPredictor):
    """
    20: 1220 股东减持计划
    """

    def __init__(self, *args, **kwargs):
        kwargs["predictors"] = predictors
        kwargs["default_model"] = "partial_text"
        super(ReductionPlan, self).__init__(*args, **kwargs)
