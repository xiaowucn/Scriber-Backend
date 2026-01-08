from copy import deepcopy

from remarkable.plugins.predict.models.model_base import NOTICE_BASE_PREDICTORS
from remarkable.plugins.predict.predictor import AIAnswerPredictor

predictors = deepcopy(NOTICE_BASE_PREDICTORS)
predictors.extend([])


class EntrustVotingRight(AIAnswerPredictor):
    """
    42: "07 委托表决权相关公告"
    """

    def __init__(self, *args, **kwargs):
        kwargs["predictors"] = predictors
        kwargs["default_model"] = "partial_text"
        super(EntrustVotingRight, self).__init__(*args, **kwargs)
