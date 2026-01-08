from copy import deepcopy

from remarkable.plugins.predict.models.model_base import NOTICE_BASE_PREDICTORS
from remarkable.plugins.predict.predictor import AIAnswerPredictor

predictors = deepcopy(NOTICE_BASE_PREDICTORS)
predictors.extend(
    [
        {
            "path": ["（二级）", "监事会召开日期"],
            "model": "partial_text",
        },
        {
            "path": ["（二级）", "应到人数"],
            "model": "partial_text",
        },
        {
            "path": ["（二级）", "实到人数"],
            "model": "partial_text",
        },
        {
            "path": ["（二级）", "（三级）"],
            "model": "motion",
            "multi_elements": True,
        },
    ]
)


class SupervisorsResolution(AIAnswerPredictor):
    """
    41: "05 监事会决议公告"
    """

    def __init__(self, *args, **kwargs):
        kwargs["predictors"] = predictors
        super(SupervisorsResolution, self).__init__(*args, **kwargs)
