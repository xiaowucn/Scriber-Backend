"""中信建投 《【深中登】回售结果明细表》"""

predictor_options = [
    {
        "path": ["文档标题"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>证券回售结果明细表)",
                ],
            },
        ],
    },
    {
        "path": ["债券简称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["债券代码"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["回售申报日期"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["证券回售明细表"],
        "sub_primary_key": ["证券账户号码", "回售登记金额（元）", "回售委托日期"],
        "models": [
            {
                "name": "table_row",
                "multi_elements": True,
                "neglect_header_regs": [
                    r"证券总数量",
                    r"总户数",
                    r"序号",
                ],
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
