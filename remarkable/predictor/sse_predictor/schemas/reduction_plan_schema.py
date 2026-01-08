"""
20: 1220 股东减持计划
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()

predictor_options.extend(
    [
        {
            "path": ["（二级）", "减持主体的名称"],
            "models": [
                {
                    "name": "table_row",
                },
                {
                    "name": "partial_text",
                },
            ],
        },
        {"path": ["（二级）", "减持主体的身份"], "models": [{"name": "table_row"}]},
        {
            "path": ["（二级）", "本次减持前持股数量"],
            "models": [
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["（二级）", "本次减持前持股比例"],
            "models": [
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["（二级）", "类型"],
            "models": [
                {
                    "name": "enum_value",
                    "simple": "计划",
                },
            ],
        },  # 只需要枚举值的情况
        {
            "path": ["（二级）", "金额（下限）"],
            "models": [
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["（二级）", "金额（上限）"],
            "models": [
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["（二级）", "数量（下限）"],
            "models": [
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["（二级）", "数量（上限）"],
            "models": [
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["（二级）", "价格（下限）"],
            "models": [
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["（二级）", "价格（上限）"],
            "models": [
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["（二级）", "减持期间"],
            "models": [
                {
                    "name": "table_row",
                },
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "减持目的"],
            "models": [
                {
                    "name": "table_row",
                },
                {
                    "name": "partial_text",
                },
            ],
        },
    ]
)

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
