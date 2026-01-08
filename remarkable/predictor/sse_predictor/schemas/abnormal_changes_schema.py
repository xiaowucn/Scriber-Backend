"""
35: "1001 异常变动"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()

predictor_options.extend(
    [
        {
            "path": ["（二级）", "异常波动的情形"],
            "models": [
                {
                    "name": "score_filter",
                },
            ],
        },
        {
            "path": ["（二级）", "核查情况"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "判断是严重波动还是异常波动"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
