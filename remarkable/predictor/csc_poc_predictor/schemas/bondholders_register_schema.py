"""中信建投 《【上清所】债券持有人名册 》"""

predictor_options = [
    {
        "path": ["文档标题"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>债券持有人名册)",
                    r"(?P<dst>银行间市场清算所股份有限公司)",
                ],
            },
        ],
    },
    {
        "path": ["权益登记日"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
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
        "path": ["持有人名册"],
        "sub_primary_key": [
            "证券账户号码",
        ],
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
