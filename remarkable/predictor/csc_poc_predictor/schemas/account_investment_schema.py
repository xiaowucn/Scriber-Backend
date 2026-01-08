"""账内投顾协议（帐内投顾）"""

predictor_options = [
    {
        "path": ["甲方"],
        "models": [
            {
                "name": "party_ab",
                "pattern": r"甲方",
            },
        ],
    },
    {
        "path": ["乙方"],
        "models": [
            {
                "name": "party_ab",
                "pattern": r"乙方",
            },
        ],
    },
    {
        "path": ["初始委托资产规模"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"投资的初始投资规模上限为人民币(?P<dst>.*)。",
                ],
            },
        ],
    },
    {
        "path": ["追加倍数"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"不超过初始投资规模的(?P<dst>[\d.]*?倍)，",
                ],
            },
        ],
    },
    {
        "path": ["放大规模之和"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"投资总规模.*?不超过(?P<dst>[\d.]*?亿元)",
                ],
            },
        ],
    },
    {
        "path": ["初始委托资产投资的业绩比较基准"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"业绩比较基准为(?P<dst>[\d.]*?%)，",
                ],
            },
        ],
    },
    {
        "path": ["业绩考核基准资产1", "资产类型"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>现金资产|债券资产)作?为业绩考核基准资产1",
                ],
            },
        ],
    },
    {
        "path": ["业绩考核基准资产1", "初始委托资产规模"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"总资产规模(?P<dst>.*)的.*?为业绩考核基准资产1",
                ],
            },
        ],
    },
    {
        "path": ["业绩考核基准资产1", "追加倍数"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"债券形式的初始委托资产的(?P<dst>.*?倍)",
                ],
            },
        ],
    },
    {
        "path": ["业绩考核基准资产1", "放大规模之和"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"债券形式的初始委托资产的.*?倍.*?即人民币(?P<dst>.*?元)",
                ],
            },
        ],
    },
    {
        "path": ["业绩考核基准资产1", "业绩比较基准"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"业绩考核基准资产1的的?业绩比较基准为(?P<dst>[\d.]*?%)",
                ],
            },
        ],
    },
    {
        "path": ["业绩考核基准资产2", "资产类型"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>现金资产|债券资产)作?为业绩考核基准资产2",
                ],
            },
        ],
    },
    {
        "path": ["业绩考核基准资产2", "初始委托资产规模"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"本协议中人民币(?P<dst>.*?)现金资产作?为业绩考核基准资产2",
                ],
            },
        ],
    },
    {
        "path": ["业绩考核基准资产2", "追加倍数"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"现金形式的初始委托资产的(?P<dst>.*?倍)",
                ],
            },
        ],
    },
    {
        "path": ["业绩考核基准资产2", "放大规模之和"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"现金形式的初始委托资产的.*?倍.*?即人民币(?P<dst>.*?元)",
                ],
            },
        ],
    },
    {
        "path": ["业绩考核基准资产2", "业绩比较基准"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"业绩考核基准资产2的的?业绩比较基准为(?P<dst>[\d.]*?%)",
                ],
            },
        ],
    },
    {
        "path": ["业务往来邮件邮寄地址（甲方）"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["联系电话（甲方）"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["传真号码（甲方）"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["联系人及授权名册（甲方）"],
        "sub_primary_key": ["岗位", "姓名"],
        "models": [
            {
                "name": "table_row",
                "岗位": {
                    "feature_from": "self",
                },
            },
        ],
    },
    {
        "path": ["业务往来邮件邮寄地址（乙方）"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"业务往来邮件邮寄地址[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["全国统一总机"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"全国统一总机[:：](?P<dst>.*)传真号码",
                ],
            },
        ],
    },
    {
        "path": ["传真号码（乙方）"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"传真号码[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["联系人及授权名册（乙方）"],
        "sub_primary_key": ["岗位", "姓名"],
        "models": [
            {
                "name": "table_row",
                "岗位": {
                    "feature_from": "self",
                    "feature_black_list": [r"姓名"],
                },
                "姓名": {
                    "feature_black_list": [r"岗位"],
                },
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
