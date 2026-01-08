"""
58: "16 定期报告-研发投入"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()

predictor_options.extend(
    [
        {
            "path": ["单位"],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [r"单位[:：]?(?P<dst>.*元)"],
                }
            ],
        },
        {
            "path": ["研发投入合计"],
            "models": [
                {
                    "name": "table_kv",
                },
            ],
        },
        {
            "path": ["研发投入总额占营业收入比例（%）"],
            "models": [
                {
                    "name": "table_kv",
                },
            ],
        },
        {
            "path": ["公司研发人员的数量"],
            "models": [
                {
                    "name": "table_kv",
                },
            ],
        },
        {
            "path": ["研发人员数量占公司总人数的比例（%）"],
            "models": [
                {
                    "name": "table_kv",
                },
            ],
        },
        {
            "path": ["本期费用化研发投入"],
            "models": [
                {
                    "name": "table_kv",
                },
            ],
        },
        {
            "path": ["本期资本化研发投入"],
            "models": [
                {
                    "name": "table_kv",
                },
            ],
        },
        {
            "path": ["研发投入资本化的比重（%）"],
            "models": [
                {
                    "name": "table_kv",
                },
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
