"""
深交所企业债
"""

predictor_options = [
    {
        "path": ["所有者权益金额"],
        "models": [
            {
                "name": "table_tuple",
                "neglect_header": [r"[\D0]1月1日"],
                "syllabus_regs": ["合并资产负债表"],
            },
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "regs": [r"^所有者权益[（]或股东权益[）]合计(?P<dst>[\d,]+[.]\d+)"],
            },
        ],
    },
    {
        "path": ["资产受限金额合计"],
        "unit_depend": {"受限金额": "单位"},
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": {
                    "受限金额": [
                        r"受限资产账面价值为(?P<dst>[\d.,]+)[万亿]?元",
                    ],
                },
                "单位": {
                    "feature_black_list": [
                        r".*",
                    ],
                },
            },
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["报告期初有息债务余额"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["报告期末有息债务余额"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [r"截至报告期末.公司有息负债总额为(?P<dst>[\d.,]+[万亿]?元)"],
            },
        ],
    },
    {
        "path": ["报告期初对外担保余额"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["报告期末对外担保余额"],
        "models": [
            {
                "name": "partial_text",
            },
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "regs": [r"报告期末对外担保的余额.(?P<dst>[\d.,]+[万亿]?元)"],
            },
        ],
    },
    {
        "path": ["信息披露负责人信息"],
        "models": [
            {
                "name": "table_kv",
                "syllabus_regs": ["信息披露事务"],
                "在公司所担任职务类型": {
                    "regs": [r"[√☑](?P<dst>[^□]+)"],
                    "split_pattern": r"[√☑]",
                },
            },
        ],
    },
    {
        "path": ["会计师事务所"],
        "models": [
            {
                "name": "table_kv",
                "syllabus_regs": [
                    r"会计师事务所",
                ],
                "use_complete_table": True,
                "multi_elements": True,
            },
            {
                "name": "table_kv",
                "elements_nearby": {
                    "regs": [
                        r"中介机构情况",
                    ],
                    "amount": 1,
                    "step": -1,
                },
                "use_complete_table": True,
            },
        ],
    },
    {
        "path": ["单项资产受限"],
        "unit_depend": {"受限金额": "单位"},
        "models": [
            {
                "name": "table_row",
                "neglect_header_regs": r"^合计",
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
