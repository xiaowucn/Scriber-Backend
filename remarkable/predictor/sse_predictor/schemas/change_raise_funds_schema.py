"""
122: "0704 变更募集资金用途【三】"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors(exclude=("公司全称"))

predictor_options.extend(
    [
        {
            "path": ["公司全称"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(0, 5)),
                    "regs": [r"(?P<dst>.*?公司)"],
                }
            ],
        },
        {
            "path": [
                "募集资金的总额",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "募集资金余额",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "变更原因",
            ],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": [
                "变更前的用途",
            ],
            "models": [
                {
                    "name": "partial_text",
                    "multi_elements": True,
                },
            ],
        },
        {
            "path": [
                "变更后的用途",
            ],
            "models": [
                {
                    "name": "partial_text",
                    "multi_elements": True,
                },
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
