"""
招商公募基金合同
"""

predictor_options = [
    {
        "path": ["产品名称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [r"(?P<dst>.*?投资基金)"],
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
            }
        ],
    },
    {
        "path": ["托管人"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": ["基金类别"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": True,
                "regs": [r"(?P<dst>.*?型.*?投资基金)"],
                "model_alternative": True,
            },
            {
                "name": "syllabus_elt_v2",
                "only_first": True,
            },
        ],
    },
    {
        "path": ["估值方法"],
        "models": [{"name": "syllabus_elt_v2"}],
    },
    {
        "path": ["费用计提方式、计提标准和支付方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "keep_parent": True,
            }
        ],
    },
    {
        "path": ["单位净值保留位数"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": ["标的指数"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [r"本基金股票资产的标的指数为(?P<dst>.*)[。\.]"],
                "model_alternative": True,
            }
        ],
    },
    {
        "path": ["业绩比较基准"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
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
                "name": "partial_text",
                "use_answer_pattern": True,
            },
            {
                "name": "syllabus_elt_v2",
                "only_first": True,
            },
        ],
    },
    {
        "path": ["管理费"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                # "multi_elements": True,
                "syllabus_regs": [r"管理费"],
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
                "bottom_anchor_regs": [r"管理费[每按]日计[算提]"],
            },
            {
                "name": "kmeans_classification",
                "syllabus_regs": [r"管理费"],
            },
        ],
    },
    {
        "path": ["管理费", "计提频率"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                # "multi": True,
                "syllabus_regs": [r"管理费"],
                "regs": [r"(?P<dst>每日计[提算])"],
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
                "regs": [r"(?P<dst>按月支付)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["管理费", "支付截止日"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"管理费"],
                "regs": [
                    r"(?P<dst>月初\d个工作日内)",
                    r"(?P<dst>次月首日起\d个工作日内)",
                    r"(?P<dst>次月首日起第?\d-\d个工作日内)",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["托管费"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                # "multi_elements": True,
                "syllabus_regs": [r"托管费"],
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
                "bottom_anchor_regs": [r"托管费[每按]日计[算提]"],
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
                "regs": [r"基金托管费年费率为(?P<dst>\d+\.\d+%)"],
                "model_alternative": True,
            }
        ],
    },
    {
        "path": ["托管费", "计提频率"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [r"(?P<dst>每日计[提算])"],
                "model_alternative": True,
                "syllabus_regs": [r"托管费"],
            }
        ],
    },
    {
        "path": ["托管费", "支付频率"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"托管费"],
                "regs": [r"(?P<dst>按月支付)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["托管费", "支付截止日"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"托管费"],
                "regs": [
                    r"(?P<dst>月初\d个工作日内)",
                    r"(?P<dst>次月首日起\d个工作日内)",
                    r"(?P<dst>次月首日起第?\d-\d个工作日内)",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["销售服务费"],
        "sub_primary_key": ["基金份额名称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "multi_elements": True,
                "syllabus_regs": [r"销售服务费"],
            },
        ],
    },
    {
        "path": ["销售服务费", "计费方式"],
        "sub_primary_key": ["基金份额名称"],
        "share_column": True,
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": False,
                "include_bottom_anchor": False,
                "top_anchor_regs": [r"销售服务费.*?计算(方法|方式|公式)"],
                "bottom_anchor_regs": [r"服务费[每按]日计[算提]"],
            },
            {
                "name": "kmeans_classification",
                "syllabus_regs": [r"销售服务费"],
            },
        ],
    },
    {
        "path": ["销售服务费", "计提频率"],
        "sub_primary_key": ["基金份额名称"],
        "share_column": True,
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"销售服务费"],
                "regs": [r"(?P<dst>每日计[提算])"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["销售服务费", "支付频率"],
        "sub_primary_key": ["基金份额名称"],
        "share_column": True,
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"销售服务费"],
                "regs": [r"(?P<dst>按月支付)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["销售服务费", "支付截止日"],
        "sub_primary_key": ["基金份额名称"],
        "share_column": True,
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "syllabus_regs": [r"销售服务费"],
                "regs": [
                    r"(?P<dst>月初\d个工作日内)",
                    r"(?P<dst>次月首日起\d个工作日内)",
                    r"(?P<dst>次月首日起第?\d-\d个工作日内)",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["基金收益分配原则"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
            {
                "name": "syllabus_elt_v2",
                "only_first": True,
            },
        ],
    },
    {
        "path": ["收益分配方式"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    r"本基金场外收益分配方式分两种：(?P<dst>现金分红与红利再投资)",
                ],
                "model_alternative": True,
            }
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
