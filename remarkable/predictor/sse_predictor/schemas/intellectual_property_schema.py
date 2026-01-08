"""
schema id: 133
schema name: "23 临时公告-知识产权"
"""

predictor_options = [
    {
        "path": ["涉及主体"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["涉及主体与上市公司关系"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["问题类别"],
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
