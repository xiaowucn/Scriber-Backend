from copy import deepcopy

from remarkable.plugins.predict.models.model_base import NOTICE_BASE_PREDICTORS
from remarkable.plugins.predict.predictor import AIAnswerPredictor

predictors = deepcopy(NOTICE_BASE_PREDICTORS)

predictors.extend(
    [
        {
            "path": ["（二级）", "对上市公司的影响"],
            "model": "syllabus_elt",
        },
        {
            "path": ["（二级）", "其他协议主体情况"],
            "model": "syllabus_elt",
        },
    ]
)


class FinancialSupport(AIAnswerPredictor):
    """
    18: "0406 提供财务资助"
    """

    def __init__(self, *args, **kwargs):
        kwargs["predictors"] = predictors
        kwargs["default_model"] = "partial_text"
        super(FinancialSupport, self).__init__(*args, **kwargs)
