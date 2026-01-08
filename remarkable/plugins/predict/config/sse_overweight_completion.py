from copy import deepcopy

from remarkable.plugins.predict.models.model_base import NOTICE_BASE_PREDICTORS
from remarkable.plugins.predict.predictor import AIAnswerPredictor

predictors = deepcopy(NOTICE_BASE_PREDICTORS)
predictors.extend(
    [
        {
            "path": ["（二级）", "增持主体的名称"],
            "model": "partial_text",
            "regs": [
                r"增持主体[:：](?P<dst>.*?(先生|女士))",
            ],
        },
        {
            "path": ["（二级）", "金额（上限）"],
            "model": "partial_text",
            "regs": [
                r"增持[^。]*?金额[^。]*?不(?:超过|高于)(?:人民币)?(?P<dst>[\d,\s]+(?:[千百万亿]*元)?)",
            ],
        },
        {
            "path": ["（二级）", "金额（下限）"],
            "model": "partial_text",
            "regs": [
                r"增持[^。]*?金额[^。]*?不(?:少于|低于)(?:人民币)?(?P<dst>[\d,\s]+(?:[千百万亿]*元)?)",
            ],
        },
        {
            "path": ["（二级）", "数量（上限）"],
            "model": "partial_text",
            "regs": [
                r"增持[^。]*?数量[^。]*?不(?:超过|高于)(?P<dst>[\d,\s]+股)",
            ],
        },
        {
            "path": ["（二级）", "数量（下限）"],
            "model": "partial_text",
            "regs": [
                r"增持[^。]*?数量[^。]*?不(?:少于|低于)(?P<dst>[\d,\s]+股)",
            ],
        },
    ]
)


class OverWeightCompletion(AIAnswerPredictor):
    """
    13: "1224 股东增持计划完成"
    """

    def __init__(self, *args, **kwargs):
        kwargs["predictors"] = predictors
        kwargs["default_model"] = "partial_text"
        super(OverWeightCompletion, self).__init__(*args, **kwargs)
