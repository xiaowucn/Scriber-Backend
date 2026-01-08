"""
博时基金 基金确认单
"""

predictor_options = [
    {
        "path": ["基金账号"],
        "models": [
            {
                "name": "table_kv",
            },
            {
                "name": "octopus_kv",
                "pattern": [
                    r"基金账号[:：](?P<dst>\d+)",
                ],
            },
        ],
    },
    {
        "path": ["证件号码"],
        "models": [
            {
                "name": "table_kv",
            },
            {
                "name": "octopus_kv",
                "pattern": [
                    r"证件号码[:：](?P<dst>\d+)",
                ],
            },
        ],
    },
    {
        "path": ["基金名称"],
        "models": [
            {
                "name": "table_kv",
            },
            {
                "name": "octopus_kv",
                "pattern": [
                    r"基金名称[:：](?P<dst>.*)",
                ],
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
