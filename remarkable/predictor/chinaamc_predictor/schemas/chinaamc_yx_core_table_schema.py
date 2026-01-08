"""华夏营销部-核心要素表V1"""

predictor_options = [
    {
        "path": ["001基金名称"],
        "models": [
            {"name": "table_kv"},
        ],
    },
    {
        "path": ["002管理人"],
        "models": [
            {"name": "table_kv"},
        ],
    },
    {
        "path": ["003托管人"],
        "models": [
            {"name": "table_kv"},
        ],
    },
    {
        "path": ["004投资目标"],
        "models": [
            {"name": "table_kv"},
        ],
    },
    {
        "path": ["005投资范围"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["006投资比例"],
        "models": [
            {"name": "table_kv"},
        ],
    },
    {
        "path": ["007投资策略"],
        "models": [
            {
                "name": "row_match",
                "width_from_all_rows": True,
                "row_pattern": [r"\d主要投资策略"],
                "content_pattern": [
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4222
                    r"\d主要投资策略.*?(?P<dst>[(（]?1[）)、].*[。])未来[,，]",  # 提取内容从1、开始
                    r"\d主要投资策略.*?(?P<dst>[(（]?1[）)、].*)",
                ],
            },
            {
                "name": "auto",
                "width_from_all_rows": True,
            },
        ],
    },
    {
        "path": ["008业绩比较基准"],
        "models": [
            {
                "name": "cell_items",
                "key_pattern": [r"\d+业绩比较基准"],
                "sub_start_end": (0, 1),
                "split_pattern": "[:：]",
            },
        ],
    },
    {
        "path": ["009管理费"],
        "models": [
            {
                "name": "row_match",
                "width_from_all_rows": True,
                "multi_answer_in_one_cell": True,
                "row_pattern": [r"管理费率"],
                "content_pattern": [
                    # r"管理费率.*?(?P<dst>基金资产净值不高于.*管理费率为[\d\.]+[%％]。?)",
                    # r"管理费率.*?(?P<dst>按前一日.*年费率计提)",
                    r"(?<!同类型基金)管理费率.*?(?P<dst>[\d\.]+[%％])",
                ],
            }
        ],
    },
    {
        "path": ["010托管费"],
        "models": [
            {
                "name": "row_match",
                "width_from_all_rows": True,
                "multi_answer_in_one_cell": True,
                "row_pattern": [r"托管费率"],
                "content_pattern": [
                    # r"托管费率.*?(?P<dst>按前一日基金资产净值扣除基金资产中本基金托管人托管的基金份额所对应资产净值后剩余部分.*?年费率计提)",
                    r"(?<!同类型基金)托管费率.*?(?P<dst>[\d\.]+[%％])",
                ],
            }
        ],
    },
    {
        "path": ["011最高认购费率"],
        "models": [
            {
                "name": "row_match",
                "width_from_all_rows": True,
                "row_pattern": [r"最高认购费率"],
                "content_pattern": [
                    r"最高认购费率(?P<dst>[\d\.]+[%％])",
                ],
            },
        ],
    },
    {
        "path": ["012最高申购费率"],
        "models": [
            {
                "name": "row_match",
                "width_from_all_rows": True,
                "row_pattern": [r"最高申购费率"],
                "content_pattern": [
                    r"最高申购费率(?P<dst>[\d\.]+[%％])",
                ],
            },
        ],
    },
    {
        "path": ["013销售服务费"],
        "models": [
            {
                "name": "row_match",
                "width_from_all_rows": True,
                "row_pattern": [r"销售服务费（若有）"],
                "neglect_row_pattern": ["无$"],
                "content_pattern": [
                    r"销售服务费[(（]若有[）)](?!无)(?P<dst>[^/]*)",
                ],
            }
        ],
    },
    {
        "path": ["014基金经理"],
        "models": [
            {
                "name": "row_match",
                "width_from_all_rows": True,
                "row_pattern": [r"金经理及其管理?产品数量"],
                "content_pattern": [
                    r"金经理及其管理?产品数量(?P<dst>.*?)[(（，、]",
                ],
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
