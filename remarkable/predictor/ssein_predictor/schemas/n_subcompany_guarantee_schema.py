"""临时公告-为子公司提供担保"""

from remarkable.predictor.ssein_predictor.schemas import filter_predictors

predictor_options = filter_predictors()
predictor_options.extend(
    [
        {
            "path": ["重要内容提示"],
            "models": [
                {
                    "name": "score_filter",
                    "threshold": 0.2,
                },
            ],
        },
        {
            "path": ["重要提示-本次担保金额"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
            "location_threshold": 0.2,
        },
        {
            "path": ["重要提示-已实际为其担保的金额"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
            "location_threshold": 0.2,
        },
        {
            "path": ["重要提示-本次担保是否有反担保"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
            "location_threshold": 0.2,
        },
        {
            "path": ["逾期金额"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
            "location_threshold": 0.2,
        },
        {
            "path": ["审议会议"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
            "location_threshold": 0.2,
        },
        {
            "path": ["备查文件"],
            "models": [
                {
                    "name": "score_filter",
                    "threshold": 0.2,
                },
            ],
        },
        {
            "path": ["上市公司及子公司累计对外担保"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
            "location_threshold": 0.2,
        },
        {
            "path": ["上市公司及子公司累计对外担保额度占总资产比例"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
            "location_threshold": 0.2,
        },
        {
            "path": ["上市公司及子公司累计对外担保额度占净资产比例"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
            "location_threshold": 0.2,
        },
        {
            "path": ["担保情况"],
            "sub_primary_key": [
                "被担保方",
            ],
            "models": [
                {
                    "name": "table_row",
                },
                {
                    "name": "partial_text",
                },
            ],
            "location_threshold": 0.2,
        },
        {
            "path": ["被担保方财务情况"],
            "sub_primary_key": ["被担保方", "报告期"],
            "models": [
                {
                    "name": "table_tuple",
                },
                {
                    "name": "partial_text",
                },
            ],
            "location_threshold": 0.2,
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
