"""
招商资管合同
"""

predictor_options = [
    {
        "path": ["产品名称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [r"(?P<dst>.*?(资产管理|资管)计划)"],
                "model_alternative": True,
            }
        ],
    },
    {
        "path": ["管理人"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["托管人"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["基金类别"],
        "models": [
            {
                "name": "syllabus_based",
                "paragraph_model": "para_match",
                "extract_from": "same_type_elements",
                "para_config": {
                    "paragraph_pattern": r"[√■◼☑➢✓](?P<content>.+)",
                },
            },
            {
                "name": "syllabus_elt_v2",
                "only_first": True,
            },
        ],
    },
    {
        "path": ["基金运作方式"],
        "models": [
            {
                "name": "syllabus_based",
                "paragraph_model": "para_match",
                "extract_from": "same_type_elements",
                "para_config": {
                    "paragraph_pattern": r"[√■◼☑➢✓](?P<content>(开放|封闭)式)",
                },
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["计划成立日"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [r"计划成立日.?(合同生效日)?[:：](?P<dst>.+)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["投资起始日"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["托管人结算模式", "直接说明"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"(?P<dst>托管人结算模式)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["托管人结算模式", "间接说明"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["券商结算模式"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["参与资金计算方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["退出资金计算方式"],
        "models": [
            {
                "name": "syllabus_based",
                "paragraph_model": "middle_paras",
                "extract_from": "same_type_elements",
                "include_title": True,
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": False,
                    "include_bottom_anchor": True,
                    "top_continue_greed": True,
                    "top_anchor_regs": [
                        r"计算(公式|方法)",
                    ],
                    "bottom_greed": True,
                    "bottom_continue_greed": True,
                    "bottom_anchor_regs": [
                        r"退出金额",
                    ],
                },
            },
            {
                "name": "syllabus_based",
                "paragraph_model": "para_match",
                "extract_from": "same_type_elements",
                "para_config": {
                    "paragraph_pattern": r"(采用“份额退出”方式，退出价格以.*元价格为基准进行计算。)",
                },
            },
        ],
    },
    {
        "path": ["估值时效"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>资产管理人.*资产管理计划财产进行估值(核对)?)",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["估值方法"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "include_title": True,
            },
        ],
    },
    {
        "path": ["单位净值保留位数"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"委托财产份额净值的计算(?P<dst>保留到小数点后\d位.小数点后第\d位四舍五入)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["万分收益尾数处理方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["7日年化收益率位数处理方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["费用计提方式、计提标准和支付方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "include_title": True,
            },
        ],
    },
    {
        "path": ["管理费", "计费方式"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": False,
                "include_bottom_anchor": False,
                "top_anchor_regs": [r"管理费.*?计算方法"],
                "bottom_anchor_regs": [r"管理费自.*起.?[每按]日计[算提]"],
            },
            {
                "name": "kmeans_classification",
                "syllabus_regs": [r"管理费"],
            },
        ],
    },
    {
        "path": ["管理费", "费率"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"管理费"],
                "regs": [r"管理费.*净值的.*?(?P<dst>[【】\d.%％]{2,})年费率"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["管理费", "计费起始日"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"管理费"],
                "regs": [r"管理费(?P<dst>自.*?日起)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["管理费", "计提频率"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"管理费"],
                "regs": [r"管理费自.*?起.?(?P<dst>每日计提)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["管理费", "支付频率"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"管理费"],
                "regs": [r"管理费自.*?起.*?(?P<dst>按.*?支付)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["管理费", "收费账户名"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"管理费"],
                "regs": [r"账户名称[:：](?P<dst>.+)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["管理费", "收费账号"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"管理费"],
            },
        ],
    },
    {
        "path": ["管理费", "收费开户行"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"管理费"],
            },
        ],
    },
    {
        "path": ["托管费", "计算方式"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": False,
                "include_bottom_anchor": False,
                "top_anchor_regs": [r"托管费.*?计算方法"],
                "bottom_anchor_regs": [r"托管费自.*起.?[每按]日计[算提]"],
            },
            {
                "name": "kmeans_classification",
                "syllabus_regs": [r"托管费"],
            },
        ],
    },
    {
        "path": ["托管费", "费率"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"托管费"],
                "regs": [r"托管费.*净值的.*?(?P<dst>[【】\d.%％]{2,})年费率"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["托管费", "计费起始日"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"托管费"],
                "regs": [r"托管费(?P<dst>自.*?日起)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["托管费", "计提频率"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"托管费"],
                "regs": [r"托管费自.*?起.?(?P<dst>每日计提)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["托管费", "支付频率"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"托管费"],
                "regs": [r"托管费自.*?起.*?(?P<dst>按.*?支付)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["托管费", "收费账户名"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"托管费"],
                "regs": [r"账户名称[:：](?P<dst>.+)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["托管费", "收费账号"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"托管费"],
            },
        ],
    },
    {
        "path": ["托管费", "收费开户行"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"托管费"],
            },
        ],
    },
    {
        "path": ["业绩报酬"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "include_title": True,
            },
        ],
    },
]


prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
