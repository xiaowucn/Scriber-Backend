"""
60: "17 定期报告-员工情况"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()

predictor_options.extend(
    [
        {
            "path": ["母公司在职员工的数量"],
            "models": [
                {
                    "name": "table_kv",
                },
            ],
        },
        {
            "path": ["主要子公司在职员工的数量"],
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
            "path": ["在职员工的数量合计"],
            "models": [
                {
                    "name": "table_kv",
                },
            ],
        },
        {
            "path": ["母公司及主要子公司需承担费用的离退休职工人数"],
            "models": [
                {
                    "name": "table_kv",
                },
            ],
        },
        {
            "path": ["生产人员"],
            "models": [
                {
                    "name": "table_kv",
                },
            ],
        },
        {
            "path": ["销售人员"],
            "models": [
                {
                    "name": "table_kv",
                },
            ],
        },
        {
            "path": ["技术人员"],
            "models": [
                {
                    "name": "table_kv",
                },
            ],
        },
        {
            "path": ["财务人员"],
            "models": [
                {
                    "name": "table_kv",
                },
            ],
        },
        {
            "path": ["行政人员"],
            "models": [
                {
                    "name": "table_kv",
                },
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
