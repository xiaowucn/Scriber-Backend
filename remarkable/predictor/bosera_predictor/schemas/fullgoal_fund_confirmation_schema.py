"""
博时基金 富国申购赎回基金确认单
"""

predictor_options = [
    {
        "path": ["业务名称"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["账户名称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
            {
                "name": "row_match",
                "row_pattern": [r"账户名称"],
                "content_pattern": [
                    r"账户名称[:：](?P<dst>\w+)",
                ],
            },
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["基金账号"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
            {
                "name": "row_match",
                "row_pattern": [r"基金账号"],
                "content_pattern": [
                    r"基金账号[:：](?P<dst>\w+)",
                ],
            },
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["交易账号"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
            {
                "name": "row_match",
                "row_pattern": [r"交易账号"],
                "content_pattern": [
                    r"交易账号[:：](?P<dst>\w+)",
                ],
            },
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["基金代码"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["基金名称"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["确认日期"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["成交金额"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["成交份额"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["手续费"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["交易净值"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
