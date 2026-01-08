from copy import deepcopy

from remarkable.plugins.predict.models.model_base import NOTICE_BASE_PREDICTORS
from remarkable.plugins.predict.predictor import AIAnswerPredictor

predictors = deepcopy(NOTICE_BASE_PREDICTORS)
predictors.extend(
    [
        {
            "path": ["（二级）", "是否构成重大资产重组"],
            "model": "enum_value",
            "threshold": 0,
        },
        {
            "path": ["（二级）", "处置资产"],
            "model": "partial_text",
        },
        {
            "path": ["（二级）", "处置资产说明"],
            "model": "syllabus_elt",
            "need_syl": True,
        },
        {
            "path": ["（二级）", "资产价值"],
            "model": "partial_text",
        },
    ]
)


class AssetDisposal(AIAnswerPredictor):
    """
    28: "01 资产处置公告"
    """

    def __init__(self, *args, **kwargs):
        kwargs["predictors"] = predictors
        kwargs["default_model"] = "partial_text"
        super(AssetDisposal, self).__init__(*args, **kwargs)
