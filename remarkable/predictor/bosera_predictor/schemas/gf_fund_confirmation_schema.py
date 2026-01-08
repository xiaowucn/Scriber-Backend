"""
博时基金 广发申购赎回基金确认单
"""

predictor_options = [
    {
        "path": ["业务名称"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(0, 4)),
                "regs": [
                    r"(?P<dst>基金(申购|赎回))",
                    r"(?P<dst>基金.*?)确认单",
                ],
            },
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
                "merge_row": True,
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
                "merge_row": True,
                "row_pattern": [r"基金账号"],
                "content_pattern": [
                    r"基金账号[:：](?P<dst>[0-9a-zA-Z]+)",
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
                "merge_row": True,
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
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"基金代码"],
                "content_pattern": [
                    r"基金代码[:：](?P<dst>[0-9a-zA-Z]+)",
                ],
            },
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["基金名称"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"基金名称"],
                "content_pattern": [
                    r"基金名称[:：](?P<dst>\w+)(分红)",
                    r"基金名称[:：](?P<dst>\w+)",
                ],
            },
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["确认日期"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"确认日期"],
                "content_pattern": [
                    r"确认日期[:：](?P<dst>.+)",
                ],
            },
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["成交金额"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"确认金额"],
                "content_pattern": [
                    r"确认金额.{0,3}[:：](?P<dst>[\d,.]+)",
                ],
            },
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["成交份额"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"确认份额"],
                "content_pattern": [
                    r"确认份额.{0,3}[:：](?P<dst>[\d,.]+)",
                ],
            },
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["手续费"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"手续费（元）"],
                "content_pattern": [
                    r"手续费.{0,3}[:：]?(?P<dst>[\d,.]+)",
                ],
            },
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["交易净值"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"单位净值"],
                "content_pattern": [
                    r"单位净值[:：](?P<dst>[\d,.]+)",
                ],
            },
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
