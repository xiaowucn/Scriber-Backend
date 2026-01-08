"""
schema id: 134
schema name: "24 临时公告-公司被责令关闭或吊销经营资质"
"""

predictor_options = [
    {
        "path": ["企业名称"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["与上市公司关系"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["企业状态"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
]


prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
