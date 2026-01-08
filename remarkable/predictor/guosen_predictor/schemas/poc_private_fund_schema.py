"""私募基金合同-poc"""

predictor_options = [
    {
        "path": ["Product name"],
        "models": [
            {
                "name": "fixed_position",
                "filter_headers": True,
                "multi_elements": True,
                "positions": list(range(0, 3)),
                "regs": [
                    r"(?P<dst>.*基金合同)",
                    r"(?P<dst>.*(私募|投资)基金)",
                ],
                "neglect_patterns": [r"(管理|托管)人"],
            },
        ],
    },
    {
        "path": ["Manager name"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["运作方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "multi": False,
                "multi_elements": False,
                "only_first": False,
                "include_title": False,
            }
        ],
    },
    {
        "path": ["存续期限"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["基金产品风险评级"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["认购费率"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>本基金不收取认购费用?.)",
                ],
            },
        ],
    },
    {
        "path": ["认购期利息处理方式"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    r"销售期间.*?利息.*?(?P<dst>归投资者所有)",
                ],
            },
        ],
    },
    {
        "path": ["投资范围"],
        "models": [
            {
                "name": "syllabus_based",
                "ignore_syllabus_children": True,
                "ignore_syllabus_range": True,
                "extract_from": "same_type_elements",
                "paragraph_model": "middle_paras",
                "para_config": {
                    "include_top_anchor": False,
                    "include_bottom_anchor": False,
                    "top_anchor_regs": [r"本基金的?投资范围"],
                    "bottom_anchor_regs": [r"基金在中国基金业协会"],
                },
            },
        ],
    },
    {
        "path": ["预警线"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>本产品.?不设置.?预警线及止损线)",
                    r"(?P<dst>本产品.?不设置.?预警线)",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [r"^无.$"],
                "anchor_regs": [r"风险控制"],
            },
        ],
    },
    {
        "path": ["止损线"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>本产品.?不设置.?预警线及止损线)",
                    r"(?P<dst>本产品.?不设置.?止损线)",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [r"^无.$"],
                "anchor_regs": [r"风险控制"],
            },
        ],
    },
    {
        "path": ["赎回限制天数"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>基金份额持有不满.*不得在固定开放日赎回)",
                ],
            },
        ],
    },
    {
        "path": ["免赎回费期限天数"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"赎回费.?(?P<dst>向持有产品不满.*?份额收取)",
                ],
            },
        ],
    },
    {
        "path": ["申购价格"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "multi": False,
                "multi_elements": False,
                "only_first": False,
                "include_title": False,
            }
        ],
    },
    {
        "path": ["赎回费率"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"赎回费.*?费率为(?P<dst>[\d.%]+)",
                    r"本基金不收取赎回费",
                ],
            }
        ],
    },
    {
        "path": ["巨额赎回比例"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["管理费费率"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>本基金(的管理人)?不(收取|计提)管理费)",
                ],
            },
        ],
    },
    {
        "path": ["是否收取管理费"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    r"(?P<dst>本基金的管理费.*?每日计提)",
                    r"(?P<dst>本基金(的管理人)?不(收取|计提)管理费)",
                ],
            },
        ],
    },
    {
        "path": ["托管费封底金额"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["业绩报酬计提方式"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    r".*(计提|提取)业绩报酬.*",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [r"^无.$"],
                "anchor_regs": [r"业绩报酬"],
            },
        ],
    },
    {
        "path": ["收益分配基准日"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": False,
            },
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
