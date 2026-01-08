from copy import deepcopy

from remarkable.plugins.predict.models.model_base import NOTICE_BASE_PREDICTORS
from remarkable.plugins.predict.predictor import AIAnswerPredictor

predictors = deepcopy(NOTICE_BASE_PREDICTORS)
predictors.extend(
    [
        {
            "path": ["（二级）", "传闻基本情况"],
            "model": "syllabus_elt",
            "need_syl": True,
        },
        {
            "path": ["（二级）", "澄清内容：真实情况"],
            "model": "syllabus_elt",
            "need_syl": True,
        },
        # {
        #     "path": ["（二级）", "澄清内容：如传闻涉及及控制权变更或重大资产重组等事项的声明"],
        #     "model": "syllabus_elt",
        #     "need_syl": True,
        # },
    ]
)


class ClarifyOrExplainPredictor(AIAnswerPredictor):
    """
    10: "1002 澄清或说明"
    todo：
        1、多组传闻+澄清
        2、传闻（澄清）没有所属章节
    """

    def __init__(self, *args, **kwargs):
        kwargs["predictors"] = predictors
        kwargs["default_model"] = "partial_text"
        super(ClarifyOrExplainPredictor, self).__init__(*args, **kwargs)
