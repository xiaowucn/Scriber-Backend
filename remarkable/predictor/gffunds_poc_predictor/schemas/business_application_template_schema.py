"""广发业务申请表模板"""

predictor_options = [
    {
        "path": ["交易类型"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"(基金转换|赎回/退出|认购/申购/?|/?参与|撤单)"],
                "content_pattern": [
                    r"(?P<dst>☑(基金转换|赎回/退出|认购/申购/参与|撤单))",
                    r"(?P<dst>☑((认购/申购/?|/?参与)))",
                    r"参与(?P<dst>赎回/退出)",
                    r"(?P<dst>☑认购/申购/参与)基金名称[:：\s]+\w+?基金代码[:：\s]+\d{6}",
                    r"(?P<dst>☑赎回/退出)基金名称[:：\s]+\w+?基金代码[:：\s]+\d{6}",
                    r"(?P<dst>☑基金转换)转出基金名称[:：\s]+\w+?基金代码[:：\s]+\d{6}",
                ],
            },
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>☑(基金转换|赎回/退出|认购/申购/参与|撤单))",
                    r"(?P<dst>☑((认购/申购/?|/?参与)))",
                    r"参与(?P<dst>赎回/退出)",
                    r"(?P<dst>☑认购/申购/参与)基金名称[:：\s]+\w+?基金代码[:：\s]+\d{6}",
                    r"(?P<dst>☑赎回/退出)基金名称[:：\s]+\w+?基金代码[:：\s]+\d{6}",
                    r"(?P<dst>☑基金转换)转出基金名称[:：\s]+\w+?基金代码[:：\s]+\d{6}",
                ],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"(基金名称[:：].+基金代码[:：]\d+)"],
                "content_pattern": [
                    r"(?P<dst>(基金转换|赎回/退出|认购/申购/参与|撤单))",
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
                    r"基金账号.*?[:：].*?(?P<dst>[0-9a-zA-Z]+)",
                ],
            },
            {"name": "partial_text", "regs": [r"基金账号.*?[:：].*?(?P<dst>[0-9a-zA-Z]+)"]},
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
                    r"(?<!转(出|入))基金名称.*?基金代码.*?[:：].*?(?P<dst>\d+)",
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
                "row_pattern": [r"转入.*?基金代码"],
                "content_pattern": [
                    r"转入.*?基金代码.*?[:：].*?(?P<dst>\d+)",
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
                "row_pattern": [r"转出.*?基金代码"],
                "content_pattern": [
                    r"转出.*?基金代码.*?[:：].*?(?P<dst>\d+)",
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
                "row_pattern": [r"(?<!转[入出])收费方式"],
                "content_pattern": [
                    r"(?<!转[入出])收费方式.*?[:：].*?(?P<dst>[［[]?[√☑E][]］]?[前后]端)",
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
                    r"分红方式.*?[:：].*?(?P<dst>[［[]?[√E][]］]分红)",
                ],
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
        "path": ["是否全部赎回"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"是否全部赎回"],
                "content_pattern": [
                    r"是否全部赎回.*?[:：].*?(?P<dst>☑(是|否))",
                ],
            },
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
                    r"转出收费方式.*?[:：].*?(?P<dst>☑[前后]端)",
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
                    r"转入收费方式.*?[:：].*?(?P<dst>☑[前后]端)",
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
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"交易币种"],
                "content_pattern": [
                    r"交易币种.*?[:：].*?☑(?P<dst>(人民币|美元现汇))",
                ],
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
                "row_pattern": [r"如(遇|发生)巨额赎回.*?是否继续参加下个交易日的赎回交易"],
                "content_pattern": [
                    r"如(遇|发生)巨额赎回.*?是否继续参加下个交易日的赎回交易.*?[:：].*?(?P<dst>☑[是处否])",
                ],
            },
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
