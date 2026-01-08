"""
11: "1222 股东增持计划"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()

predictor_options.extend(
    [
        {
            "path": ["（二级）", "增持主体的名称"],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [
                        r"增持主体(的?名称)?[:：](?P<dst>.*)。?",
                    ],
                },
            ],
        },
        {
            "path": ["（二级）", "增持主体的身份"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "增持主体本次增持前已持有股份的数量"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "增持主体本次增持前持股比例"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "增持主体及其一致行动人增持前已持有股份的数量"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "增持主体及其一致行动人增持前持股比例"],
            "models": [
                {
                    "name": "partial_text",
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
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "金额（上限）"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "数量（下限）"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "数量（上限）"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "价格（下限）"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "价格（上限）"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "实施期限"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "资金来源"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "增持股份的目的"],
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
