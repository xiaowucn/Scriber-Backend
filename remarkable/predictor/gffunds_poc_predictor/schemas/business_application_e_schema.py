"""广发业务申请表模板e"""

CHECK_MARK = "[☑✓√■\uf052]"
predictor_options = [
    {
        "path": ["交易类型"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "multi": True,
                "row_pattern": [r"(产品转换|赎回|认/申购|转托管|分红方式)"],
                "content_pattern": [
                    rf"(?P<dst>{CHECK_MARK}(基金转换|赎回|认/申购|分红方式选择|转托管))",
                ],
            },
            {
                "name": "partial_text",
                "multi_elements": True,
                "regs": [rf"(?P<dst>{CHECK_MARK}(基金转换|赎回|认/申购|分红方式选择|转托管))"],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "multi": True,
                "row_pattern": [r"产品名称.*?产品代码.*?\d+", r"转出产品代码.*?\d+转出产品名称"],
                "content_pattern": [
                    r"(?P<dst>(基金转换|赎回|认/申购|分红方式选择|转托管|产品转换))",
                ],
            },
        ],
    },
    {
        "path": ["交易账号"],
        "models": [
            {"name": "partial_text", "regs": [r"交易[账帐]号.*?[:：]?.*?(?P<dst>\w+)"]},
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"交易[帐账]号"],
                "content_pattern": [
                    r"交易[账帐]号.*?[:：]?.*?(?P<dst>\w+)",
                ],
            },
        ],
    },
    {
        "path": ["基金账号"],
        "models": [
            {"name": "partial_text", "regs": [r"基金[账帐]号\/投资者[账帐]号.*?[:：]?.*?(?P<dst>[A-Za-z0-9]+)"]},
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"基金[账帐]号"],
                "content_pattern": [
                    r"基金[账帐]号\/投资者[账帐]号.*?[:：]?\s*(?P<dst>[A-Za-z0-9]+)",
                ],
            },
        ],
    },
    {
        "path": ["基金代码"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"产品代码"],
                "content_pattern": [
                    r"(产品代码.*?[:：].*?(?P<dst>\d+))",
                ],
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["转入基金代码"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"转入基金代码"],
                "content_pattern": [
                    r"转入基金代码.*?[:：].*?(?P<dst>\d+)",
                ],
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["转出基金代码"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"转出基金代码"],
                "content_pattern": [
                    r"转出基金代码.*?[:：].*?(?P<dst>\d+)",
                ],
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["收费方式"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"收费方式"],
                "content_pattern": [
                    r"收费方式.*?[:：].*?(?P<dst>[［[]?[√☑E][]］]?[前后]端)",
                ],
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["分红方式"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"分红方式"],
                "content_pattern": [
                    rf"(?P<dst>{CHECK_MARK}(现金分红|红利再投资))",
                ],
            },
            {"name": "partial_text", "regs": [rf"(?P<dst>{CHECK_MARK}(现金分红|红利再投资))"]},
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
                    r"小写.*?(?P<dst>[\d·•]+)",
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
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["转入网点代码"],
        "models": [
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
        ],
    },
    {
        "path": ["转出申请单编号"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["转出收费方式"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"转出收费方式"],
                "content_pattern": [
                    rf"转出收费方式.*?[:：].*?(?P<dst>{CHECK_MARK}[前后]端)",
                ],
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["转入收费方式"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"转入收费方式"],
                "content_pattern": [
                    rf"转入收费方式.*?[:：].*?(?P<dst>{CHECK_MARK}[前后]端)",
                ],
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["交易币种"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["巨额未确认部分是否继续"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "use_all_elements": True,
                "row_pattern": [r"如(遇|发生)巨额赎回"],
                "content_pattern": [
                    rf"如(遇|发生)巨额赎回.*?是否顺延未获确认部分至下个交易日[:：]?.*?[:：].*?(?P<dst>{CHECK_MARK}[是否])",
                ],
            },
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
