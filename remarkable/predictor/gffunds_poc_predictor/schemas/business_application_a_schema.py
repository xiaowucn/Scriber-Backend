"""广发业务申请表A"""

P_CHECK_MARK = r"(([［[][✓√门/]+[]］]?\]?)|(√))\s*"
predictor_options = [
    {
        "path": ["交易类型"],
        "models": [
            {
                "name": "partial_text",
                # http://scriber-gffound-test.test.paodingai.com/#/project/remark/8914?treeId=7&fileId=27&schemaId=1&projectId=2&task_type=extract&fileName=A-%E8%BD%AC%E6%8D%A23.png
                "extract_other_element_type": ["SHAPE"],
                "other_element_type_page_range": [0],
                "regs": [r"(?<!贵公司)开放式基金(?P<dst>.*)业务申请表"],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"业务申请表"],
                "content_pattern": [
                    r"开放式基金(?P<dst>.*)业务申请表",
                    r"(?P<dst>转换|申（认）购 )",
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
                    r"交易账号[:：](?P<dst>[0-9a-zA-Z]{3,})",
                ],
            },
            {
                "name": "partial_text",
                "extract_other_element_type": ["SHAPE"],
                "other_element_type_page_range": [0],
                "regs": [r"交易账号[:：](?P<dst>[0-9a-zA-Z]{3,})"],
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
                    r"基金账号[:：](?P<dst>[0-9a-zA-Z]+)",
                ],
            },
            {
                "name": "partial_text",
                "extract_other_element_type": ["SHAPE"],
                "other_element_type_page_range": [0],
                "regs": [r"基金账号[:：](?P<dst>[0-9a-zA-Z]+)"],
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
                    r"(?<!转(出|入))基金代码[:：](?P<dst>\d+)",
                ],
            },
            {
                "name": "partial_text",
                "model_alternative": True,
                "extract_other_element_type": ["SHAPE"],
                "other_element_type_page_range": [0],
                "regs": [r"(?<!转(出|入))基金代码[:：]\s*?(?P<dst>\d+)"],
            },
        ],
    },
    {
        "path": ["转入基金代码"],
        "models": [
            {
                "name": "row_match",
                "merge_row": False,
                "row_pattern": [r"转入基金代码"],
                "content_pattern": [
                    r"转入基金代码.*?[:：].*?(?P<dst>\d+)",
                ],
            },
            {
                "name": "partial_text",
                "model_alternative": True,
                "extract_other_element_type": ["SHAPE"],
                "other_element_type_page_range": [0],
                "regs": [r"转入基金代码.*?[:：].*?(?P<dst>\d+)"],
            },
        ],
    },
    {
        "path": ["转出基金代码"],
        "models": [
            {
                "name": "row_match",
                "merge_row": False,
                "row_pattern": [r"转出基金代码"],
                "content_pattern": [
                    r"转出基金代码.*?[:：].*?(?P<dst>\d+)",
                ],
            },
            {
                "name": "partial_text",
                "model_alternative": True,
                "extract_other_element_type": ["SHAPE"],
                "other_element_type_page_range": [0],
                "regs": [r"转出基金代码.*?[:：].*?(?P<dst>\d+)"],
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
                    rf"收费方式.*?[:：].*?(?P<dst>{P_CHECK_MARK}[前后]端收费)",
                ],
            },
            {
                "name": "partial_text",
                "extract_other_element_type": ["SHAPE"],
                "other_element_type_page_range": [0],
                "regs": [rf"收费方式.*?[:：].*?(?P<dst>{P_CHECK_MARK}[前后]端收费)"],
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
                    rf"分红方式.*?[:：].*?(?P<dst>{P_CHECK_MARK}(红利再投资|现金再?分红))",
                ],
            },
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    rf"分红方式.*?[:：].*?(?P<dst>{P_CHECK_MARK}(红利再投资|现金再?分红))",
                ],
            },
            {
                "name": "para_match",
                "force_use_all_elements": True,
                "use_crude_answer": False,
                "content_pattern": True,
                "index_range": (0, 20),
                "paragraph_pattern": [
                    rf"分红方式.*?[:：].*?(?P<content>{P_CHECK_MARK}(红利再投资|现金再?分红))",
                ],
            },
            {
                "name": "shape_text",
                "regs": [rf"分红方式.*?[:：].*?(?P<dst>{P_CHECK_MARK}(红利再投资|现金再?分红))"],
            },
        ],
    },
    {
        "path": ["金(份)额小写"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"￥[:：]?(?P<dst>\d+)",
                ],
            },
            {
                "name": "parse_money",
                "merge_row": True,
                "row_pattern": [r"亿[仟任]佰拾万[仟任]佰拾"],
                "content_pattern": [
                    r"(?P<dst>\d+)",
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
                "row_pattern": [r"巨额(赎回|转换)"],
                "content_pattern": [
                    rf"巨额(赎回|转换).*?[:：].*?(?P<dst>{P_CHECK_MARK}(顺延|撤销))",
                    rf"(?P<dst>{P_CHECK_MARK}(顺延|撤销))",
                ],
            },
            {
                "name": "partial_text",
                "model_alternative": True,
                "extract_other_element_type": ["SHAPE"],
                "other_element_type_page_range": [0],
                "regs": [
                    rf"(?P<dst>{P_CHECK_MARK}(顺延|撤销))",
                    rf"巨额(赎回|转换).*?[:：].*?(?P<dst>{P_CHECK_MARK}(顺延|撤销))",
                ],
            },
        ],
    },
    {
        "path": ["交易币种"],
        "models": [
            {
                "name": "partial_text",
                "extract_other_element_type": ["SHAPE"],
                "other_element_type_page_range": [0],
                "regs": [r"大写[:：].*?(?P<dst>人民币)"],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"大写[:：].*?(?P<dst>人民币)"],
                "content_pattern": [r"大写[:：].*?(?P<dst>人民币)"],
            },
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
