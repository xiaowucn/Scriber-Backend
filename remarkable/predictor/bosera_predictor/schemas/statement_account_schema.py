"""
博时基金 对账单
"""

predictor_options = [
    {
        "path": ["账号名称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    r"账户名称[:：](?P<dst>\w+)",
                ],
                "model_alternative": True,
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
                "regs": [
                    r"基金账号[:：](?P<dst>\w+)",
                ],
                "model_alternative": True,
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
                "regs": [
                    r"交易账号[:：](?P<dst>\w+)",
                ],
                "model_alternative": True,
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
        "path": ["基金持仓明细"],
        "sub_primary_key": ["基金代码"],
        "models": [
            {
                "name": "table_row",
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
