"""
103: "1411 配股发行"

todo: 审议程序情况（是否要上股东大会决议）
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors(exclude=("公司全称",))

predictor_options.extend(
    [
        {
            "path": ["公司全称"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": (0,),
                    "regs": [r"(?P<dst>.*?公司)"],
                    "use_crude_answer": True,
                }
            ],
        },
        {
            "path": ["每10股配几股"],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [r"每10股配售?(?P<dst>.*?股)"],
                }
            ],
        },
        {
            "path": ["发行的每股价格", "金额"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["发行的每股价格", "单位"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["本次可认购数量", "金额"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["本次可认购数量", "单位"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["本次可认购数量", "单位"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["审议程序情况（是否要上股东大会决议）"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
