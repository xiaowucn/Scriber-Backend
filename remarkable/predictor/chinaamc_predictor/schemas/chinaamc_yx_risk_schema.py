"""华夏营销部-风险评估报告V1"""

elements_nearby = {
    "regs": [r"风险评估报告$"],
    "amount": 20,
    "step": -1,
}

predictor_options = [
    {
        "path": ["001基金名称"],
        "models": [
            {
                "name": "middle_paras",
                "top_anchor_regs": [
                    "^华夏.*型",
                ],
                "bottom_anchor_regs": [
                    "流动性风险评估报告$",
                ],
                "bottom_anchor_content_regs": ["(?P<content>.*?)流动性风险评估报告$"],
                "include_bottom_anchor": True,
            },
            {
                "name": "partial_text",
                "neglect_patterns": [r"的请示$", r"募集"],
                "use_answer_pattern": False,
                "regs": [
                    "(?P<dst>.*?)流动性风险评估报告$",
                    "(?P<dst>华夏.*投资基金$)",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["002基金名称"],
        "models": [
            {
                "name": "partial_text",
                "elements_nearby": elements_nearby,
                "regs": [
                    r"(?P<dst>华夏.+基金.*联接基金([(（]?[a-zA-Z]+[）)])?)",
                    r"(?P<dst>华夏.*?基金中基金([(（]?[a-zA-Z]+[）)])?)",
                    r"(?P<dst>华夏.*?基金([(（]?[a-zA-Z]+[）)])?)",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["003基金名称"],
        "models": [
            {
                "name": "table_kv",
                "elements_nearby": elements_nearby,
            },
        ],
    },
    {
        "path": ["004管理人"],
        "models": [
            {
                "name": "table_kv",
                "regs": [
                    r"(?P<dst>[^。]*)",
                ],
                "elements_nearby": elements_nearby,
            },
            {
                "name": "row_match",
                "row_pattern": [r"管理人"],
                "content_pattern": [
                    r"管理人[:：](?P<dst>[^。]*)",
                ],
                "elements_nearby": elements_nearby,
            },
        ],
    },
    {
        "path": ["005托管人"],
        "models": [
            {
                "name": "table_kv",
                "regs": [
                    r"(?P<dst>[^。]*)",
                ],
                "feature_black_list": [r"投资范围："],
                "elements_nearby": elements_nearby,
            },
            {
                "name": "partial_text",
                "regs": [r"基金托管人[:：](?P<dst>[^。]*)"],
            },
            {
                "name": "row_match",
                "row_pattern": [r"托管人"],
                "content_pattern": [
                    r"托管人[:：](?P<dst>[^。]*)",
                ],
                "elements_nearby": elements_nearby,
            },
        ],
    },
    {
        "path": ["006基金经理"],
        "models": [
            {
                "name": "table_kv",
                "elements_nearby": elements_nearby,
            },
        ],
    },
    {
        "path": ["007运作方式"],
        "models": [
            {
                "name": "table_kv",
                "elements_nearby": elements_nearby,
            },
            {
                "name": "row_match",
                "row_pattern": [r"运作方式"],
                "content_pattern": [
                    r"运作方式.*[:：](?P<dst>[^。]*)",
                ],
                "elements_nearby": elements_nearby,
            },
        ],
    },
    {
        "path": ["008投资目标"],
        "models": [
            {
                "name": "table_kv",
                "elements_nearby": elements_nearby,
                "feature_white_list": [r"__regex__投资目标"],
                "regs": [r"(?P<dst>.*?)本基金主要投资于"],
            },
            {
                "name": "table_kv",
                "elements_nearby": elements_nearby,
            },
        ],
    },
    {
        "path": ["009投资范围"],
        "models": [
            {
                "name": "table_kv",
                "elements_nearby": elements_nearby,
            },
        ],
    },
    {
        "path": ["010投资比例限制"],
        "models": [
            {
                "name": "table_kv",
                "feature_black_list": [r"投资范围："],
                "elements_nearby": elements_nearby,
            },
        ],
    },
    {
        "path": ["011业绩比较基准"],
        "models": [
            {
                "name": "table_kv",
                "feature_black_list": [r"投资范围："],
                "elements_nearby": elements_nearby,
                "feature_white_list": [r"__regex__业绩比较基准"],
                "neglect_regs": [r"本基金主要投资于"],
                "regs": [
                    r"(?P<dst>[^。:：]*[-+×].*?。)",
                ],
            },
        ],
    },
    {
        "path": ["012管理费率"],
        "models": [
            {
                "name": "table_kv",
                "elements_nearby": elements_nearby,
                "multi_answer_in_one_cell": True,
                "regs": [r"(?P<dst>[\d.]+[%％])"],
            },
            {
                "name": "row_match",
                "row_pattern": [r"管理费"],
                "content_pattern": [
                    r"管理费[:：](?P<dst>.*)",
                ],
                "elements_nearby": elements_nearby,
            },
        ],
    },
    {
        "path": ["013托管费率"],
        "models": [
            {
                "name": "table_kv",
                "multi_answer_in_one_cell": True,
                "elements_nearby": elements_nearby,
                "regs": [r"(?P<dst>[\d.]+[%％])"],
            },
            {
                "name": "row_match",
                "row_pattern": [r"托管费"],
                "content_pattern": [
                    r"托管费[:：](?P<dst>.*)",
                ],
                "elements_nearby": elements_nearby,
            },
        ],
    },
    {
        "path": ["014销售服务费"],
        "models": [
            {
                "name": "table_kv",
                "elements_nearby": elements_nearby,
                "feature_black_list": [r"投资比例"],
            },
            {
                "name": "row_match",
                "row_pattern": [r"销售服务费"],
                "content_pattern": [
                    r"销售服务费[:：](?P<dst>.*)",
                ],
                "elements_nearby": elements_nearby,
            },
        ],
    },
    {
        "path": ["015认购费率"],
        "models": [
            {
                "name": "row_match",
                "row_pattern": [r"认购费率?"],
                "keep_dummy": True,
                "multi": True,
                "content_pattern": [
                    r"认购费率如下[:：](?P<dst>.*?)本基金.类份额不收取认购费",
                    r"认购费率?(如下)?[:：](?P<dst>.*)",
                ],
                "elements_nearby": elements_nearby,
            },
            {
                "name": "table_kv",
                "keep_dummy": True,
                "multi": True,
                "feature_black_list": [r"__regex__投资(范围|比例)：?"],
                "elements_nearby": elements_nearby,
                "regs": [
                    r"认购费率如下[:：](?P<dst>.*?)本基金.类份额不收取认购费",
                ],
            },
        ],
    },
    {
        "path": ["016申购费率"],
        "models": [
            {
                "name": "row_match",
                "row_pattern": [r"申购费率?"],
                "keep_dummy": True,
                "multi": True,
                "content_pattern": [
                    r"申购费率如下[:：](?P<dst>.*?)本基金.类份额不收取认购费",
                    r"申购费率?(如下)?[:：](?P<dst>.*)",
                ],
                "elements_nearby": elements_nearby,
            },
            {
                "name": "table_kv",
                "feature_black_list": [r"__regex__基金认购费", r"__regex__投资范围"],
                "elements_nearby": elements_nearby,
            },
        ],
    },
    {
        "path": ["017赎回费"],
        "models": [
            {
                "name": "row_match",
                "row_pattern": [r"赎回费率?"],
                "keep_dummy": True,
                "multi": True,
                "content_pattern": [
                    r"赎回费率如下[:：](?P<dst>.*?)本基金.类份额不收取认购费",
                    r"赎回费率?(如下)?[:：](?P<dst>.*)",
                ],
                "elements_nearby": elements_nearby,
            },
            {
                "name": "table_kv",
                "feature_black_list": [r"__regex__投资范围", r"__regex__基金认购费"],
                "elements_nearby": elements_nearby,
            },
        ],
    },
    {
        "path": ["018投资范围"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"投资范围"],
                "only_inject_features": True,
                "break_para_pattern": [r"可以将其纳入投资范围", "可.*约定.参与融资业务"],
                "include_break_para": True,
            },
            {
                "name": "middle_paras",
                "top_anchor_regs": [
                    r"本基金(主要投资于|的?投资范围为)",
                ],
                "bottom_anchor_regs": [
                    "将其纳入投资范围",
                ],
                "top_anchor_content_regs": ["(?P<content>本基金(主要投资于|的?投资范围为).*)"],
                "bottom_anchor_content_regs": ["(?P<content>.*将其纳入投资范围)"],
                "include_bottom_anchor": True,
            },
            {
                "name": "partial_text",
                "regs": [
                    r"本基金的投资范围为.*",
                    r"本基金主要投资于.*将其纳入投资范围",
                    r"本基金主要投资于.*其他金融工具",
                ],
            },
        ],
    },
    {
        "path": ["019基金名称"],
        "models": [
            {
                "name": "middle_paras",
                "top_anchor_regs": [
                    "本页无",
                ],
                "bottom_anchor_regs": [
                    "流动性风险评估报告",
                ],
                "top_anchor_content_regs": ["(?P<content>华夏.*)"],
                "bottom_anchor_content_regs": ["(?P<content>.*?)流动性风险评估报告"],
                "include_bottom_anchor": True,
            },
            {
                "name": "partial_text",
                # 最后页可能是空白
                "page_range": [-1, -2],
                "regs": [r"本页.*(?P<dst>华夏.*?)流动"],
            },
        ],
    },
]
prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
