from remarkable.plugins.predict.predictor import AIAnswerPredictor

# from remarkable.plugins.predict.models.model_base import SPECIAL_ATTR_PATTERNS

predictors = [
    {
        "path": ["投资范围"],
        "model": "multi_paras",
    },
    {
        "path": ["投资策略"],
        "model": "multi_paras",
    },
    {
        "path": ["报告期末基金资产"],
        "model": "multi_paras",
    },
]


class YHFoudPocPredictor(AIAnswerPredictor):
    """银华基金信息抽取POC"""

    def __init__(self, *args, **kwargs):
        kwargs["predictors"] = predictors
        kwargs["default_model"] = "partial_text"
        super(YHFoudPocPredictor, self).__init__(*args, **kwargs)
