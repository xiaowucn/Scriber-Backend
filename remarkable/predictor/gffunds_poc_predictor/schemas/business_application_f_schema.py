"""广发业务申请表模板f"""

CHECK_MARK = "[☑✓√■\uf052]"
predictor_options = [
    {
        "path": ["交易类型"],
        "models": [
            {
                "name": "partial_text",
                "multi_elements": True,
                "regs": [r"基金(?P<dst>(赎回|认购/申购))申请表"],
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
            {"name": "partial_text", "regs": [r"基金[账帐]户卡号(?P<dst>[A-Za-z0-9]{10,})"]},
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"基金[账帐]户卡号"],
                "content_pattern": [
                    r"基金[账帐]户卡号(?P<dst>[A-Za-z0-9]{10,})",
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
                    r"(基金代码(?P<dst>\d+))",
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
                    r"(?P<dst>\d+)",
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
                "row_pattern": [r"金额", r"[￥¥]"],
                "content_pattern": [
                    r"(?P<dst>[￥¥])",
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
                "row_pattern": [r"如(遇|发生)巨额赎"],
                "content_pattern": [
                    rf"如(遇|发生)巨额赎.*?对未获兑付部分.*?您选择.*?[:：].*?(?P<dst>(撤[销消]赎回申请|延迟办理)[\[［]?{CHECK_MARK}]?)",
                ],
            },
            {
                "name": "partial_text",
                "regs": [
                    rf"如(遇|发生)巨额赎.*?对未获兑付部分.*?您选择.*?[:：].*?(?P<dst>(撤[销消]赎回申请|延迟办理)[\[［]?{CHECK_MARK}]?)"
                ],
            },
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
