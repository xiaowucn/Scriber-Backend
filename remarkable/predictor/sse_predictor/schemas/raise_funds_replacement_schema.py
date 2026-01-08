"""
106: "0705 用募集资金置换预先投入的自筹资金（KCB数据）"
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
                "募集资金净额",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "计划投入募集资金金额",
            ],
            "models": [
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": [
                "预先投入募投项目金额",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "预先支付发行费用金额（总计）",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "会计师鉴证时点",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "用于置换的金额（合计数）",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {"path": ["董事会审议反对及弃权情况"], "models": [{"name": "partial_text"}], "share_column": True},
        {
            "path": [
                "股东大会审议情况",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "注册时间",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "注册时间原文",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
