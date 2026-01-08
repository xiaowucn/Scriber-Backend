"""广发业务申请表其他模板"""

predictor_options = [
    {
        "path": ["交易类型"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"(分红方式修改|基金份额冻结/解冻|转托管|撤单)"],
                "content_pattern": [
                    r"(?P<dst>[☑](分红方式修改|基金份额冻结/解冻|撤单|转托管))",
                ],
            },
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>[☑](分红方式修改|基金份额冻结/解冻|撤单|转托管))",
                ],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"转出网点代码[:：].+\d+", r"[a-zA-Z0-9]+.*?现金分红"],
                "keep_first_dummy_cell": True,
                "content_pattern": [
                    r"(?P<dst>(转托管|分红方式修改))",
                ],
            },
        ],
    },
    {
        "path": ["交易账号"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"交易账号"],
                "content_pattern": [
                    r"交易账号.*?[:：]?.*?(?P<dst>[0-9a-zA-Z]+)",
                ],
            },
            {
                "name": "partial_text",
                "regs": [r"交易账号.*?[:：]?.*?(?P<dst>[0-9a-zA-Z]+)"],
            },
        ],
    },
    {
        "path": ["基金账号"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"基金账号"],
                "content_pattern": [
                    r"基金账号.*?[:：].*?(?P<dst>\d+)",
                ],
            },
            {"name": "partial_text", "regs": [r"基金账号.*?[:：].*?(?P<dst>\d+)"]},
        ],
    },
    {
        "path": ["转托管基金代码"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"转出基金名称.*?基金代码"],
                "content_pattern": [
                    r"基金代码.*?[:：].*?(?P<dst>\d+)",
                ],
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["分红方式列表"],
        # "sub_primary_key": ['分红方式基金代码', '分红方式选择'],
        "models": [
            {
                "name": "withdrawal_dividends",
                "multi": True,
                "content_regs": [r"\d+.*?(现金分红|红利再投资)"],
                "分红方式选择": {"regs": [r"[√☑](?P<dst>(现金分红|红利再投资))"]},
                "分红方式基金代码": {"regs": [r"^(?P<dst>[\d+a-zA-Z]+)"]},
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["金(份)额小写"],
        "models": [
            {
                "name": "parse_money",
                "merge_row": True,
                "row_pattern": [r"亿仟佰拾万仟佰拾"],
                "content_pattern": [
                    r"小写.*?(?P<dst>[\d]+)",
                ],
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["转出网点代码"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"转出网点代码"],
                "content_pattern": [
                    r"转出网点代码[:：]?.*?(?P<dst>\d+)",
                ],
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["转入网点代码"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"转入网点代码"],
                "content_pattern": [
                    r"转入网点代码[:：]?.*?(?P<dst>\d+)",
                ],
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["转入网点席位号"],
        "models": [
            {
                "name": "partial_text",
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"转入网点席位号"],
                "content_pattern": [
                    r"转入网点席位号[:：]?.*?(?P<dst>\d+)",
                ],
            },
        ],
    },
    {
        "path": ["转出申请单编号"],
        "models": [
            {
                "name": "partial_text",
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"转出申请单编号"],
                "content_pattern": [
                    r"转出申请单编号[:：]?.*?(?P<dst>\d+)",
                ],
            },
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
