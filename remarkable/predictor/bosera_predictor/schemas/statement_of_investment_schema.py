"""
博时基金 投资说明书
"""

predictor_options = [
    {
        "path": ["投资范围"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"本计划投资范围包括",
                    r"投[资資]范围(及比例)?",
                    r"投资范围[:：]?$",
                    r"主要投资方向",
                ],
            },
            {
                "name": "partial_text",
                "regs": [
                    r"主要投资于.*?类资产",
                ],
            },
        ],
    },
    {
        "path": ["投资比例"],
        "sub_primary_key": [r"投资大类"],
        "models": [
            {
                "name": "investment_proportion",
                "syllabus_regs": [r"投[资資](范围及)?比例", r"资产配置比例", r"投[资資]范围"],
                "use_answer_pattern": False,
                "merge_char_result": False,
                "model_alternative": True,
                "multi_elements": True,
                "multi": True,
                "投资大类": {
                    "regs": [
                        r"(权益|股票|债券|现金|货币|固定收益|固收|商品|债权)类",
                        r"本产品的投资范围包括(?P<dst>.*等以及中国此监会允许投资的其他金融工具)",
                        r"现金.*?债券回购",
                    ],
                },
                "大类内容": {
                    "regs": [
                        r"资产的(投资)?比例不低于.*?总资产的?\d+[%％]",
                        r"资产的(投资)?比例.*?(总资产|资产总值)的?\d+[%％]?.\d+[%％]",
                        r"品种.?为本计划资产净值的?\d+[%％]?.\d+[%％]",
                        r"以上投资标的的投资范围为组合资产总值的?\d+[%％]?.\d+[%％]",
                    ],
                },
            },
        ],
    },
    {
        "path": ["投资限制"],
        "sub_primary_key": ["限制条数"],
        "models": [
            {
                "name": "syllabus_based",
                "include_title": False,
                "inject_syllabus_features": [r"__regex__^投资的?限制$"],
                "only_inject_features": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "neglect_regs": [r"以下限制"],
                    "paragraph_pattern": [r"(?P<dst>.*)"],
                },
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
