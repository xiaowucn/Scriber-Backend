# _*_ coding: utf-8 _*_

from remarkable.plugins.predict.predictor import AIAnswerPredictor

predictors = [
    {"path": ["公司名称"], "model": ["partial_text"], "valid": {"length": {"公司名称": [2, 16]}}},
    {
        "path": ["现金红利发放日"],
        "model": ["table_row", "partial_text"],
    },
    {
        "path": ["股权登记日"],
        "model": ["table_row", "partial_text"],
    },
    {
        "path": ["除权（息）日"],
        "model": ["table_row", "partial_text"],
    },
]


class ProfitDistribution(AIAnswerPredictor):
    """
    利润分配实施公告
    """

    def __init__(self, *args, **kwargs):
        kwargs["predictors"] = predictors
        kwargs["default_model"] = "partial_text"
        super(ProfitDistribution, self).__init__(*args, **kwargs)
