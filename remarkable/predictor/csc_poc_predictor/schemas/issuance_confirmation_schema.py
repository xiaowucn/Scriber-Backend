"""发行款到账确认书"""

predictor_options = [
    {
        "path": ["发行人账户账号"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"发行人账户账号[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["发行人账户中文全称"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"发行人账户中文全称[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["到账情况"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(?P<content>全部到账|部分到账)",
                "combine_paragraphs": True,
                # 'enum_from_multi_element': True,
                "multi_elements": True,
            },
        ],
    },
    {
        "path": ["包销数量"],
        "sub_primary_key": ["产品代码"],
        "models": [
            {
                "name": "table_row",
            },
        ],
    },
    {
        "path": ["未到账"],
        "sub_primary_key": ["产品代码"],
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
