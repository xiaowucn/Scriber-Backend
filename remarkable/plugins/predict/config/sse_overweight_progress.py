from copy import deepcopy

from remarkable.plugins.predict.models.model_base import NOTICE_BASE_PREDICTORS
from remarkable.plugins.predict.predictor import AIAnswerPredictor

predictors = deepcopy(NOTICE_BASE_PREDICTORS)
predictors.extend(
    [
        {
            "path": ["（二级）", "类型"],
            "model": "enum_value",
            "threshold": 0,
            "default_value": "进展",
        },
    ]
)


class OverWeightProgress(AIAnswerPredictor):
    """
    12: "1223 股东增持计划"
    """

    def __init__(self, *args, **kwargs):
        kwargs["predictors"] = predictors
        kwargs["default_model"] = "partial_text"
        super(OverWeightProgress, self).__init__(*args, **kwargs)
