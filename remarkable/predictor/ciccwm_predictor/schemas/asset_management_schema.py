"""
资管合同POC
"""

predictor_options = [
    {
        "path": ["产品名称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    "中金财富(?P<dst>.+?)FOF",
                    "中金财富(?P<dst>.+?)(单一|集合)资产管理计划",
                ],
            },
        ],
    },
    {
        "path": ["委托方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["投资经理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["产品类型"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["业绩报酬A"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["业绩报酬B"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["固定管理费率"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": ["管理费按前一日集合计划资产净值的(?P<dst>.+?)的年费率计提"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["投资者姓名名称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["合同编码"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["住所"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"投资者"],
            },
        ],
    },
    {
        "path": ["联系人"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"投资者"],
            },
        ],
    },
    {
        "path": ["通讯地址"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"投资者"],
            },
        ],
    },
    {
        "path": ["联系电话"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"投资者"],
            },
        ],
    },
    {
        "path": ["电子邮箱"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"投资者"],
            },
        ],
    },
    {
        "path": ["认购费率"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": ["本(单一|集合)计划认购费率为(?P<dst>.+[%％])"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["追加费率"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["提取费率"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["投资者信息披露指定电子邮箱"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["托管费率"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
]


prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
