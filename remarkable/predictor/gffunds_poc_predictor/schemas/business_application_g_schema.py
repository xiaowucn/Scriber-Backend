"""广发业务申请表模板g"""

CHECK_MARK = "[☑✓√■\uf052]"
predictor_options = [
    {
        "path": ["交易类型"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "multi": True,
                "row_pattern": [r"(产品名称[:：].+产品代码[:：]\d+)"],
                "content_pattern": [
                    r"(?P<dst>(赎回|认/申购))",
                ],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "multi": True,
                "row_pattern": [r"赎回|认/申购"],
                "content_pattern": [
                    rf"(?P<dst>{CHECK_MARK}(赎回|认/申购))",
                ],
            },
        ],
    },
    {
        "path": ["交易账号"],
        "models": [
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1146#note_280572
            {
                "name": "partial_text",
                "extract_other_element_type": ["SHAPE"],
                "other_element_type_page_range": [0],
                "regs": [r"交易[账帐]号.*?[:：]?.*?(?P<dst>[A-Za-z0-9]+?)(2[\.．]?\s*交易.*)?$"],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"交易[帐账]号"],
                "content_pattern": [
                    r"交易[账帐]号.*?[:：]?.*?(?P<dst>[A-Za-z0-9]+)",
                ],
            },
        ],
    },
    {
        "path": ["基金账号"],
        "models": [
            {"name": "partial_text", "regs": [r"基金账号/投资者账号：(?P<dst>[A-Za-z0-9]+)"]},
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"基金账号/投资者账号"],
                "content_pattern": [
                    r"基金账号/投资者账号[:：](?P<dst>[A-Za-z0-9]+)",
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
                    r"(产品代码[：:](?P<dst>\d+))",
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
                    r"小写.*?(?P<dst>[\d·点]+)",
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
                    rf"如(遇|发生)巨额赎回.*?对未获兑付部分.*?您选择.*?[:：].*?(?P<dst>(撤[销消]赎回申请|延迟办理)[\[［]?{CHECK_MARK}]?)",
                ],
            },
            {
                "name": "partial_text",
                "regs": [rf"如遇巨额赎回.*?是否顺延未获确认部分至下个交易日[：:]?.*?(?P<dst>([{CHECK_MARK}]?(是|否))"],
            },
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
