"""
42: "06 委托表决权相关公告"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()
predictor_options.extend(
    [
        {
            "path": ["（二级）", "委托方"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "被委托方"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "股份数量"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "股份比例"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "委托时间"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
    ]
)

prophet_config = {
    "depends": {},
    # 'merge_schema_answers': True,
    "predictor_options": predictor_options,
}
