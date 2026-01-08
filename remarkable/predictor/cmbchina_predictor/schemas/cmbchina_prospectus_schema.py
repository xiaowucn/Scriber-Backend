"""
招募说明书
"""

from remarkable.predictor.cmbchina_predictor import R_DMSNYT
from remarkable.predictor.cmbchina_predictor.schemas import (
    R_AMOUNT,
    R_FIRST,
    R_FUND_SHORT_NAME,
    R_INTERVAL_END,
    R_INTERVAL_START,
    R_NON_PUNCTUATION,
    R_PLATFORM_KEYWORDS,
    R_SINGLE_REDEMPTION,
    gen_fund_name_regex,
    gen_platform_regex,
    get_predictor_options,
    p_holding_period,
    p_holding_period_unit,
)
from remarkable.predictor.common_pattern import R_CN, R_COMMA, R_CONJUNCTION, R_NOT_SENTENCE_END
from remarkable.predictor.eltype import ElementClass


def gen_table_subscription(keywords: str, splits: str = "[(（\n]"):
    return {
        "name": "table_subscription",
        "syllabus_regs": [
            r"基金份额的?(分[类级]|等级|类别)",
            r"基金分率及分类规则",
        ],
        "cell_regs": {
            "基金名称": [r"(?P<dst>[A-Z][类级].*)"],
            "最低限额": [
                rf"[:：为]?{R_AMOUNT}",
                r"(?P<dst>无|不设单笔最.*)",
                # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/9559?projectId=1&treeId=9&fileId=10&schemaId=2
                r"[:：](?P<dst>.*规定为准)",
            ],
            "销售平台": [rf"(?P<dst>.*{R_PLATFORM_KEYWORDS})"],
        },
        "main_column": "基金名称",
        "secondary_column": "销售平台",
        "header_patterns": {
            "基金名称": [r"^[A-Z][类级]"],
            "最低限额": [rf"{keywords}.*金额"],
            "销售平台": [rf"{keywords}"],
        },
        "splits": rf"{splits}",
    }


def gen_sales_service_fee_rate(
    syllabus_regs: list[str], neglect_syllabus_regs: list[str], neglect_patterns: list[str] = None
):
    return {
        "name": "subscription",
        "syllabus_regs": syllabus_regs,
        "neglect_syllabus_regs": neglect_syllabus_regs,
        "para_regs": [
            r"(?!.*(托管|管理)费)[A-Z](类|级).*([%％]|费率为[0零]|不收取(基金)?销售服务费)",
            r"(?!.*(托管|管理)费)([%％]|费率为[0零]|不收取(基金)?销售服务费).*[A-Z](类|级)",
            r"(销售服务费.*[\d.%％]+年费率)",
        ],
        "multi_config": {
            "基金名称": True,
            "销售服务费": False,
        },
        "regs": {
            "基金名称": [
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5308#note_578025
                # 不好排除按资产净值的句子，只提取A类，用分组排除
                r"(?P<dst>[A-Z][类级])",
            ],
            "销售服务费": [
                r"(?P<dst>([\d.]+[%％]?|不收取(基金)?销售服务费))",
                r"(?P<dst>([\d.]+[%％]?)年费率)",
            ],
        },
        "neglect_patterns": neglect_patterns,
        "splits": [r"[。,，;；]"],
    }


def gen_redemption_rate(mold_name: str, elements_nearby: dict, *args, **kwargs):
    # 赎回费率
    rate_config = {
        "name": mold_name,
        "multi_elements": True,
        "elements_nearby": elements_nearby,
        "distinguish_header": False,
        "lazy_match": True,
        "split_table": ["持有(基金)?(期|年限|时间)"],
        "filter_single_data_row": False,
        "feature_white_list": {
            "赎回区间": [
                r"__regex__持有(基金)?(期|年限|时间)",
            ],
            "区间起始值": [
                r"__regex__持有(基金)?(期|年限|时间)",
            ],
            "区间结束值": [
                r"__regex__持有(基金)?(期|年限|时间)",
            ],
            "赎回费": [
                r"__regex__赎回费率",
                r"__regex__[A-Z]类基金份额",
            ],
            "基金名称": [],
            "销售平台": [
                r"__regex__赎回费率场外",
            ],
            "销售对象": [],
            "购买金额": [
                r"__regex__持有(基金)?(期|年限|时间)",
            ],
        },
        "neglect_header_regs": [
            r"场内",
        ],
        "neglect_patterns": [
            # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/10701?projectId=36&treeId=59&fileId=904&schemaId=2
            r"(赎回|基金)(费率|[金份]额)(?!\d+\.\d+[%％])(?![(（]场外)",
            rf"(情形|费率|金额|持有(基金)?(期|年限|时间))(?!\d+[{R_DMSNYT}])(?![(（]计为[{R_DMSNYT}])(?!\d+\.\d+[%％])(?![(（]场外)",
        ],
        "cell_regs": {
            "区间起始值": R_INTERVAL_START,
            "区间结束值": R_INTERVAL_END,
            # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/11181?projectId=36&treeId=59&fileId=884&schemaId=2
            "购买金额": [rf"持有(基金)?(期|年限|时间).*?(计为)?(?P<dst>[{R_DMSNYT}])"],
            "赎回区间": [
                # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/10701?fileid=904&projectId=36&treeId=59&fileId=904&schemaId=2
                r"持有(基金)?时间(?P<dst>.*)",
                r"(?P<dst>.+)",
            ],
            "赎回费": [r"(?P<dst>\d+.\d+[%％])"],
        },
        "基金名称": {
            "from_title": [
                rf"(?P<dst>(([A-Z]类|[A-Z]类?)[{R_CONJUNCTION}]?){{1,2}})基金份额.?(具体)?赎回费率",
            ],
            "from_above_row": [
                rf"(?P<dst>(([A-Z]类|[A-Z]类?)[{R_CONJUNCTION}]?){{1,2}})基金份额",
            ],
        },
        "销售平台": {
            "from_title": gen_platform_regex("赎回"),
            "from_header": [r"(?P<dst>场外)"],
        },
        "销售对象": {
            "from_title": [
                r"(?P<dst>(上述|其他)投资(群体|者))",
            ],
        },
        "购买金额": {
            "from_header": [
                rf"[（(](计为)?(?P<dst>[{R_DMSNYT}])[)）]",
            ],
        },
    }
    if args or kwargs:
        rate_config.update(*args, **kwargs)
    return rate_config


def gen_subscription_rate(mold_name: str, *args, **kwargs):
    rate_config = {
        "name": mold_name,
        "syllabus_regs": [rf"((申购|赎回)[{R_CONJUNCTION}]?){{1,2}}", r"申购费率"],
        "multi_elements": True,
        "split_table": [r"^[A-Z](?P<dst>类基金份额)$"],
        "elements_nearby": {
            "regs": [
                "申购费率",
                "申购时收取申购费",
            ],
            "neglect_regs": [
                r"举例(说明|[一二三四五六七八九十])[:：]",
            ],
            # https://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/11184?fileid=881&projectId=36&treeId=59&fileId=881&schemaId=2
            "amount": 10,
            "step": -1,
        },
        "distinguish_header": False,
        "feature_white_list": {
            "申购区间": [
                r"__regex__申购[金份]额",
                r"__regex__金额[A-Z]",
            ],
            "购买金额": [
                r"__regex__申购[金份]额",
                r"__regex__金额[A-Z]",
            ],
            "区间起始值": [
                r"__regex__申购[金份]额",
                r"__regex__金额[A-Z]",
            ],
            "区间结束值": [
                r"__regex__申购[金份]额",
                r"__regex__金额[A-Z]",
            ],
            "申购费": [
                r"__regex__申购费率",
            ],
            "基金名称": [],
            "销售平台": [
                r"__regex__申购费率",
            ],
            "销售对象": [],
        },
        "neglect_patterns": [
            r"(申购|基金)(费率|[金份]额)",
            r"情形|费率|金额",
        ],
        "cell_regs": {
            "区间起始值": R_INTERVAL_START,
            "区间结束值": R_INTERVAL_END,
        },
        "基金名称": {
            "from_title": [
                rf"(?P<dst>(([A-Z]类|[A-Z]类?)[{R_CONJUNCTION}]?){{1,2}})基金份额.?(具体)?申购费率",
                rf"申购本?基金(?P<dst>(([A-Z]类|[A-Z]类?)[{R_CONJUNCTION}]?){{1,2}})",
            ],
            "from_above_row": [
                rf"(?P<dst>(([A-Z]类|[A-Z]类?)[{R_CONJUNCTION}]?){{1,2}})(基金)?份额",
            ],
        },
        "销售平台": {
            "from_title": gen_platform_regex("申购"),
            # https://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/11184?fileid=881&projectId=36&treeId=59&fileId=881&schemaId=2
            "from_header": [
                r"申购费率[（(]通过(?P<dst>.*)申购",
            ],
        },
        "销售对象": {
            "from_above_row": [
                r"申购费率[（(]通过.*申购的?(?P<dst>.*)[)）]",
                r"申购费率[（(](?P<dst>其他投资[人者])[)）]",
            ],
            "from_title": [
                r"(?P<dst>(上述|其他|特定)投资(群体|者(群体)?))",
                r"(?P<dst>非?养老金客户)",
                r"(?P<dst>^投资[人者])申购本基金",
                r"(?P<dst>其他投资[人者])的申购费率",
            ],
        },
        "购买金额": {
            "from_header": [
                # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/11177?projectId=36&treeId=59&fileId=901&schemaId=2
                rf"[（(](?P<dst>[{R_DMSNYT}]([{R_COMMA}]含申购费)?)[)）]",
                rf"申购金额(?P<dst>[{R_DMSNYT}])[（(]",
            ],
        },
    }
    if args or kwargs:
        rate_config.update(*args, **kwargs)
    return rate_config


FIRST_SUBSCRIPTION_ZERO_NORM = (
    rf"[A-Z]类和[A-Z]类{R_NOT_SENTENCE_END}*首次申购{R_NOT_SENTENCE_END}*[均同]为{R_AMOUNT}",
)

predictor_options = [
    {
        "path": ["基金名称"],
        "models": [
            {
                "name": "middle_paras",
                "elements_in_page_range": [0],
                "top_default": True,
                "bottom_anchor_regs": [r"招募说明书$"],
                "ignore_pattern": [r"^招募说明书"],
                "top_anchor_content_regs": [
                    r"基金管理有限公司(?P<content>.*)",
                    r"(?P<content>.*)",
                ],
                "bottom_anchor_content_regs": [
                    r"(?P<content>.*基金([(（][a-zA-Z]+[）)])?)(?!管理)",
                    r"(?P<content>.*)招募说明书",
                ],
                "include_bottom_anchor": True,
            },
            {
                "name": "fixed_position",
                "target_element": [ElementClass.PARAGRAPH.value],
                "pages": [0],
                "regs": [
                    r"(?P<dst>.*基金([(（][a-zA-Z\-—一]+[）)])?)(?!管理)",
                    r"(?P<dst>.*)招募说明书",
                ],
            },
        ],
    },
    {
        "path": ["基金代码"],
        "models": [
            {
                "name": "partial_text",
            },
            {
                "name": "table_kv",
                "feature_white_list": [
                    r"__regex__基金代码",
                ],
                "only_matched_value": True,
                "regs": [
                    r"(?P<dst>\d{6})",
                ],
            },
        ],
    },
    {
        "path": ["是否升降级"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__份额分[类级]规则|自动升降级"],
                "only_inject_features": True,
                "break_para_pattern": [
                    r"累计收益",
                ],
            },
            {
                "name": "para_match",
                "syllabus_regs": [
                    r"分类规则|份额的?(分[类级]|类别)",
                    r"基金份额的?[升降]+级",
                ],
                "paragraph_pattern": [r"[升降]+级(?!$)"],
                "neglect_regs": [
                    r"调整基金份额[升降]+级",
                    r"基金份额的?((升级|降级)[和]?){2}$",
                ],
                "multi_elements": True,
                "order_by_index": True,
            },
            {
                "name": "para_match",
                "syllabus_regs": [r"释义$"],
                "paragraph_pattern": [r"[升降]+级(?!$)"],
                "neglect_regs": [
                    r"调整基金份额[升降]+级",
                ],
                "multi_elements": True,
                "order_by_index": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": [r"[升降]+级(?!$)"],
                "neglect_regs": [
                    r"调整基金份额[升降]+级",
                ],
            },
        ],
    },
    {
        "path": ["赎回限制类型"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r".*每个运作期到期日.*",
                    r".*最短持有期.*",
                    r".*第一个运作期.*第二个运作期.*",
                    r".*锁定(持有)?期.*",
                ],
            },
        ],
    },
    {
        "path": ["赎回限制"],
        "models": [
            {
                "name": "reference",
                "from_path": ["赎回限制类型"],
            },
        ],
    },
    {
        "path": ["产品销售对象"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__基金的募集__regex__(销售|发售|募集)对象",
                    r"__regex__基金份额的申购.赎回__regex__(销售|发售|募集)对象",
                    r"__regex__基金份额的申购.赎回__regex__(基金投资者.范围|申购和赎回.*限制)",
                ],
                "only_inject_features": True,
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        r"([，。\s]+?|^)(?P<dst>(本基金)?募集对象.*)",
                        r"(^|本基金的)募集对象.*投资.",
                        r"^符合法律.*投资.",
                        r"(^|[1-9、])本基金暂不向.*",
                        r"^个人.*投资者",
                        r"^本基金仅.*(销售|调整)",
                        r"(依据)?中华人民共和国.*投资.",
                    ],
                    "multi_elements": True,
                },
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__基金的募集",
                ],
                "only_inject_features": True,
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        r"([，。\s]+?|^)(?P<dst>(本基金)?募集对象.*)",
                        r"(^|本基金的)募集对象.*投资.",
                        r"^符合法律.*投资.",
                        r"(^|[1-9、])本基金暂不向.*",
                        r"^个人.*投资者",
                        r"^本基金仅.*(销售|调整)",
                        r"(依据)?中华人民共和国.*投资.",
                    ],
                    "multi_elements": True,
                },
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__重要提示",
                ],
                "only_inject_features": True,
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        r"^本基金仅.*(销售|调整)",
                        r"(^|[1-9、])本基金暂不向.*",
                    ],
                },
            },
            {
                "name": "partial_text",
                # "page_range": [0],
                "model_alternative": True,
                "need_match_length": False,
                "regs": [
                    r"本基金.*公开销售",
                    r"符合法律.*他投资.",
                ],
            },
        ],
    },
    {
        "path": ["管理费率"],
        "sub_primary_key": ["基金名称", "管理费"],
        "divide_answers": True,
        "models": [
            {
                "name": "subscription",
                "para_regs": [
                    r"管理费年费率.*[A-Z][类级]基金份额",
                ],
                "multi_config": {
                    "基金名称": True,
                    "管理费": False,
                },
                "regs": {
                    "基金名称": [r"(?P<dst>[A-Z][类级]基金份额)"],
                    "管理费": [
                        r"管理费年费率均?为(?P<dst>[\d\.]+[%％])",
                    ],
                },
                "neglect_patterns": [
                    r"固定管理费",
                ],
                "splits": ["$"],
            },
            {
                "name": "subscription",
                "para_regs": [
                    r"管理费.*[A-Z][类级]基金份额",
                    r"管理费按.*费率计[提算]",
                    r"年?管理费年?费?率为",
                    r"取0[）)].*[.0-9%％]+.年费率计提",
                ],
                "multi_config": {
                    "基金名称": True,
                    "管理费": False,
                },
                "regs": {
                    "基金名称": [r"(本基金)?(?P<dst>[A-Z][类级]基金份额)"],
                    "管理费": [
                        r"管理费[^，,。]*?(?P<dst>[\d\.]+[%％])",
                        r"(?P<dst>[\d.]+[%％]).?年费率",
                    ],
                },
                "skip_syllabus": True,
                "neglect_patterns": [
                    r"设置不同的管理费费率",
                ],
                "splits": [
                    "[。；;,，](?![^(（]*[)）])",
                ],
            },
            {
                "name": "table_subscription",
                "syllabus_regs": [
                    r"基金份额的?(分[类级]|等级|申购|赎回)",
                ],
                "cell_regs": {
                    "基金名称": [r"(?P<dst>[A-Z][类级].*)"],
                    "管理费": [r"(?P<dst>[\d\.]+[%％]?)"],
                },
                "main_column": "基金名称",
                "secondary_column": "管理费",
                "header_patterns": {
                    "基金名称": [r"[A-Z][类级]"],
                    "管理费": [r"管理费"],
                },
            },
            {
                "name": "table_row",
                "syllabus_regs": [
                    r"基金份额的分类",
                ],
                "parse_by": "col",
                "title_patterns": [
                    r"申[)）]?购",
                ],
                "feature_black_list": {
                    "基金名称": [r"__regex__.*"],
                    "管理费": [r"__regex__.*"],
                },
                "feature_white_list": {
                    "基金名称": [
                        r"__regex__份额类别",
                        r"",
                    ],
                    "管理费": [r"__regex__管理费"],
                },
            },
        ],
    },
    {
        "path": ["销售服务费率"],
        "sub_primary_key": ["基金名称", "销售服务费"],
        "primary_key_unit": ["[%％]"],
        "pick_answer_strategy": "all",
        "models": [
            gen_sales_service_fee_rate(
                [
                    r"基金份额的(分类|等级|申购|赎回)",
                    rf"基金的?(?:(?:费用|税收)[{R_CONJUNCTION}]?){{2}}",
                    r"销售.?服务费",
                ],
                [
                    r"申购费",
                ],
            ),
            {
                "name": "table_subscription",
                "syllabus_regs": [
                    r"基金份额的?(分[类级]|等级|申购|赎回)",
                ],
                "cell_regs": {
                    "基金名称": [r"(?P<dst>[A-Z][类级].*)"],
                    "销售服务费": [r"(?P<dst>[\d\.]+[%％]?)"],
                },
                "main_column": "基金名称",
                "secondary_column": "销售服务费",
                "header_patterns": {
                    "基金名称": [r"[A-Z][类级]"],
                    "销售服务费": [r"销售.?服务费"],
                },
            },
        ],
    },
    {
        "path": ["首次认购下限-原文"],
        "models": [
            {
                "name": "para_match",
                "syllabus_regs": [
                    r"基金的?募集",
                ],
                "combine_paragraphs": True,
                "multi_elements": True,
                "order_by_index": True,
                "paragraph_pattern": [
                    rf"(起点|首[次笔])(最低)?认购[^,.。；;]*?{R_AMOUNT}",
                    rf"单笔最.认购金额为?{R_AMOUNT}",
                ],
            },
            {
                "name": "para_match",
                "combine_paragraphs": True,
                "multi_elements": True,
                "order_by_index": True,
                "neglect_syllabus_regs": [
                    r"申购金额的限制",
                ],
                "paragraph_pattern": [
                    rf"(起点|首[次笔])(最低)?认购[^,.。；;]*?{R_AMOUNT}",
                    rf"单笔最.认购金额为?{R_AMOUNT}",
                ],
            },
        ],
    },
    {
        "path": ["首次认购下限"],
        "sub_primary_key": ["基金名称", "最低限额", "销售平台"],
        "strict_group": True,
        "models": [
            {
                "name": "subscription",
                "main_column": "销售平台",
                "depends": ["首次认购下限-原文"],
                "multi_config": {
                    "基金名称": True,
                    "最低限额": False,
                    "销售平台": False,
                },
                "para_regs": [
                    rf"(起点|首[次笔])[^,.。；;]*?{R_AMOUNT}",
                    rf"单笔最.(认购)?金额为?{R_AMOUNT}",
                ],
                "regs": {
                    "基金名称": gen_fund_name_regex("首[次笔]认购"),
                    "最低限额": [
                        rf"(起点|首[次笔])[^,.。；;]*?{R_AMOUNT}",
                        rf"(?<!单笔)最.(认购)?金额为?{R_AMOUNT}",
                    ],
                    "销售平台": [
                        *gen_platform_regex("(认购(?!金额)|首次)"),
                        rf"管理人(本基金)?(?P<dst>[^。;；,，]*{R_PLATFORM_KEYWORDS})",
                    ],
                },
                "neglect_answer_patterns": {
                    "销售平台": [
                        r"可以?多次",
                    ]
                },
            },
            gen_table_subscription("首[次笔].*认.*购", splits="[(（]"),
        ],
    },
    {
        "path": ["追加认购最低金额-原文"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [r"追加认购"],
                "combine_paragraphs": True,
                "multi_elements": True,
                "order_by_index": True,
            },
        ],
    },
    {
        "path": ["追加认购最低金额"],
        "sub_primary_key": ["基金名称", "最低限额", "销售平台"],
        "pick_answer_strategy": "all",
        "models": [
            {
                "name": "subscription",
                "main_column": "销售平台",
                "depends": ["追加认购最低金额-原文"],
                "multi_config": {
                    "基金名称": True,
                    "最低限额": True,
                    "销售平台": False,
                },
                "regs": {
                    "基金名称": gen_fund_name_regex("认购"),
                    "最低限额": [
                        rf"追加[^,.，。；;]*?{R_AMOUNT}",
                        r"追加认购(?P<dst>不受首次[^,.，。；;]*?限制)",
                    ],
                    "销售平台": [
                        *gen_platform_regex("(认购(?!金额)|首次)"),
                        rf"管理人(本基金)?(?P<dst>[^。;；,，]*{R_PLATFORM_KEYWORDS})",
                    ],
                },
                "para_regs": [
                    rf"追加[^,.，。；;]*?{R_AMOUNT}",
                    r"追加认购不受首次[^,.，。；;]*?限制",
                ],
                "splits": [
                    r"[。；;](?![）)])",
                ],
            },
            gen_table_subscription("追加.*认.*购", splits="[(（]"),
        ],
    },
    {
        "path": ["单笔申购下限-原文"],
        "models": [
            {
                "name": "para_match",
                "syllabus_regs": [
                    r"[金数][额量]的?限制",
                    r"(申购|赎回)(份额)?的限制",
                    r"申请申购基金的?金额",
                ],
                "multi_elements": True,
                "order_by_index": True,
                "combine_paragraphs": True,
                "neglect_syllabus_regs": [r"单笔申购(?!限制)", r"场内申购和赎回"],
                "paragraph_pattern": [
                    rf"((单|每)[次笔]|首笔)(首次)?(最.)?申购(?!各类){R_NOT_SENTENCE_END}*?{R_AMOUNT}",
                    rf"申购[^。，,]*?((单|每)[次笔]|首笔){R_NOT_SENTENCE_END}*?{R_AMOUNT}",
                    rf"首次申购或追加申购各类基金份额时[{R_COMMA}]单笔最低金额为",
                    r"首次申购和追加申购的最低金额均为",
                    r"份额(?P<dst>(无|不设)单笔最低限额)",
                    rf"申购(金额)?(下限|最低金额)(均|分别)?为{R_AMOUNT}",
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5311#note_585216
                    # 首次申购的描述中部分包含单笔最低限额的情况
                    rf"首次申购(本?基金?)?{R_FUND_SHORT_NAME}的?单笔最.[限金]额",
                ],
            },
        ],
    },
    {
        "path": ["单笔申购下限"],
        "sub_primary_key": ["基金名称", "最低限额", "销售平台"],
        "strict_group": True,
        "pick_answer_strategy": "all",
        "post_process": "post_process_sale_platform",
        "models": [
            {
                "name": "subscription",
                "main_column": "销售平台",
                "depends": ["单笔申购下限-原文"],
                "multi_config": {
                    "基金名称": True,
                    "最低限额": True,
                    "销售平台": False,
                },
                "para_regs": [
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5311#note_584711
                    # 如果描述的是首笔（不能是首次）申购的时候可以同时框选到单笔申购和首次申购，
                    rf"((单|每)[次笔]|首笔)(首次)?(最.)?(申购(?!各类)[^,.，。；;]*?(人民币)?|金额为?){R_AMOUNT}",
                    rf"申购[^。，,]*?((单|每)[次笔]|首笔)[^,.，。；;]*?{R_AMOUNT}",
                    rf"(?<!首次)申购(金额)?(下限|最低金额)(均|分别)?为{R_AMOUNT}",
                    r"首次申购或追加申购各类基金份额时[,，]单笔最低金额为",
                    r"首次申购和追加申购的最低金额均为",
                    r"份额(无|不设)单笔最低限额",
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5311#note_585216
                    # 首次申购的描述中部分包含单笔最低限额的情况
                    rf"首次申购(本?基金?)?{R_FUND_SHORT_NAME}([{R_CONJUNCTION}]{R_FUND_SHORT_NAME})?的单笔最.限额",
                    rf"{R_FUND_SHORT_NAME}[\w\s]*首次申购的?单笔最.限额",
                    r"通过本基金.*申购.*((单|每)[次笔]|首笔)申购",
                ],
                "regs": {
                    "基金名称": [
                        rf"(((单|每)[次笔]|首笔)申购|[{R_CONJUNCTION}]|基金){R_NON_PUNCTUATION}*?(?<!首次申购)(?P<dst>{R_FUND_SHORT_NAME})[{R_CONJUNCTION}][A-Z][类级]",
                        rf"(((单|每)[次笔]|首笔)申购|[{R_CONJUNCTION}]|基金){R_NON_PUNCTUATION}*?(?<!首次申购)(?P<dst>{R_FUND_SHORT_NAME})",
                        rf"(((单|每)[次笔]|首笔)申购|[{R_CONJUNCTION}]|基金){R_NON_PUNCTUATION}*?(?P<dst>[^,.，。；;申购]*?货币[A-Z])",
                        rf"(?<!持有本基金)(?P<dst>{R_FUND_SHORT_NAME})([\/、和或与]{R_FUND_SHORT_NAME})?{R_NON_PUNCTUATION}*?((单|每)[次笔]|首笔)申购",
                        r"通过[^;；。]*?(?P<dst>[A-Z][类级]((基金)?份额)?)[^;；。]*?((单|每)[次笔]|首笔)申购",
                        rf"^(?P<dst>{R_FUND_SHORT_NAME})首次最低金额及追加申购最低金额",
                        # *gen_fund_name_regex("((单|每)[次笔]|首笔)申购"),
                        rf"首次申购(本?基金?)?{R_NON_PUNCTUATION}*?(?P<dst>{R_FUND_SHORT_NAME})的?单笔最.[限金]额",
                        rf"首次申购(本?基金?)?(?P<dst>{R_FUND_SHORT_NAME})[{R_CONJUNCTION}]{R_FUND_SHORT_NAME}的?单笔最.[限金]额",
                        rf"已持有本基金(?P<dst>{R_FUND_SHORT_NAME})[\w\s]*首次申购的?单笔最.[限金]额",
                        # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/11197?projectId=36&treeId=59&fileId=877&schemaId=2
                        rf"申购(?P<dst>{R_FUND_SHORT_NAME}).*?单笔最低申购金额.*元",  # fid 877
                    ],
                    "最低限额": [
                        rf"(追加申购[{R_CN}]{{,2}})((单|每)[次笔]|首笔)(首次)?(最.)?(申购(?!各类)[^,.，。；;]*?(人民币)?|金额为?){R_AMOUNT}",
                        rf"追加申购[^。，,]*?((单|每)[次笔]|首笔)[^,.，。；;]*?{R_AMOUNT}",
                        rf"追加申购的?((金额)?下限|最低金额)均?为{R_AMOUNT}",
                        rf"首次申购或追加申购各类基金份额时[,，]单笔最低金额为{R_AMOUNT}",
                        rf"首次最低金额及追加申购最低金额分别为.*?和{R_AMOUNT}",
                        # 优先提取追加申购的
                        rf"(?<!追加申购)(?<!追加申购[^,，].)(?<!追加申购的)((单|每)[次笔]|首笔)(首次)?(最.)?(申购(?!各类)[^,.，。；;]*?(人民币)?|金额为?){R_AMOUNT}",
                        rf"(?<!追加)申购[^。，,]*?((单|每)[次笔]|首笔)[^,.，。；;]*?{R_AMOUNT}",
                        rf"(?<!追加|首次)申购(金额)?下限为{R_AMOUNT}",
                        r"份额(?P<dst>(无|不设|不对)单笔最低(申购)?(限额|进行限制))",
                        rf"首次申购(本?基金?)?{R_NON_PUNCTUATION}*?{R_FUND_SHORT_NAME}的单笔最.限额为?{R_AMOUNT}",
                        rf"{R_FUND_SHORT_NAME}[\w\s]*首次申购的?单笔最.限额{R_AMOUNT}",
                    ],
                    "销售平台": gen_platform_regex("(((单|每)[次笔]|首笔)?申购|每个账户)"),
                },
                "splits": [
                    r"[。；;](?![）)])|[(（]但已持有",
                ],
                # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/11197?projectId=36&treeId=59&fileId=868&schemaId=2
                "neglect_patterns": [r"(?<!1元[,，\s])如果销售机构"],  # fid 868 882
                "need_distinct": True,
            },
            gen_table_subscription("((单|每)[次笔]|首笔)(?!赎回).*申.*购"),
        ],
    },
    {
        "path": ["单客户每日累计申购、转入限额"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r".*单(一投资[者人]|客户).*单日(累计)?申购.*",
                ],
            },
        ],
    },
    {
        "path": ["首次申购下限-原文"],
        "models": [
            {
                "name": "para_match",
                "combine_paragraphs": True,
                "multi_elements": True,
                "order_by_index": True,
                "syllabus_regs": [
                    rf"(?:(?:申购|赎回)[{R_CONJUNCTION}]?){{2}}(与转换)?的?数[量额]限制",
                    r"份额的金额限制",
                ],
                "paragraph_pattern": [
                    rf"{R_FIRST}(最.)?申购.*{R_AMOUNT}",
                    r"(?<!追加申购)(?<!追加)[单每]笔最低(申购)?金额",
                ],
            },
            {
                "name": "para_match",
                "combine_paragraphs": True,
                "multi_elements": True,
                "order_by_index": True,
                "syllabus_regs": [r"收益分配风险"],
                "paragraph_pattern": [
                    rf"{R_FIRST}(最.)?申购.*{R_AMOUNT}",
                ],
            },
            {
                "name": "para_match",
                "combine_paragraphs": True,
                "multi_elements": True,
                "order_by_index": True,
                "paragraph_pattern": [
                    rf"{R_FIRST}(最.)?申购.*{R_AMOUNT}",
                ],
            },
        ],
    },
    {
        "path": ["首次申购下限"],
        "sub_primary_key": ["基金名称", "最低限额", "销售平台"],
        "strict_group": True,
        "post_process": "post_process_sale_platform",
        "pick_answer_strategy": "all",
        "models": [
            {
                "name": "subscription",
                "main_column": "销售平台",
                "depends": ["首次申购下限-原文"],
                "multi_config": {
                    "基金名称": True,
                    "最低限额": True,
                    "销售平台": False,
                },
                # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/11382?projectId=60&treeId=89&fileId=1513&schemaId=2
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/6738
                "duplication": {
                    "基金名称": [],
                    "最低限额": [FIRST_SUBSCRIPTION_ZERO_NORM],
                    "销售平台": [],
                },
                "regs": {
                    "基金名称": [
                        *gen_fund_name_regex(rf"({R_FIRST}|投资人)申购", "追加[申认]购[A-Z]类"),
                        rf"^(?P<dst>{R_FUND_SHORT_NAME})首次最低金额及追加申购最低金额",
                    ],
                    "最低限额": [
                        FIRST_SUBSCRIPTION_ZERO_NORM,
                        rf"(?<!追加申购)(?<!追加){R_FIRST}(?!追加){R_NOT_SENTENCE_END}*?{R_AMOUNT}",
                        rf"{R_FIRST}申购或追加申购各类基金份额时[{R_COMMA}]单笔最低金额为{R_AMOUNT}",
                        rf"(?<!追加申购)(?<!追加)[单每]笔(申购)?最低(申购)?金额(（含申购费）)?为{R_AMOUNT}",
                        r"(?P<dst>无单笔最低限额)",
                    ],
                    "销售平台": gen_platform_regex(rf"({R_FIRST}?申购|每个账户)"),
                },
                "para_regs": [
                    rf"(申购{R_NOT_SENTENCE_END}*?{R_FIRST}(?!追加)|{R_FIRST}(?!追加){R_NOT_SENTENCE_END}*?申购){R_NOT_SENTENCE_END}*?{R_AMOUNT}",
                    rf"{R_FIRST}申购或追加申购各类基金份额时[{R_COMMA}]单笔最低金额为",
                    r"(?<!追加申购)(?<!追加)[单每]笔(申购)?最低(申购)?金额",
                ],
                "splits": [
                    r"[。；;](?![）)])",
                ],
            },
            gen_table_subscription(rf"{R_FIRST}.*申.*购"),
        ],
    },
    {
        "path": ["追加申购下限-原文"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"追加申购.*?元",
                ],
                "multi_elements": True,
                "order_by_index": True,
                "combine_paragraphs": True,
                # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/9305?projectId=1&treeId=9&fileId=37&schemaId=2
                "neglect_regs": [r"本基金场外.*追加申购的最低金额均为.*?元"],  # fid:37
            },
        ],
    },
    {
        "path": ["追加申购下限"],
        "sub_primary_key": ["基金名称", "最低限额", "销售平台"],
        "strict_group": True,
        "pick_answer_strategy": "all",
        "models": [
            {
                "name": "subscription",
                "main_column": "销售平台",
                "depends": ["追加申购下限-原文"],
                "multi_config": {
                    "基金名称": True,
                    "最低限额": True,
                    "销售平台": False,
                },
                "para_regs": [
                    rf"追加[^,.，。；;]*?({R_AMOUNT}|无单笔最低限额)",
                    r"追加申购(单笔)?金额不设?限",
                    r"通过.*?网上交易系统等特定交易方式申购.*?不受此限制",
                ],
                "bracket_content_regs": [r"通过.*?网上交易系统等特定交易方式申购.*?不受此限制"],
                "regs": {
                    "基金名称": [
                        rf"(申购|[、和或与]|(?<!持有本)基金){R_NON_PUNCTUATION}*?(?P<dst>[A-Z][类级]((基金)?份额)?)或[A-Z][类级]",
                        rf"(申购|[、和或与]|(?<!持有本)基金){R_NON_PUNCTUATION}*?(?P<dst>[A-Z][类级]((基金)?份额)?)",
                        rf"(申购|[、和或与]|(?<!持有本)基金){R_NON_PUNCTUATION}*?(?P<dst>[^,.，。；;申购]*?货币[A-Z])",
                        rf"(?<!持有本基金)(?P<dst>{R_FUND_SHORT_NAME})([\/、和或与]{R_FUND_SHORT_NAME})?{R_NON_PUNCTUATION}*?申购",
                        r"通过[^;；。]*?(?P<dst>[A-Z][类级]((基金)?份额)?)[^;；。]*?申购",
                    ],
                    "最低限额": [
                        rf"追加[^,.，。；;]*?{R_AMOUNT}",
                        r"追加申购(单笔)?(?P<dst>金额不设?限)",
                        r"(?P<dst>无单笔最低限额)",
                        r"通过.*?网上交易系统等特定交易方式申购本基金(?P<dst>暂不受此限制)",
                    ],
                    "销售平台": gen_platform_regex("(认购(?!金额)|首次|申购)"),
                },
                "neglect_answer_patterns": {
                    "销售平台": [
                        r"转入",
                    ]
                },
                "splits": [
                    r"[。；;](?![）)])",
                ],
            },
            gen_table_subscription("追加.*申.*购"),
        ],
    },
    {
        "path": ["单客户持仓上限"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>.*单(个|一)投资[人者](累计)?持有(的?基金)?份额.*)。.*?(法律|法规)",
                    r"(?P<dst>.*单(个|一)投资[人者]单日申购金额上限.*)。.*?(法律|法规)",
                    r"(?P<dst>.*单(个|一)投资[人者](不设|在认购期间)?累计持有(的基金)?份额(上限|不得超过).*)",
                    r"(?P<dst>.*单(个|一)投资[人者]单日申购金额上限.*)",
                    r"(?P<dst>.*单(个|一)投资[人者](累计)?持有(的?基金)?份额.*)",
                ],
                "neglect_answer_patterns": [
                    r"(累计|单日).购",
                ],
            },
        ],
    },
    {
        "path": ["单客户持有上限单位"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["是否共用限额"],
        "models": [
            {
                "name": "para_match",
                "neglect_regs": [r"费率"],
            },
        ],
    },
    {
        "path": ["限额控制模式"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["费率生效日期"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["分级基金"],
        "sub_primary_key": ["基金简称"],
        "models": [
            {
                "name": "subscription",
                "para_regs": [
                    r"[A-Z].*\d{6}",
                    r"\d{6}.*[A-Z]",
                    r"现有[A-Z][^，,。；;]*基础上",
                ],
                "multi_config": {
                    "基金简称": True,
                    "基金代码": True,
                },
                "regs": {
                    "基金简称": [
                        r"(?<!降.|调整)(?P<dst>[A-Z][类级])",
                        r"\d+[)）](?P<dst>.*[A-Z])",
                    ],
                    "基金代码": [
                        r"代码[:：为]?(?P<dst>\d{6})",
                        r"新增(?P<dst>\d{6})",
                    ],
                },
                "splits": [r"(。|[,，]增设)"],
                "neglect_patterns": [r"^报告期内基金投资的前十名"],
            },
        ],
    },
    {
        "path": ["产品户类型"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"(基金)?募集对象为(?P<dst>.*)",
                    r".*暂不向金融机构自营账户销售.*",
                    r"^个人.*?投资",
                    r"仅(面)?向个人投资者.*",
                    r"符合法律法规规定的.*?投资(人|者).*",
                    r"中华人民共和国境内.*?投资(人|者).*",
                ],
            }
        ],
    },
    {
        "path": ["产品持有期"],
        "models": [
            {
                "name": "fixed_position",
                "target_element": [ElementClass.PARAGRAPH.value],
                "pages": [0],
                "neglect_patterns": [
                    r"\d{2,4}年\d{1,2}月\d{1,2}日",
                ],
                "regs": p_holding_period,
            }
        ],
    },
    {
        "path": ["产品持有期单位"],
        "models": [
            {
                "name": "fixed_position",
                "target_element": [ElementClass.PARAGRAPH.value],
                "pages": [0],
                "neglect_patterns": [
                    r"\d{2,4}年\d{1,2}月\d{1,2}日",
                ],
                "regs": p_holding_period_unit,
            }
        ],
    },
    {
        "path": ["管理费率优惠开始日期"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["管理费率优惠结束日期"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["销售服务费率优惠开始日期"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["销售服务费率优惠结束日期"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["单笔赎回下限-原文"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__申请赎回(与转换)?基金的?份额",
                    r"__regex__赎回(份额)?的?限制",
                    r"__regex__赎回(份额)?的?数[额量]限制",
                ],
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [
                        r"单笔赎回份额不限",
                        r"不对单笔最低赎回(及最低持有)?份额进行限制",
                        r"本基金不设单笔(最低赎回份额|赎回份额下限)",
                        r"最小申购、赎回单位",
                        rf"{R_SINGLE_REDEMPTION}(各类)?(基金)?(申请)?的?(或转换)?份?(额|数)?(单笔)?均?(最低[份限][额数]|不得?[少低]于)",
                    ],
                    "neglect_regs": [
                        r"单笔赎回的最低份额数量请见基金管理人相关公告",
                        r"本基金的最小申购、赎回单位请参考届时发布的申购、赎回相关公告以及申购赎回清单",
                    ],
                },
            },
        ],
    },
    {
        "path": ["单笔赎回下限"],
        "sub_primary_key": ["基金名称", "最低限额", "销售平台"],
        "pick_answer_strategy": "all",
        "strict_group": True,
        "models": [
            {
                "name": "subscription",
                "main_column": "销售平台",
                "depends": ["单笔赎回下限-原文"],
                "multi_config": {
                    "基金名称": True,
                    "最低限额": True,
                    "销售平台": False,
                },
                "para_regs": [
                    rf"{R_FUND_SHORT_NAME}[\w\s]*单笔最低赎回",
                    rf"{R_SINGLE_REDEMPTION}(各类)?(基金)?(的|申请)?(或转换)?份?(额|数)?(单笔)?(最低[份限][额数]|不得[少低]于)",
                    rf"(?<!追加赎回)((单|每)[次笔]|首笔)(最.)?(赎回(?!各类)[^,.，。；;]*?(人民币)?|金额为?){R_AMOUNT}",
                    rf"(?<!追加)赎回[^。，,]*?((单|每)[次笔]|首笔)[^,.，。；;]*?{R_AMOUNT}",
                    rf"(?<!追加|首次)赎回(金额)?下限为{R_AMOUNT}",
                    r"份额(?P<dst>(无|不设)单笔最低限额)",
                    rf"首次赎回(本?基金?)?{R_FUND_SHORT_NAME}([{R_CONJUNCTION}]{R_FUND_SHORT_NAME})?的单笔最.限额",
                    r"最小.*赎回单位为.*?份",
                ],
                "regs": {
                    "基金名称": [
                        rf"(?P<dst>{R_FUND_SHORT_NAME})([\/、和或与]+{R_FUND_SHORT_NAME})?.?{R_SINGLE_REDEMPTION}",
                        rf"({R_SINGLE_REDEMPTION}|[{R_CONJUNCTION}]|基金){R_NON_PUNCTUATION}*?(?<!首次赎回)(?P<dst>{R_FUND_SHORT_NAME})[{R_CONJUNCTION}][A-Z][类级]",
                        rf"({R_SINGLE_REDEMPTION}|[{R_CONJUNCTION}]|基金){R_NON_PUNCTUATION}*?(?<!首次赎回)(?P<dst>{R_FUND_SHORT_NAME})",
                        rf"({R_SINGLE_REDEMPTION}|[{R_CONJUNCTION}]|基金){R_NON_PUNCTUATION}*?(?P<dst>[^,.，。；;赎回]*?货币[A-Z])",
                        rf"(?<!持有本基金)(?P<dst>{R_FUND_SHORT_NAME})([\/、和或与]{R_FUND_SHORT_NAME})?{R_NON_PUNCTUATION}*?{R_SINGLE_REDEMPTION}",
                        r"通过[^;；。]*?(?P<dst>[A-Z][类级]((基金)?份额)?)[^;；。]*?{R_DANBI}",
                        # *gen_fund_name_regex("{R_DANBI}"),
                        rf"{R_SINGLE_REDEMPTION}(本?基金?)?{R_NON_PUNCTUATION}*?(?P<dst>{R_FUND_SHORT_NAME})的?单笔最.[限金]额",
                        rf"{R_SINGLE_REDEMPTION}(本?基金?)?(?P<dst>{R_FUND_SHORT_NAME})[{R_CONJUNCTION}]{R_FUND_SHORT_NAME}的?单笔最.[限金]额",
                        rf"已持有本基金(?P<dst>{R_FUND_SHORT_NAME})[\w\s]*{R_SINGLE_REDEMPTION}的?单笔最.[限金]额",
                    ],
                    "最低限额": [
                        rf"{R_SINGLE_REDEMPTION}(各类)?(基金)?(的|申请)?(或转换)?份?(额|数)?(单笔)?均?(最低[份限][额数]为?|不得[少低]于){R_AMOUNT}",
                        r"份[额数](?P<dst>(无|不设|不对)单笔最低(赎回)?(及最低持有)?(限额|份额进行限制))",
                        rf"{R_SINGLE_REDEMPTION}份额为(?P<dst>\d份)或.*的整数",
                        r"最小申购.赎回单位为(?P<dst>.*?份)",
                        rf"(?<!追加赎回)(?<!追加赎回[^,，].)((单|每)[次笔]|首笔)(最.)?(赎回(?!各类)[^,.，。；;]*?(人民币)?|金额为?){R_AMOUNT}",
                        rf"(?<!追加)赎回[^。，,]*?((单|每)[次笔]|首笔)[^,.，。；;]*?{R_AMOUNT}",
                        rf"(?<!追加|首次)赎回(金额)?下限为{R_AMOUNT}",
                        rf"{R_SINGLE_REDEMPTION}(本?基金?)?{R_NON_PUNCTUATION}*?{R_FUND_SHORT_NAME}的单笔最.限额为?{R_AMOUNT}",
                        rf"{R_FUND_SHORT_NAME}[\w\s]*{R_SINGLE_REDEMPTION}的?单笔最.限额{R_AMOUNT}",
                    ],
                    "销售平台": [
                        rf"(((持有|投资)[者人]|[账帐]户)(赎回)?时?([在通过]+该?|办理基金份额))(?P<dst>[^。;；,，或]*{R_PLATFORM_KEYWORDS})",
                        rf"(实际操作中|有其他规定的).*各(?P<dst>[^。;；,，或]*{R_PLATFORM_KEYWORDS})",
                        r"(?P<dst>直销机构或其他其他销售机构)",
                        r"通过(?P<dst>.*?)(赎回时[,，])?单笔赎回(申请|份额)不得少于",
                    ],
                },
                "neglect_answer_patterns": {
                    "销售平台": [
                        r"(持有人|投资者)(赎回时)?在(某一|该)?销售机构",
                    ],
                    "最低限额": [],
                    "基金名称": [],
                },
                "splits": [
                    r"[。；;](?![）)])",
                ],
            },
            gen_table_subscription("单笔赎回"),
        ],
    },
    {
        "path": ["单客户持仓下限"],
        "sub_primary_key": ["基金名称", "最低限额", "单客户持仓下限单位"],
        "divide_answers": True,
        "models": [
            {
                "name": "subscription",
                "main_column": "最低限额",
                "para_regs": [
                    r"最低(持有)?(本?基金)?(各类(基金)?)?([持保]有份额|份额余额)",
                    r"基金份额最低数量限制",
                    r"(保留|某一交易账户内)的?基金份额(余额)?不足",
                ],
                "multi_config": {
                    "基金名称": True,
                    "最低限额": False,
                    "单客户持仓下限单位": False,
                },
                "regs": {
                    "基金名称": [
                        r"(?P<dst>[A-Z][类级])",
                        r"(?P<dst>(东吴|兴全天添益)货币[A-Z])",
                    ],
                    "最低限额": [
                        rf"(?P<dst>(不[{R_CN}]+最低(持有|基金)份额[{R_CN}]*(限制|下限)))",
                        rf"最低(持有)?(本?基金)?(各类(基金)?)?([持保]有份额|份额余额)为{R_AMOUNT}",
                        rf"基金份额最低数量限制调整为{R_AMOUNT}",
                        rf"赎回时(或赎回后)?在销售机构([(（].{{2,4}}[）)])?保留的基金份额(余额)?不足{R_AMOUNT}",
                        rf"某一交易账户内的?基金份额(余额)?不足{R_AMOUNT}的.应一次性全部赎回",
                    ],
                    "单客户持仓下限单位": [
                        r"最低(持有)?(本?基金)?(各类(基金)?)?([持保]有份额|份额余额)为[\d.万]+(?P<dst>[元份])",
                        r"基金份额最低数量限制调整为[\d.万]+(?P<dst>[元份])",
                        r"赎回时(或赎回后)?在销售机构([(（].{2,4}[）)])?保留的基金份额(余额)?不足[\d.万]+(?P<dst>[元份])",
                        r"某一交易账户内的?基金份额(余额)?不足[\d.万]+(?P<dst>[元份])的.应一次性全部赎回",
                    ],
                },
            },
        ],
    },
    {
        "path": ["基金转出最低份额"],
        "sub_primary_key": ["基金名称", "最低限额"],
        "divide_answers": True,
        "models": [
            {
                "name": "partial_text",
                "multi": True,
                "multi_elements": True,
            },
            {
                "name": "subscription",
                "text_regs": [
                    r"(最低转换转出份额.*?){2,}",
                    r"份额(必须)?不得?(低|少)于",
                ],
                "para_regs": [
                    r"(最低转换转出份额.*?){2,}",
                    r"份额(必须)?不得?(低|少)于",
                ],
                "main_column": "最低限额",
                "multi_config": {
                    "基金名称": False,
                    "最低限额": False,
                },
                "regs": {
                    "基金名称": [
                        r"(?P<dst>[A-Z][类级]基金份额)",
                    ],
                    "最低限额": [
                        rf"[每单]笔最低转换转出份额及单个基金账户最低持有份额为{R_AMOUNT}",
                        rf"[每单]笔最低转换转出份额为{R_AMOUNT}",
                        rf"转出的(基金|最低)份额(必须)?不得?(低|少)于{R_AMOUNT}",
                    ],
                },
            },
            {
                "name": "row_match",
                "syllabus_regs": [r"最低申购金额"],
                "multi": True,
                "merge_char_result": False,
                "row_pattern": {"基金名称": [r"[A-Z]级基金份额"], "最低限额": [r"单笔转换最低份额"]},
                "content_pattern": {
                    "基金名称": [r"(?P<dst>[A-Z].*级基金份额)"],
                    "最低限额": [r"单笔转换最低份额(?P<dst>.+)"],
                },
                "split_pattern": {
                    "基金名称": r"额",
                    "最低限额": r"份",
                },
                "keep_separator": True,
            },
        ],
    },
    {
        "path": ["默认分红方式"],
        "divide_answers": True,
        "sub_primary_key": ["基金名称", "默认分红"],
        "models": [
            {
                "name": "partial_text",
                "multi": True,
                "merge_char_result": False,
                "model_alternative": True,
                "regs": {
                    "基金名称": [
                        r"(?P<dst>[A-Z][类级])[^,，；;。]*分配方式",
                    ],
                    "默认分红": [
                        r"方式([为是]|只采用)(?P<dst>现金分红|现金红利|红利再投资)",
                    ],
                },
            },
        ],
    },
    {
        "path": ["是否支持分红方式修改"],
        "divide_answers": True,
        "sub_primary_key": ["基金名称", "份额登记系统", "分红方式修改"],
        "models": [
            {
                "name": "partial_text",
                "multi": True,
                "merge_char_result": False,
                "model_alternative": True,
                "regs": {
                    "基金名称": [
                        r"(?P<dst>[A-Z][类级])[^,，；;。]*分配方式",
                    ],
                    "份额登记系统": [
                        r"登记在(?P<dst>.*?)下的基金份额",
                    ],
                    "分红方式修改": [
                        rf"(?P<dst>可选择((现金红利|将?现金红利)[{R_CONJUNCTION}]?){{1,2}}{R_NOT_SENTENCE_END}*自动转为{R_NOT_SENTENCE_END}*基金份额进行再投资)",
                        rf"(?P<dst>(可(自行)?选择|只能选择|只采用)(现金分红|现金红利|红利再投资|收益分配)的?([(（][{R_CN}]+[）)])?方式)",
                        r"(?<!默认的收益分配)(?<!默认的分红)方式(?P<dst>([为是]|只采用)(现金分红|现金红利|红利再投资))",
                    ],
                },
            },
        ],
    },
    {
        "path": ["托管机构"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"基金托管人[:：]指?(?P<dst>[^;；]*)",
                ],
            },
            {
                "name": "table_kv",
                "feature_black_list": [
                    r"银行业监督管理机构：",
                ],
                "regs": [
                    r"指(?P<dst>[^;；]*)",
                ],
            },
        ],
    },
    {
        "path": ["认购交易确认日期"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    rf"__regex__(基金份额的认购程序|投资人对基金份额的认购|认购安排)__regex__认购(申请)?的?((确认|限制|限额|方式)[{R_CONJUNCTION}]?){{1,2}}",
                ],
                "only_inject_features": True,
                "one_result_per_feature": False,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [
                        rf"(T|《基金合同》生效日){R_NOT_SENTENCE_END}*查询",
                        r"认购的确认以登记机构的确认结果为准",
                    ],
                },
            },
        ],
    },
    {
        "path": ["申购交易确认日期"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    rf"__regex__((申购|赎回|转换)[{R_CONJUNCTION}]?){{1,3}}的程序__regex__((申购|赎回|转换)[{R_CONJUNCTION}]?){{1,3}}(申请)?的?确认",
                ],
                "only_inject_features": True,
                "one_result_per_feature": False,
                "skip_merged_para": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "multi_elements": True,
                    "paragraph_pattern": [
                        rf"申购(或转换)?的?申请日|申购(或赎回)?申请{R_NOT_SENTENCE_END}*日进行确认|日规定时间受理的申请",
                        rf"T{R_NOT_SENTENCE_END}*查询{R_NOT_SENTENCE_END}*申购",
                        rf"T{R_NOT_SENTENCE_END}*申购{R_NOT_SENTENCE_END}*有效性进行确认",
                        rf"T{R_NOT_SENTENCE_END}*对该交易的有效性进行确认",
                        rf"((申购|赎回)[{R_CONJUNCTION}]?){{2}}{R_NOT_SENTENCE_END}*日进行确认",
                        r"申购赎回代理券商查询有关申请的确认情况",
                        rf"((申购|赎回)[{R_CONJUNCTION}]?){{2}}的确认以登记机构的确认结果为准",
                    ],
                },
            },
            {
                "name": "para_match",
                "syllabus_regs": [
                    rf"((申购|赎回|转换)[{R_CONJUNCTION}]?){{1,3}}(申请)?的?确认",
                ],
                "paragraph_pattern": [
                    rf"申购(或转换)?的?申请日|申购(或赎回)?申请{R_NOT_SENTENCE_END}*日进行确认|日规定时间受理的申请",
                    rf"T{R_NOT_SENTENCE_END}*查询{R_NOT_SENTENCE_END}*申购",
                    rf"T{R_NOT_SENTENCE_END}*申购{R_NOT_SENTENCE_END}*有效性进行确认",
                    rf"T{R_NOT_SENTENCE_END}*对该交易的有效性进行确认",
                    rf"((申购|赎回)[{R_CONJUNCTION}]?){{2}}{R_NOT_SENTENCE_END}*日进行确认",
                    r"申购赎回代理券商查询有关申请的确认情况",
                    rf"((申购|赎回)[{R_CONJUNCTION}]?){{2}}的确认以登记机构的确认结果为准",
                ],
            },
        ],
    },
    {
        "path": ["赎回交易确认日期"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    rf"__regex__((申购|赎回|转换)[{R_CONJUNCTION}]?){{1,3}}的程序__regex__((申购|赎回|转换)[{R_CONJUNCTION}]?){{1,3}}(申请)?的?确认",
                ],
                "only_inject_features": True,
                "one_result_per_feature": False,
                "skip_merged_para": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "multi_elements": True,
                    "paragraph_pattern": [
                        rf"赎回(或转换)?的?申请日|赎回申请{R_NOT_SENTENCE_END}*日进行确认|日规定时间受理的申请",
                        rf"T{R_NOT_SENTENCE_END}*查询{R_NOT_SENTENCE_END}*赎回",
                        rf"T{R_NOT_SENTENCE_END}*赎回{R_NOT_SENTENCE_END}*有效性进行确认",
                    ],
                },
            },
            {
                "name": "para_match",
                "combine_paragraphs": True,
                "syllabus_regs": [
                    rf"((申购|赎回|转换)[{R_CONJUNCTION}]?){{1,3}}(申请)?的?确认",
                ],
                "paragraph_pattern": [
                    rf"赎回(或转换)?的?申请日|赎回申请{R_NOT_SENTENCE_END}*日进行确认|日规定时间受理的申请",
                    rf"T{R_NOT_SENTENCE_END}*查询{R_NOT_SENTENCE_END}*赎回",
                    rf"T{R_NOT_SENTENCE_END}*赎回{R_NOT_SENTENCE_END}*有效性进行确认",
                ],
            },
        ],
    },
    {
        "path": ["单笔认购下限-原文"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__基金份额类别的限制",
                    r"__regex__基金份额认购原则及持有限额",
                    r"__regex__基金份额的?认购|认购安排__regex__认购的?限[制额]",
                ],
                "skip_merged_para": True,
                "table_model": "table_titles",
                "table_config": {
                    "multi_elements": True,
                    "first_row_as_title": True,
                    "feature_white_list": [
                        r"单笔认.*购",
                    ],
                },
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [
                        r"单笔认购份额不限",
                        r"认购最低|最低认购",
                        rf"认购[A-Z][{R_CN}]+最低",
                    ],
                    "neglect_regs": [],
                },
            },
        ],
    },
    {
        "path": ["单笔认购下限"],
        "sub_primary_key": ["基金名称", "最低限额", "销售平台"],
        "strict_group": True,
        "models": [
            {
                "name": "subscription",
                "main_column": "销售平台",
                "depends": ["单笔认购下限-原文"],
                "multi_config": {
                    "基金名称": True,
                    "最低限额": True,
                    "销售平台": False,
                },
                "para_regs": [
                    rf"(起点|[单每][次笔])[^,.。；;]*?{R_AMOUNT}",
                    rf"[单每][次笔]最.(认购)?金额为?{R_AMOUNT}",
                ],
                "regs": {
                    "基金名称": [
                        *gen_fund_name_regex("[单首][次笔]认购"),
                        r"(?P<dst>[A-Z]类)",
                    ],
                    "最低限额": [
                        rf"(起点|[单每][次笔])[^,.。；;]*?{R_AMOUNT}",
                        rf"[单每][次笔]最.(认购)?金额为?{R_AMOUNT}",
                    ],
                    "销售平台": [
                        *gen_platform_regex("(认购(?!金额)|单次)"),
                        rf"管理人(本基金)?(?P<dst>[^。;；,，]*{R_PLATFORM_KEYWORDS})",
                        r"^[(（]\d+[)）]\s*?\s*(?P<dst>[^。;；,，]*)的首次最低认购",
                    ],
                },
                "neglect_answer_patterns": {
                    "销售平台": [
                        r"可以?多次",
                    ]
                },
            },
            gen_table_subscription("单[次笔].*认.*购", splits="[(（]"),
        ],
    },
    {
        "path": ["单客户每日累计认购限额"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"(单[一个]?(投资[人者]|客户|账户))([（].*[）])?(在认购期间)?的?([每单]日)?累计认购",
                    r"每个基金交易账户的?认购金额进行其[他它]限制.具体限制请参看相关公告",
                ],
            },
        ],
    },
    {
        "path": ["首次认购上限"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["申购基数"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["赎回基数"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["单笔认购上限"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["基金转出最高份额"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["认购费率"],
        "pick_answer_strategy": "all",
        "models": [
            {
                "name": "partial_text",
                "regs": {
                    "认购费": [
                        r"基金的?认购费率?为(?P<dst>[\d.%％零]+)",
                        r"(?P<dst>本基金不(支付|收取)认购费)",
                        r"基金份额(?P<dst>不(支付|收取)认购费)",
                    ],
                    "基金名称": [
                        r"(?P<dst>[A-Z]类)基金份额不(支付|收取)认购费",
                    ],
                    "认购区间": [],
                    "购买金额": [],
                    "区间起始值": [],
                    "区间结束值": [],
                    "销售平台": [],
                    "销售对象": [],
                },
            },
            {
                "name": "subscription_rate",
                "elements_nearby": {"regs": ["认购费率"], "amount": 1, "step": -1},
                "feature_white_list": {
                    "认购区间": [
                        r"__regex__认购份额",
                    ],
                    "购买金额": [
                        r"__regex__认购份额",
                    ],
                    "区间起始值": [
                        r"__regex__认购份额",
                    ],
                    "区间结束值": [
                        r"__regex__认购份额",
                    ],
                    "认购费": [r"__regex__认购费率"],
                    "基金名称": [],
                    "销售平台": [],
                    "销售对象": [],
                },
                "cell_regs": {
                    "区间起始值": R_INTERVAL_START,
                    "区间结束值": R_INTERVAL_END,
                },
                "基金名称": {
                    "from_title": [
                        rf"(?P<dst>[A-Z]类)基金份额{R_NOT_SENTENCE_END}*认购费率",
                    ],
                },
                "销售平台": {
                    "from_title": [
                        rf"通过基金管理人的(?P<dst>{R_NOT_SENTENCE_END}*)认购本?(基金)?基金份额",
                    ],
                },
                "销售对象": {
                    "from_title": [
                        rf"^(本基金([A-Z]类基金份额))?.*认购本基金基金份额的(?P<dst>{R_NOT_SENTENCE_END}*?)适用下表特定认购费率",
                        rf"本基金([A-Z]类基金份额)?(?P<dst>{R_NOT_SENTENCE_END}*?)的?认购{R_NOT_SENTENCE_END}*认购费率如下",
                        rf"^(本基金([A-Z]类基金份额))?(?P<dst>{R_NOT_SENTENCE_END}*?)的?认购",
                        r"本基金基金份额的(?P<dst>.*)适用下表特定认购费率",
                    ],
                },
            },
        ],
    },
    {
        "path": ["申购费率"],
        # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/11186?projectId=36&treeId=59&fileId=879&schemaId=2
        "model_relation": [0, (1, 2, 3)],
        "post_process": "post_process_subscription_rate",
        "models": [
            {
                "name": "partial_text",
                "neglect_patterns": [r"申购本基金管理人管理的其他基金不收取申购费"],
                "regs": {
                    "申购费": [
                        r"基金的?申购费率?为(?P<dst>[\d.%％零]+)",
                        r"(?P<dst>不(支付|收取)申购费)",
                        r"基金份额时?(?P<dst>不(支付|收取)申购费)",
                        r"基金份额的?申购费率?为(?P<dst>[\d.%％零]+)",
                        r"本基金的?申购[、和及与]赎回费率为(?P<dst>[\d.%％零]+)",
                        r"份额的投资人.申购费率为(?P<dst>[\d.%％零]+)",
                    ],
                    "基金名称": [
                        rf"(?P<dst>(([A-Z]类|[A-Z])[{R_CONJUNCTION}]?){{1,3}})(基金)?份额时?不(支付|收取)申购费",
                        rf"(?P<dst>(([A-Z]类|[A-Z])[{R_CONJUNCTION}]?){{1,3}})(基金)?份额的投资人.申购费率为",
                        r"(?P<dst>[A-Z]类)基金份额的?申购费率?为",
                    ],
                    "申购区间": [],
                    "购买金额": [],
                    "区间起始值": [],
                    "区间结束值": [],
                    "销售平台": [],
                    "销售对象": [],
                },
            },
            gen_subscription_rate(
                "table_regroup",
                {
                    "main_col": [r"申购金额"],
                    "assistant_col": [r"^[A-Z]类基金份额(申购费率)?$", r"^申购费率[(（]"],
                },
            ),
            gen_subscription_rate(
                "subscription_rate",
                {
                    "neglect_syllabus_regs": [r"与基金销售[相有]关的费用"],
                },
            ),
            gen_subscription_rate("subscription_rate"),
        ],
    },
    {
        "path": ["赎回费率"],
        "models": [
            gen_redemption_rate(
                "table_regroup",
                {
                    "regs": [
                        "赎回费率",
                        "赎回时收取赎回费",
                        "基金份额赎回时收取.*赎回费",
                    ],
                    "neglect_regs": [
                        r"场内",  # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/10702?projectId=36&treeId=59&fileId=903&schemaId=2
                    ],
                    "amount": 5,
                    "step": -1,
                },
                {
                    "main_col": [r"持有(基金)?(期|年限|时间)"],
                    "assistant_col": [r"^[A-Z]类基金份额$"],
                },
            ),
            gen_redemption_rate(
                "split_table_row",
                {
                    "regs": [
                        "赎回费率为[:：]$",
                    ],
                    "neglect_regs": [
                        r"场内",
                    ],
                    "amount": 1,
                    "step": -1,
                },
            ),
            gen_redemption_rate(
                "split_table_row",
                {
                    "regs": [
                        "赎回费率",
                        "赎回时收取赎回费",
                        "基金份额赎回时收取.*赎回费",
                    ],
                    "neglect_regs": [
                        r"场内",
                    ],
                    "amount": 5,
                    "step": -1,
                },
            ),
            {
                "name": "partial_text",
                "neglect_patterns": [
                    r"赎回本基金管理人管理的其他基金不收取赎回费",
                    r"持续持有期不少于\d+日的基金份额持有人不收取赎回费",
                ],
                "regs": {
                    "赎回费": [
                        r"基金的?(申购费[用率]?[、和及与])?赎回费率?为(?P<dst>[\d.%％零]+)",
                        r"(?P<dst>不(支付|收取)(申购费用[、和及与])?赎回费用?)",
                        r"基金份额时?(?P<dst>不(支付|收取)(申购费用[、和及与])?赎回费)",
                        r"基金份额的?(申购费[用率]?[、和及与])?赎回费[用率]?为(?P<dst>[\d.%％零]+)",
                        r"赎回费[用率]?为(?P<dst>[\d.%％零]+)",
                        r"(?P<dst>不再收取赎回费)",
                    ],
                    "基金名称": [
                        r"(?P<dst>([A-Z]类[、和及与])*[A-Z]类)基金份额时?不(支付|收取)(申购费[用率]?[、和及与])?赎回费",
                        r"(?P<dst>[A-Z]类)基金份额的?(申购费[用率]?[、和及与])?赎回费率?为",
                    ],
                    "赎回区间": [],
                    "购买金额": [],
                    "区间起始值": [],
                    "区间结束值": [],
                    "销售平台": [],
                    "销售对象": [],
                },
            },
        ],
    },
    {
        "path": ["收费方式"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": {
                    "费用类型": [
                        r"^(?P<dst>(申购|认购))本基金",
                        r"^本基金(?P<dst>(申购|认购)费)用采",
                    ],
                    "收费": [
                        r"采(用|取)(?P<dst>.*?)模式",
                    ],
                },
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__(申购|认购)费率、赎回费率",
                    r"__regex__申购份额、赎回金额的计算",
                    r"__regex__申购、赎回及转换的费用__regex__申购费用",
                ],
                "only_inject_features": True,
                "skip_merged_para": True,
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": {
                        "费用类型": [
                            r"[\d]+、(?P<dst>(申购|认购)费)率$",
                            r"[\d]+、(?P<dst>(申购|认购))份额的计算方式[:：]",
                            r"需[缴交]纳[前后]端(?P<dst>[申认]购费)",
                        ],
                        "收费": [
                            r"采用(?P<dst>.*?)模式",
                            r"需[缴交]纳(?P<dst>.*?)[申认]购费",
                        ],
                    },
                    "multi_elements": True,
                },
            },
        ],
    },
    {
        "path": ["升降级阈值"],
        "sub_primary_key": ["升降级别"],
        "models": [
            {
                "name": "subscription",
                "main_column": "升降级别",
                "multi_config": {
                    "升降级别": True,
                },
                "neglect_text_regs": [r"[升降]级[:：]", r"取消.*份额.*升降级"],
                "neglect_syllabus_regs": [
                    r"最低保留",
                    r"重要提示",
                    r"申购[与和]赎回的数[额量]限制",
                    r"基金份额等级的限制",
                ],
                "para_regs": [
                    r"(?P<dst>(.[类级]|相应))(基金份额|持有人)(全部|自动)?[升降][级为]",
                ],
                "regs": {
                    "升降级阈值类型": [
                        r"(超过|达到|[低少]于|最低余额为)(?P<dst>[\d.,，\s千百万]+[元年月周日天份]+)",
                        r"(?P<dst>.年)后的年度对日",
                    ],
                    "升降级别": [r"(?P<dst>([ABCD\d]+[类级]|相应))(基金份额|持有人)(全部|自动)?[升降][级为]"],
                    "最小值": [
                        r"([低少]于|最低余额为)(?P<dst>[\d.,，\s千百万]+)[元年月周日天份]+",
                    ],
                    "最小值单位": [
                        r"([低少]于|最低余额为)(?P<dst>[\d.,，\s]+[千百万]*[元年月周日天份]+)",
                    ],
                    "最大值": [
                        r"(超过|达到)(?P<dst>[\d.,，\s千百万]+)[元年月周日天份]+",
                        r"(?P<dst>.年)后的年度对日",
                    ],
                    "最大值单位": [
                        r"(超过|达到)(?P<dst>[\d.,，\s]+[千百万]*[元年月周日天份]+)",
                        r"(?P<dst>.年)后的年度对日",
                    ],
                },
            },
            {
                "name": "subscription",
                "main_column": "升降级别",
                "multi_config": {
                    "升降级别": True,
                },
                "neglect_text_regs": [r"[升降]级[:：]", r"取消.*份额.*升降级"],
                "para_regs": [
                    r"[升降]级为(?P<dst>.[类级])",
                ],
                "regs": {
                    "升降级阈值类型": [
                        r"(超过|低于|最低余额为)(?P<dst>[\d.,，\s千百万]+[元年月周日天份]+)",
                    ],
                    "升降级别": [r"[升降]级为(?P<dst>.[类级])"],
                    "最大值": [
                        r"(低于|最低余额为)(?P<dst>[\d.,，\s千百万]+)[元年月周日天份]+",
                    ],
                    "最大值单位": [
                        r"(低于|最低余额为)(?P<dst>[\d.,，\s]+[千百万]*[元年月周日天份]+)",
                    ],
                    "最小值": [
                        r"(超过)(?P<dst>[\d.,，\s千百万]+)[元年月周日天份]+",
                    ],
                    "最小值单位": [
                        r"(超过)(?P<dst>[\d.,，\s]+[千百万]*[元年月周日天份]+)",
                    ],
                },
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": get_predictor_options(predictor_options),
}
