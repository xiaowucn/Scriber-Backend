"""广发业务申请表模板c"""

predictor_options = [
    {
        "path": ["交易类型"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"(转换|赎回|申[(（]认[)）]购)"],
                "content_pattern": [
                    r"业务类型[：:].*?(?P<dst>(转换|赎回|申[(（]认[)）]购))",
                ],
            },
            {
                "name": "partial_text",
                "extract_other_element_type": ["SHAPE"],
                "other_element_type_page_range": [0],
                "regs": [r"业务类型[：:](?P<dst>(转换|赎回|申[(（]认[)）]购))"],
            },
        ],
    },
    {
        "path": ["交易账号"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"交易[账帐]号"],
                "content_pattern": [
                    r"交易[账帐]号.*?[:：]?.*?(?P<dst>\d+)",
                ],
            },
            {
                "name": "partial_text",
                "regs": [
                    r"交易[账帐]号.{0,1}[:：]?(?P<dst>\d+)",
                ],
            },
        ],
    },
    {
        "path": ["基金账号"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"基金[账帐]号"],
                "content_pattern": [
                    r"基金[账帐]号.*?[:：].*?(?P<dst>[A-Za-z0-9]{10,})",
                ],
            },
            {
                "name": "partial_text",
                "extract_other_element_type": ["SHAPE"],
                "other_element_type_page_range": [0],
                "regs": [
                    r"基金[账帐]号.*?[:：].*?(?P<dst>[A-Za-z0-9]{10,})",
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
                "row_pattern": [r"基金代码"],
                "content_pattern": [
                    r"(?<!转(出|入))基金代码.*?[:：].*?(?P<dst>\d+)",
                ],
            },
            {
                "name": "partial_text",
                "extract_other_element_type": ["SHAPE"],
                "other_element_type_page_range": [0],
                "regs": [
                    r"(?<!转(出|入))基金代码.*?[:：].*?(?P<dst>\d+)",
                ],
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
                "regs": [
                    r"转入.*?基金代码.*?[:：].*?(?P<dst>\d+)",
                ],
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
                "regs": [
                    r"转出.*?基金代码.*?[:：].*?(?P<dst>\d+)",
                ],
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
                    r"分红方式.*?[:：].*?(?P<dst>(现金红利|红利再投资?|现金分红))",
                ],
            },
            {
                "name": "partial_text",
                "extract_other_element_type": ["SHAPE"],
                "other_element_type_page_range": [0],
                "regs": [
                    r"分红方式.*?[:：].*?(?P<dst>(现金红利|红利再投资?|现金分红))",
                ],
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
                    r"(?P<dst>\d+)",
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
                    r"如(遇|发生)巨额赎回.*?是否继续参加下个交易日的赎回交易.*?[:：].*?(?P<dst>☑[是否])",
                ],
            },
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
