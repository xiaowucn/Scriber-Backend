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
        {
            "path": ["（二级）", "标的名称"],
            "model": "partial_text",
            "ignore_around_texts": True,
            "regs": [
                r"投资设立(?P<dst>[^。]*?公司)",
            ],
        },
        {
            "path": ["（二级）", "标的情况"],
            "model": "partial_text",
            "ignore_around_texts": True,
            "regs": [
                r"([:：]|其中)公司出资.*?元，(?P<dst>持股[.\d,\s%]*)",
            ],
        },
        {
            "path": ["（二级）", "投资金额"],
            "model": "partial_text",
            "ignore_around_texts": True,
            "regs": [
                r"投资金额[:：](?P<dst>[\d\s,.千万亿元]*(人民币)?)",
                r"([:：]|其中)公司出资(?P<dst>.*?元)，持股[.\d,\s%]*",
            ],
        },
        {
            "path": ["（二级）", "是否是关联交易"],
            "model": "partial_text",
            "regs": [r"(?P<dst>[^，。（）]*构成[^，。；]*?关联交易)"],
            "enum_pattern": [
                (
                    "否",
                    [
                        r"[无不未没][^，。；]*?关联交易",
                    ],
                )
            ],
        },
        {
            "path": ["（二级）", "是否是重大资产重组"],
            "model": "partial_text",
            "regs": [
                r"(?P<dst>[无不未没][^，。；]*?重大资产重组[^，。；]*)",
            ],
            "enum_pattern": [
                (
                    "否",
                    [
                        r"[无不未没][^，。；]*?重大资产重组",
                    ],
                )
            ],
        },
        {
            "path": ["（二级）", "审议程序（是否要上股东大会决议）"],
            "model": "partial_text",
            "ignore_around_texts": True,
            "regs": [
                r"(?P<dst>[无不未没][^，。；]*?股东大会[^，。；]*)",
            ],
            "enum_pattern": [
                (
                    "否",
                    [
                        r"[无不未没][^，。；]*?股东大会",
                    ],
                )
            ],
        },
    ]
)


class InvestmentsAbroad(AIAnswerPredictor):
    """
    14: "0403 对外投资"
    """

    def __init__(self, *args, **kwargs):
        kwargs["predictors"] = predictors
        kwargs["default_model"] = "partial_text"
        super(InvestmentsAbroad, self).__init__(*args, **kwargs)
