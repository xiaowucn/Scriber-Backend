"""
21: 1221 股东减持进展
todo:
"进展"
"本次已减持的股份数量",
"本次已减持持股比例",
"本次已减持金额",
"本次已减持占本计划规模下限的比率",
"减持主体目前持股数量",
"减持主体目前持股比例"
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
        {
            "path": ["（二级）", "减持主体的身份"],
            "models": [
                {
                    "name": "table_row",
                },
            ],
        },
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
            "path": ["（二级）", "减持主体目前持股比例"],
            "models": [
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["（二级）", "本次已减持持股比例"],
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
                    "simple": "进展",
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
            ],
        },
        {
            "path": ["（二级）", "减持目的"],
            "models": [
                {
                    "name": "table_row",
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
