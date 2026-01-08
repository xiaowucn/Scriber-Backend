"""市场地位"""

predictor_options = [
    {
        "path": ["发行人市场地位及竞争情况", "市场地位标题"],
        "models": [
            {
                "name": "score_filter",
                "threshold": 0.2,
            },
        ],
    },
    {
        "path": ["发行人市场地位及竞争情况", "市场地位原文"],
        "models": [
            {
                "name": "score_filter",
                "threshold": 0.2,
            },
        ],
    },
    {
        "path": ["行业内主要企业名称"],
        "sub_primary_key": [
            "企业名称",
        ],
        "models": [
            {
                "name": "table_row",
                "multi": True,
                "multi_elements": True,
            },
            {
                "name": "partial_text",
                "multi": True,
                "multi_elements": True,
            },
        ],
        "location_threshold": 0.2,
    },
]


prophet_config = {"depends": {}, "predictor_options": predictor_options}
