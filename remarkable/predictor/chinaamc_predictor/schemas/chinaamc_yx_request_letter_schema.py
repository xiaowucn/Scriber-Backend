def table_as_paras_auto(prefix_key: str, is_percent: bool = False) -> dict:
    return {
        "name": "elements_collector_based",
        "elements_collect_model": "middle_paras",
        "elements_collect_config": {
            "top_anchor_regs": [r"基金的?基本情况$"],
            "bottom_anchor_regs": [
                r"条件的?说明$",
                r"附件[一二三四五六七八九十零〇\d]+",
            ],
            "use_top_crude_neighbor": False,
            "table_regarded_as_paras": True,
            "keep_dummy": True,
        },
        "paragraph_model": "auto",
        "para_config": {
            "model_alternative": True,
            "regs": [
                rf"^(基金)?{prefix_key}.*?(?P<dst>\d+(\.\d+)?[%％])" if is_percent else "^$",
                rf"^(基金)?{prefix_key}[：:]?(?P<dst>.*)",
            ],
        },
    }


elements_nearby = {
    "elements_nearby": {
        "regs": [r"中国证券监督管理委员会[：:]$"],
        "amount": 20,
        "step": -1,
    },
}
predictor_options = [
    {
        "path": ["001基金名称"],
        "models": [
            {
                "name": "middle_paras",
                "top_anchor_regs": [
                    r"(募集|变更注册为?)华夏",
                ],
                "bottom_anchor_regs": [
                    "的请示",
                ],
                "top_anchor_content_regs": [
                    r"(募集|变更注册为?)(?P<content>华夏.*)的请示",
                    r"(募集|变更注册为?)(?P<content>华夏.*)",
                ],
                "bottom_anchor_content_regs": ["(?P<content>.*)的请示"],
                "include_bottom_anchor": True,
            },
            {
                "name": "auto",
                "use_answer_pattern": False,
                "multi_elements": True,
                "order_by_index": True,
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4658
                "regs": [
                    r"募集(?P<dst>华夏.*)的请示",
                    r"(?P<dst>.*)的请示",
                ],
            },
        ],
    },
    {
        "path": ["002基金名称"],
        "models": [
            {
                "name": "table_kv",
                **elements_nearby,
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["003管理人"],
        "models": [
            {
                "name": "table_kv",
                "regs": [
                    r"(?P<dst>[^。]*)",
                ],
                **elements_nearby,
            },
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>[^。]*)",
                ],
            },
        ],
    },
    {
        "path": ["004托管人"],
        "models": [
            {
                "name": "table_kv",
                "regs": [
                    r"(?P<dst>[^。]*)",
                ],
                **elements_nearby,
            },
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>[^。]*)",
                ],
            },
        ],
    },
    {
        "path": ["005基金经理"],
        "models": [
            {
                "name": "table_kv",
                "regs": [
                    r"(?P<dst>[^。]*)",
                ],
                **elements_nearby,
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["006运作方式"],
        "models": [
            {
                "name": "table_kv",
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["007投资目标"],
        "models": [
            {
                "name": "table_kv",
                **elements_nearby,
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["008投资范围"],
        "models": [
            {
                "name": "table_kv",
                **elements_nearby,
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["009投资比例"],
        "models": [
            {
                "name": "table_kv",
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4659
                "feature_white_list": [
                    r"投资比例",
                ],
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["010业绩比较基准"],
        "models": [
            {
                "name": "table_kv",
                **elements_nearby,
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4660
                "regs": [
                    r"(?P<dst>.*?。)",
                ],
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["011管理费率"],
        "models": [
            {
                "name": "table_kv",
                "multi_answer_in_one_cell": True,
                "regs": [
                    r"(?P<dst>[\d+\.]+[%％])",
                ],
                **elements_nearby,
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["012托管费率"],
        "models": [
            {
                "name": "table_kv",
                "multi_answer_in_one_cell": True,
                "regs": [
                    r"(?P<dst>[\d+\.]+[%％])",
                ],
                **elements_nearby,
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["013销售服务费"],
        "models": [
            {
                "name": "table_kv",
                "multi_answer_in_one_cell": True,
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["014认购费率"],
        "models": [
            {
                "name": "table_kv",
                "multi_answer_in_one_cell": True,
                "regs": [
                    r"如下[：:](?P<dst>[^，,。]*?)(本基金|$)",
                    r"(?P<dst>本?基金[A-Z]类份额不收取认购费)",
                ],
            },
            {
                "name": "auto",
                "multi": True,
            },
        ],
    },
    {
        "path": ["015申购费率"],
        "models": [
            {
                "name": "table_kv",
                "multi_answer_in_one_cell": True,
                "regs": [
                    r"如下[：:](?P<dst>[^，,。]*?)(本基金|$)",
                    r"(?P<dst>本?基金[A-Z]类份额不收取申购费)",
                ],
            },
            {
                "name": "auto",
                "multi": True,
            },
        ],
    },
    {
        "path": ["016赎回费"],
        "models": [
            {
                "name": "table_kv",
                "multi_answer_in_one_cell": True,
                "regs": [
                    r"如下[：:](?P<dst>[^，,。]*?)(对(于|持续)|$|所?收取|本基金)",
                ],
            },
            {
                "name": "auto",
                "multi": True,
            },
        ],
    },
    {
        "path": ["017管理人"],
        "models": [
            {
                "name": "auto",
                # # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4657
                "regs": [
                    "第六条[,，](?P<dst>[^,，、]*)",
                ],
            },
        ],
    },
    {
        "path": ["018托管人"],
        "models": [
            {
                "name": "auto",
                "regs": [
                    "第六条.*?公司[、，,](?P<dst>.*?)符合",
                ],
            },
        ],
    },
    {
        "path": ["019管理人"],
        "models": [
            {
                "name": "auto",
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4657
                "regs": [
                    "第六条.*。(?P<dst>.*?公司)",
                ],
            },
        ],
    },
    {
        "path": ["020托管人"],
        "models": [
            {
                "name": "auto",
                "regs": [
                    "第六条.*?托管人.*?管理公司[、，,](?P<dst>.*?)为",
                ],
            },
        ],
    },
    {
        "path": ["021基金名称"],
        "models": [
            {
                "name": "auto",
            },
            {
                "name": "syllabus_based",
                "include_title": False,
                "only_inject_features": True,
                "inject_syllabus_features": [r"__regex__(销售|系统)准备情况$"],
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [
                        "(?P<content>^.*?)属于",
                    ],
                },
            },
        ],
    },
    {
        "path": ["022基金名称"],
        "models": [
            {
                "name": "auto",
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4656
                "regs": [
                    r"[“\"](?P<dst>.*)[”\"]是可行的",
                ],
            },
        ],
    },
]


prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
