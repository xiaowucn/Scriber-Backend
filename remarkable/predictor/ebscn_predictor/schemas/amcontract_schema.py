"""资管合同要素"""

predictor_options = [
    {
        "path": ["产品名称"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
        "location_threshold": 0.2,
    },
    {
        "path": ["托管人"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
        "location_threshold": 0.2,
    },
    {
        "path": ["类型"],
        "models": [
            {
                "name": "score_filter",
                "threshold": 0.2,
            },
        ],
    },
    {
        "path": ["投资范围"],
        "models": [
            {
                "name": "score_filter",
                "threshold": 0.2,
            },
        ],
    },
    {
        "path": ["投资比例"],
        "models": [
            {
                "name": "score_filter",
                "threshold": 0.2,
            },
        ],
    },
    {
        "path": ["存续期限"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
        "location_threshold": 0.2,
    },
    {
        "path": ["募集期"],
        "models": [
            {
                "name": "score_filter",
                "threshold": 0.2,
            },
        ],
    },
    {
        "path": ["巨额退出告知方式"],
        "models": [
            {
                "name": "score_filter",
                "threshold": 0.2,
            },
        ],
    },
    {
        "path": ["托管费率"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
        "location_threshold": 0.2,
    },
    {
        "path": ["托管账户"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
        "location_threshold": 0.2,
    },
]


prophet_config = {"depends": {}, "predictor_options": predictor_options}
