from remarkable.plugins.predict.predictor import AIAnswerPredictor

predictors = [
    {
        "path": [
            "产品基本信息",
            "是否结构化",
        ],
        "model": "enum_value",
        "deny_regs": [r"(?P<dst>不设置(结构化|分级)安排)"],
    },
    {
        "path": [
            "产品基本信息",
            "是否允许临开",
        ],
        "model": "enum_value",
        "deny_regs": [
            r"(?P<dst>在?本基金存续期[内间](封闭式?运作)?[，。]?不(办理|开放|能)申购(和赎回业务|参与或退出))",
            r"合伙企业(^[，。]*)?(?P<dst>不接[纳受]新的(有限)合伙人入伙)",
            r"(?P<dst>存续期间不增?设立?开放日)",
            r"(?P<dst>(无|不设[定立置]?)临时开放日)",
        ],
    },
    {
        "path": [
            "产品基本信息",
            "是否允许合同展期",
        ],
        "model": "enum_value",
        "deny_regs": [
            r"(?P<dst>.*债券回购到期后不展期)",
        ],
    },
    # {
    #     "path": ["管理人及代销机构信息"],
    #     "model": "partial_text",
    #     "around_regs": {
    #         "联系电话": [
    #             ('联系电话：', ''), ],
    #     },/
    #     "valid": {
    #         "fullfill": 0.1,
    #     }
    # },
    {
        "path": [
            "投资信息",
            "投资范围",
        ],
        "model": "multi_paras",
    },
    {
        "path": [
            "投资信息",
            "最大投资比例",
        ],
        "model": "multi_paras",
    },
    # {
    #     "path": [
    #         "托管外包信息",
    #     ],
    #     "model": "partial_text",
    # },
    {
        "path": [
            "募集期信息",
            "是否设置回访",
        ],
        "model": "enum_value",
        "deny_regs": [r"(?P<dst>不设回访制度)"],
    },
    # {
    #     "path": [
    #         "申赎信息",
    #     ],
    #     "model": "partial_text",
    # },
    # {
    #     "path": [
    #         "费用信息",
    #     ],
    #     "model": "partial_text",
    # },
    # {
    #     "path": [
    #         "业绩报酬",
    #     ],
    #     "model": "partial_text",
    # },
    # {
    #     "path": [
    #         "募集账户信息",
    #     ],
    #     "model": "partial_text",
    # },
    {
        "path": [
            "托管账户信息",
        ],
        "model": "partial_text",
        "near_regs": [r"托管费收费账户信息|托管账号信息|收取托管费用?的?(银行)?账户"],
    },
    {
        "path": [
            "管理费账户信息",
        ],
        "model": "partial_text",
        "regs": {
            "账号": [
                r"账号[：:]\s?[“【](?P<dst>.*?)[”】]",
                r"账号[：:]\s?(?P<dst>\d*)",
            ],
        },
        "near_regs": [r"业绩报酬|管理费|投资顾问费"],
    },
    {
        "path": [
            "业绩报酬账户信息",
        ],
        "model": "partial_text",
        "near_regs": [
            r"业绩报酬|投资顾问费",
        ],
    },
    {
        "path": [
            "投资顾问费账户信息",
        ],
        "model": "partial_text",
        "near_regs": [
            r"投资顾问费",
        ],
    },
]


class CscPredictor(AIAnswerPredictor):
    """中信建投基金合同"""

    def __init__(self, *args, **kwargs):
        kwargs["predictors"] = predictors
        kwargs["default_model"] = "partial_text"
        super(CscPredictor, self).__init__(*args, **kwargs)
