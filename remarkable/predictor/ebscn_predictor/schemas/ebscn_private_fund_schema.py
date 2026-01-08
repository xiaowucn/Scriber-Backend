"""光大POC"""

predictor_options = [
    {
        "path": ["产品代码"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>\d{6})\]?-001",
                ],
            },
        ],
    },
    {
        "path": ["产品名称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>.*?基金名称$)",
                ],
            },
        ],
    },
    {
        "path": ["管理人名称"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["管理人代码"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["认购费率"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["首次投资最低金额"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["认购利息处理方式"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["基金申购和赎回的开放日"],
        "models": [
            {
                "name": "partial_text",
                "multi_elements": True,
                "order_by_index": True,
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>本基金自基金成立之日起.*?允许赎回)",
                ],
            },
        ],
    },
    {
        "path": ["赎回费率"],
        "models": [
            {"name": "partial_text"},
            {
                "name": "row_match",
                "row_pattern": [
                    r"本基金不收取赎回费用",
                ],
                "content_pattern": [r"(?P<dst>本基金不收取赎回费用)"],
            },
        ],
    },
    {
        "path": ["归基金资产比例"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["赎回后资产低于最低保有金额处理方式"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["净值精度"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["业绩报酬提取"],
        "sub_primary_key": ["基金类型"],
        "models": [
            {
                "name": "performance_extract",
                "multi": True,
                "multi_elements": True,
            },
        ],
    },
    {
        "path": ["业绩报酬计算公式（单公式）"],
        "sub_primary_key": ["基金类型"],
        "models": [
            {
                "name": "single_formula",
                "multi": True,
                "multi_elements": True,
                "model_alternative": True,
                "计提公式": {
                    "regs": [
                        r"(?P<dst>PFi.*?\d+%)",
                        r"(?P<dst>Y=F.*?W$)",
                    ],
                },
            },
        ],
    },
    {
        "path": ["业绩报酬计算公式（多行公式）"],
        "sub_primary_key": ["基金类型"],
        "models": [
            {
                "name": "multi_formula",
                "multi_elements": True,
            },
        ],
    },
]


prophet_config = {"depends": {}, "predictor_options": predictor_options}
