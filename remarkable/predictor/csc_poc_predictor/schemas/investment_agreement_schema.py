"""一对一专户投顾协议（固益联、委外专户）"""

predictor_options = [
    {
        "path": ["甲方", "甲方（管理人/受托人）"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"甲方（受托人）[:：](?P<dst>.*?公司)",
                ],
            },
        ],
    },
    {
        "path": ["甲方", "法定代表人"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"法定代表人[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["甲方", "住所"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"住所[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["乙方", "乙方（投资顾问）"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"乙方（投资顾问）[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["乙方", "法定代表人"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"法定代表人[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["乙方", "通讯地址"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"通讯地址[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["甲方名单"],
        "sub_primary_key": ["岗位", "姓名"],
        "models": [
            {
                "name": "table_row",
                "岗位": {
                    "feature_black_list": [r"姓名"],
                },
                "姓名": {
                    "feature_black_list": [r"岗位"],
                },
            },
        ],
    },
    {
        "path": ["乙方名单"],
        "sub_primary_key": ["姓名"],
        "models": [
            {
                "name": "table_row",
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
