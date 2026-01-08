"""广发业务申请表模板b"""

from remarkable.predictor.gffunds_poc_predictor.schemas.business_application_a_schema import P_CHECK_MARK

predictor_options = [
    {
        "path": ["交易类型"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [
                    # r'(基金转换|赎回|认/申购|转托管)',
                    r"(基金名称[:：].+基金代码[:：]\d+)"
                ],
                "content_pattern": [
                    r"(?P<dst>(\[\-\]|☑|-|√\])(基金转换|赎回|认/申购))",
                    r"(?P<dst>(基金转换|赎回|认/申购))",
                ],
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["交易账号"],
        "models": [
            {"name": "partial_text", "regs": [r"交易[账帐]号.*?[:：]?.*?(?P<dst>[0-9a-zA-Z]+)"]},
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"交易[帐账]号"],
                "content_pattern": [
                    r"交易[账帐]号.*?[:：]?.*?(?P<dst>[0-9a-zA-Z]+)",
                ],
            },
            {
                "name": "choose_account",
                "merge_row": True,
                "need_first_row": False,
                "row_pattern": [r"(?P<dst>[0-9a-zA-Z]+)"],
            },
        ],
    },
    {
        "path": ["基金账号"],
        "models": [
            {"name": "partial_text", "regs": [r"基金[账帐]号.*?[:：]?.*?(?P<dst>[0-9a-zA-Z]+)"]},
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"基金[账帐]号"],
                "content_pattern": [
                    r"基金[账帐]号.*?[:：]?.*?(?P<dst>[0-9a-zA-Z]+)",
                ],
            },
            {
                "name": "choose_account",
                "merge_row": True,
                "need_first_row": True,
                "row_pattern": [r"(?P<dst>[0-9a-zA-Z]+)"],
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
                    r"(基金代码.*?[:：].*?(?P<dst>\d+))",
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
                    rf"收费方式.*?[:：].*?(?P<dst>{P_CHECK_MARK}[前后]端)",
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
                "row_pattern": [r"(转出)?基金代码[:：]?\s*\d+"],
                "content_pattern": [
                    rf"分红方式.*?[:：].*?(?P<dst>{P_CHECK_MARK}(现金(红利|分红)|红利再投资))",
                    r"分红方式.*?[:：]\s*(?P<dst>现金(红利|分红)|红利再投资)",
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
                "row_pattern": [r"亿[仟任]佰拾万[仟任]佰拾"],
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
                "row_pattern": [r"如果发生巨额赎回"],
                "content_pattern": [
                    r"发生巨额赎回.*?将当日未获确认的部分.*?[:：].*?(?P<dst>(?:☑|［√J|\[[✓√]\]|✓|√)(顺延|取消))",
                ],
            },
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
