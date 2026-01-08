"""银河证券 8 私募-运营操作备忘录"""

KEYWORD_AFTER_TABLE = r"深[圳证]通小站号?|业务数据专用电子邮箱|数据传输(同估值核算)?(接收)?邮箱|(中国银河证券)?(业务|结算)?数据(发送)?专用邮箱|估值核算"
JOB_BLACK_LIST = r"业务数据专用电子邮箱|数据(传输接收|发送专用)邮箱"


predictor_options = [
    {
        "path": ["基金名称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "model_alternative": False,
                "regs": [r".*?(私募)?证券投资基金"],
            }
        ],
    },
    {
        "path": ["基金管理人"],
        "models": [
            {
                "name": "middle_paras",
                "top_default": True,
                "bottom_default": True,
                "use_top_crude_neighbor": True,
                "top_anchor_regs": [r"甲方"],
                "bottom_anchor_regs": [r"乙方"],
            },
        ],
    },
    {
        "path": ["基金托管人"],
        "models": [
            {
                "name": "middle_paras",
                "top_default": True,
                "bottom_default": True,
                "use_top_crude_neighbor": True,
                "top_anchor_regs": [r"乙方"],
                "bottom_anchor_regs": [r"丙方"],
            },
        ],
    },
    {
        "path": ["证券经纪商"],
        "models": [
            {
                "name": "middle_paras",
                "top_default": True,
                "bottom_default": True,
                "use_top_crude_neighbor": True,
                "top_anchor_regs": [r"丙方"],
                "bottom_anchor_regs": [r"丁方"],
            },
        ],
    },
    {
        "path": ["基金服务机构"],
        "models": [
            {
                "name": "middle_paras",
                "top_default": True,
                "bottom_default": True,
                "use_top_crude_neighbor": True,
                "top_anchor_regs": [r"丁方.*?指为私募基金管理人提供.*?份额登记"],
                "bottom_anchor_regs": [r"释义"],
            },
        ],
    },
    {
        "path": ["证券经纪商开户网点"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"开户网点为?[:：]?.*"],
                "model_alternative": True,
            }
        ],
    },
    {
        "path": ["数据传输及核对"],
        "models": [
            {
                "name": "syllabus_elt",
                "keep_parent": True,
                "数据传输及核对": {
                    "feature_white_list": [
                        r"数据接收传输",
                        r"数据传输及核对",
                    ],
                },
            }
        ],
    },
    {
        "path": ["争议的处理"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>对于因本备忘录的订立、内容、履行和解释或与本备忘录有关的争议.*合法权益。)",
                ),
            }
        ],
    },
    {
        "path": ["基金管理人（甲方）授权业务联系人员及方式"],
        "sub_primary_key": ["岗位", "姓名"],
        "models": [
            {
                "name": "fund_people",
                "filter_single_data_row": False,
                "title_patterns": [r"甲方"],
                "岗位": {
                    "neglect_patterns": [rf"{JOB_BLACK_LIST}"],
                },
            }
        ],
    },
    {
        "path": ["表后信息-基金管理人（甲方）授权业务联系人员及方式"],
        "models": [
            {
                "name": "after_table_info",
                "title_patterns": [r"甲方"],
                "cell_text_patterns": {
                    "传真号": [
                        r"(?P<dst>传真号[:：])(深[圳证]通小站号?|\n)",
                        r"传真号[:：]?(?P<dst>[^:：]+)(深[圳证]通小站号?|\n)",
                        r"传真号[:：]?(?P<dst>[^:：]+)(深[圳证]通小站号?|\n)?",
                    ],
                    "深圳通小站号": [
                        rf"深[圳证]通小站号?[:：]?(?P<dst>[^:：]+?)({KEYWORD_AFTER_TABLE}|\n)",
                        rf"深[圳证]通小站号?[:：]?(?P<dst>[^:：]+?)({KEYWORD_AFTER_TABLE}|\n)?",
                    ],
                    "业务数据专用电子邮箱": [r"业务数据专用电子邮箱[:：]?(?P<dst>[^:：]+)"],
                },
            },
        ],
    },
    {
        "path": ["基金托管人（乙方）授权业务联系人员及方式"],
        "sub_primary_key": ["岗位", "姓名"],
        "models": [
            {
                "name": "fund_people",
                "filter_single_data_row": False,
                "title_patterns": [r"乙方"],
                "岗位": {
                    "neglect_patterns": [rf"{JOB_BLACK_LIST}"],
                },
            }
        ],
    },
    {
        "path": ["表后信息-基金托管人（乙方）授权业务联系人员及方式"],
        "models": [
            {
                "name": "after_table_info",
                "title_patterns": [r"乙方"],
                "cell_text_patterns": {
                    "深证通小站号": [rf"深[圳证]通小站号?[:：]?(?P<dst>.*?)({KEYWORD_AFTER_TABLE}|\n)"],
                    "数据传输接收邮箱": [r"数据传输(同估值核算)?(接收)?邮箱[:：]?(?P<dst>.*?(com|cn))"],
                },
            }
        ],
    },
    {
        "path": ["证券经纪商（丙方）授权业务联系人员及方式"],
        "sub_primary_key": ["岗位", "姓名"],
        "models": [
            {
                "name": "fund_people",
                "filter_single_data_row": False,
                "title_patterns": [r"丙方"],
                "岗位": {
                    "neglect_patterns": [rf"{JOB_BLACK_LIST}"],
                },
            }
        ],
    },
    {
        "path": ["表后信息-证券经纪商（丙方）授权业务联系人员及方式"],
        "models": [
            {
                "name": "after_table_info",
                "title_patterns": [r"丙方"],
                "cell_text_patterns": {
                    "传真号": [r"传真号[:：]?(?P<dst>.*)(深[圳证]通小站号?|\n)"],
                    "深证通小站号": [
                        rf"深[圳证]通小站号?[:：]?(?P<dst>([A-Z]\d+|[A-Z]+|无))({KEYWORD_AFTER_TABLE}|\n)"
                    ],
                    "数据专用邮箱": [r"(业务|结算)?数据(发送)?专用邮箱[:：]?(?P<dst>.*)"],
                },
            }
        ],
    },
    {
        "path": ["基金服务机构（丁方）授权业务联系人员及方式"],
        "sub_primary_key": ["岗位", "姓名"],
        "models": [
            {
                "name": "fund_people",
                "filter_single_data_row": False,
                "title_patterns": [r"丁方", "基金服务机构业务联系表"],
                "岗位": {
                    "neglect_patterns": [rf"{JOB_BLACK_LIST}"],
                },
            }
        ],
    },
    {
        "path": ["表后信息-基金服务机构（丁方）授权业务联系人员及方式"],
        "models": [
            {
                "name": "after_table_info",
                "title_patterns": [r"丁方", "基金服务机构业务联系表"],
                "cell_text_patterns": {
                    "深证通小站号": [rf"深[圳证]通小站号[:：]?(?P<dst>.*?)({KEYWORD_AFTER_TABLE}|\n)"],
                    "业务数据专用电子邮箱": [r"业务数据专用电子邮箱[:：]?(?P<dst>.*)"],
                },
            }
        ],
    },
]
prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
