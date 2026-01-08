"""
64: "2402 股份被冻结"
"""

from remarkable.predictor.sse_predictor.predictor_config import SPECIAL_ATTR_PATTERNS, filter_predictors

predictor_options = filter_predictors(exclude=("公告时间"))

predictor_options.extend(
    [
        {
            "path": ["公告日期"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(-10, 0))[::-1],
                    "regs": SPECIAL_ATTR_PATTERNS["date"],
                }
            ],
        },
        {
            "path": ["公告类型"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": [
                "二级",
            ],
            "models": [
                {
                    "name": "table_row",
                },
                {
                    "name": "partial_text",
                },
            ],
            "sub_primary_key": ["被冻结人名称"],
        },
        {
            "path": ["股份被冻结的影响分析"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
