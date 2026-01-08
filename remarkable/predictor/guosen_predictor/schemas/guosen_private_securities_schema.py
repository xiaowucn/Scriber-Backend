"""
国信证券-私募证券投资基金基金合同POC
"""

predictor_options = [
    {
        "path": ["托管人"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["基金类型"],
        "models": [
            {"name": "para_match", "paragraph_pattern": [r"(?P<dst>本基金为.*?基金)"]},
        ],
    },
    {
        "path": ["投资目标"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["初始销售面值"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["风险承受能力"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["初始认购金额"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["账户名称"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["销售失败的处理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    "__regex__基金初始销售失败的处理$",
                ],
            },
        ],
    },
    {
        "path": ["投资经理"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"本基金投资经理为：【(?P<dst>.*)】"],
            },
        ],
    },
    {
        "path": ["固定开放日"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>本基金自成立之日起.*?为固定开放日，(如|开放日){2}遇节假日则顺延至下一个?工作日)",
                    r"(?P<dst>本基金自成立之日起，.?每个.*?的最后.*?个工作日.?为固定开放日)",
                    r"(?P<dst>本基金自成立之日起不设置固定开放日.自.*?每个最后一个工作日为固定开放日)",
                    r"(?P<dst>本基金自成立之日起.*?不设置固定开放日.*?每个.*?个工作日为固定开放日)",
                    r"(?P<dst>封闭期届满后的.*为固定开放日，遇节假日顺延至下一个工作日)",
                ],
            },
        ],
    },
    {
        "path": ["赎回限制天数"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>基金份额持有不满.*?不得在固定开放日赎回)",
                ],
            },
        ],
    },
    {
        "path": ["申购费率"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"(?P<dst>本基金不收取申购费用)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["赎回价格"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["免赎回费期限天数"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"赎回费.*(?P<dst>持有产品超过.*?份额不收取赎回费)",
                    r"(?P<dst>赎回费.?向持有产品不满.*?的.*?份额收取)",
                ],
            },
        ],
    },
    {
        "path": ["是否收取服务费"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>本基金的服务费自基金成立日起，每日计提，按[年季]支付)",
                ],
            },
        ],
    },
    {
        "path": ["服务费费率"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["是否收取托管费"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>本基金的托管费自基金成立日起，每日计提，按[年季]支付)",
                ],
            },
        ],
    },
    {
        "path": ["托管费费率"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [r"本基金的托管费按前一日基金资产净值的(?P<dst>.*)年费率计提"],
            },
        ],
    },
    {
        "path": ["可供分配利润构成"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["收益分配方式"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>本基金不进行收益分配。?)",
                ],
            },
        ],
    },
]


prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
