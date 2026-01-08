"""
产品资料概要
"""

from remarkable.predictor.cmbchina_predictor.schemas import (
    R_INTERVAL_END,
    R_INTERVAL_START,
    gen_platform_regex,
    get_predictor_options,
    p_holding_period,
    p_holding_period_unit,
)
from remarkable.predictor.cmbchina_predictor.schemas.cmbchina_rate_adjustment_schema import R_FUND_SUFFIX
from remarkable.predictor.common_pattern import R_CN, R_HYPHEN
from remarkable.predictor.eltype import ElementClass

P_FUND_NAME_TITLE = [
    r"(?P<dst>.*(混合|发起)[A-Z])",
    r"(?P<dst>([A-Z]类[、和及与])*[A-Z]类)基金(份额)?.(具体)?(认购|申购|赎回)费率",
]

predictor_options = [
    {
        "path": ["分级基金"],
        "sub_primary_key": ["基金简称", "基金代码"],
        "divide_answers": True,
        "models": [
            {
                "name": "table_kv",
                "multi": True,
                "merge_cell_result": False,
                "keep_dummy": True,
                "feature_black_list": {
                    "基金简称": [r"__regex__.*"],
                    "基金代码": [r"__regex__.*"],
                },
                "feature_white_list": {
                    "基金简称": [
                        r"__regex__(分级|下属)基金([名简]称|份额类别)(?!代码)",
                        r"__regex__基金[名简]称[A-Z]",
                        r"__regex__份额类别[名简]称(?!代码)",
                    ],
                    "基金代码": [
                        r"__regex__(分级|下属)基金(交易|份额类别)?代码[A-Z]?",
                        r"__regex__基金(交易|份额类别)?代码[A-Z]",
                        r"__regex__份额类别子代码",
                    ],
                },
            },
        ],
    },
    {
        "path": ["赎回限制类型"],
        "models": [
            {
                "name": "partial_text",
            },
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "regs": [
                    r"开放频率(每日开放申购.)?(?P<dst>.*(最短持有期|滚动运作期|锁定(持有)?期).*)",
                ],
            },
        ],
    },
    {
        "path": ["赎回限制"],
        "models": [
            {
                "name": "partial_text",
            },
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "regs": [
                    r"开放频率(每日开放申购.)?(?P<dst>.*(最短持有期|滚动运作期|锁定(持有)?期).*)",
                ],
            },
        ],
    },
    {
        "path": ["基金名称"],
        "models": [
            {
                "name": "middle_paras",
                "top_anchor_content_regs": [rf"(?P<content>.*?基金(中基金)?{R_FUND_SUFFIX}?)"],
                "top_default": True,
                "bottom_anchor_regs": [r"产品资料概要"],
                "page_range": [0],
            },
            {
                "name": "middle_paras",
                "bottom_anchor_content_regs": [rf"(?P<content>.*?基金(中基金)?{R_FUND_SUFFIX}?)"],
                "top_default": True,
                "include_bottom_anchor": True,
                "bottom_anchor_regs": [r"产品资料概要"],
                "page_range": [0],
            },
            {
                "name": "fixed_position",
                "target_element": [
                    ElementClass.PARAGRAPH.value,
                ],
                "pages": [0],
                "regs": [
                    rf"(?P<dst>.*?基金(中基金)?{R_FUND_SUFFIX}?)",
                ],
                "neglect_patterns": [r"本概要|、|投资者|^基金|基金的投资"],
            },
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    rf"(?P<dst>.*?基金(中基金)?{R_FUND_SUFFIX}?)",
                ],
                "neglect_answer_patterns": [r"^基金|基金的投资"],
            },
        ],
    },
    {
        "path": ["基金代码"],
        "models": [
            {
                "name": "cell_partial_text",
            },
        ],
    },
    {
        "path": ["管理费率"],
        "models": [
            {
                "name": "cell_partial_text",
                "model_alternative": True,
                "from_cell": False,
                "neglect_patterns": [r"(托管|服务|披露|审计)费"],
                "regs": [
                    r"[:：](?P<dst>[\d.]+[%％])",
                    r"年费率(计提。)?(?P<dst>[\d.]+[[%％])",
                    r"管理费(计提。)?(?P<dst>[\d.]+[%％])",
                    r"管理费(?P<dst>min.*[\d.]+[%％])",
                ],
            },
        ],
    },
    {
        "path": [
            "销售服务费率",
        ],
        "sub_primary_key": ["基金名称", "销售服务费"],
        "divide_answers": True,
        "models": [
            {
                "name": "kv_partial_text",
                "from_cell": False,
                "column_from_multi_rows": True,
                "model_alternative": True,
                "multi_rows": True,
                "regs": {
                    "基金名称": [
                        r"(?P<dst>销售服务费[A-Z])[\d.]+[%％]",
                        r"销售服务费[(（]?(?P<dst>.*?)[)）]?[\d.]+[%％]",
                        r"(?P<dst>.*)销售服务费[\d.]+[%％]",
                    ],
                    "销售服务费": [r"销售服务费.*?(?P<dst>[\d.]+[%％])", rf"销售服务费.*?(?P<dst>{R_HYPHEN})"],
                },
            },
        ],
    },
    {
        "path": ["产品持有期"],
        "models": [
            {
                "name": "fixed_position",
                "target_element": [ElementClass.PARAGRAPH.value],
                "pages": [0],
                "regs": p_holding_period,
                "neglect_patterns": [
                    r"投资者阅读",
                ],
            },
            # 处理标题识别为页眉
            {
                "name": "fixed_position",
                "target_element": [ElementClass.PAGE_HEADER.value],
                "pages": [0],
                "regs": p_holding_period,
            },
        ],
    },
    {
        "path": ["产品持有期单位"],
        "models": [
            {
                "name": "fixed_position",
                "target_element": [ElementClass.PARAGRAPH.value],
                "pages": [0],
                "regs": p_holding_period_unit,
                "neglect_patterns": [
                    r"投资者阅读",
                ],
            },
            # 处理标题识别为页眉
            {
                "name": "fixed_position",
                "target_element": [ElementClass.PAGE_HEADER.value],
                "pages": [0],
                "regs": p_holding_period_unit,
            },
        ],
    },
    {
        "path": ["产品简称"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["托管机构"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["认购费率"],
        "pick_answer_strategy": "all",
        "models": [
            {
                "name": "subscription",
                "text_regs": [
                    r"认购费.*?持有期.*?认购费.*?持有期.*?认购费",
                ],
                "main_column": "认购费",
                "regs": {
                    "认购费": [r"认购费为(?P<dst>[\d.%％零]+)"],
                    "认购区间": [
                        r"(?P<dst>持有期[大小]于\d+天([（(]含[)）])?(小于\d+天)?([（(]含[)）])?)",
                    ],
                    "购买金额": [
                        r"(?P<dst>持有期[大小]于\d+天([（(]含[)）])?(小于\d+天)?([（(]含[)）])?)",
                    ],
                    "区间起始值": [
                        r"持有期大于(?P<dst>\d+天)([（(]含[)）])?(小于\d+天)?([（(]含[)）]?)?",
                    ],
                    "区间结束值": [
                        r"(持有期大于\d+天)?([（(]含[)）])?小于(?P<dst>\d+天)([（(]含[)）])?",
                    ],
                },
            },
            {
                "name": "partial_text",
                "neglect_text_regs": [
                    r"认购费.*?持有期.*?认购费.*?持有期.*?认购费",
                ],
                "regs": {
                    "认购费": [
                        r"基金的?认购费率?为(?P<dst>[\d.%％零]+)",
                        r"(?P<dst>不(支付|收取|涉及)认购费)",
                        r"基金份额(?P<dst>不(支付|收取)认(.申)?购费)",
                    ],
                    "基金名称": [
                        r"(?P<dst>([A-Z]类[、和及与])*[A-Z]类)(基金)?份额不(支付|收取)认(.申)?购费",
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
                "name": "table_row",
                "elements_nearby": {
                    "regs": [
                        "认购费率",
                        r"以下费用在(认购.)?申购.赎回基金过程中收取",
                    ],
                    "amount": 2,
                    "step": -1,
                },
                "header_regs": [r"认购费"],
                "feature_white_list": {
                    "认购区间": [
                        r"__regex__份额",
                    ],
                    "购买金额": [
                        r"__regex__份额",
                    ],
                    "区间起始值": [
                        r"__regex__份额",
                    ],
                    "区间结束值": [
                        r"__regex__份额",
                    ],
                    "认购费": [],
                    "基金名称": [],
                    "销售平台": [],
                    "销售对象": [
                        r"__regex__备注",
                    ],
                },
                "cell_regs": {
                    "区间起始值": R_INTERVAL_START,
                    "区间结束值": R_INTERVAL_END,
                    "销售对象": [
                        r"(?P<dst>非?养老金用户)",
                        r".*",
                    ],
                },
                "special_title_pattern": P_FUND_NAME_TITLE,
                "基金名称": {
                    "from_title": P_FUND_NAME_TITLE,
                },
            },
        ],
    },
    {
        "path": ["申购费率"],
        "pick_answer_strategy": "all",
        "models": [
            {
                "name": "partial_text",
                "multi_elements": True,
                "regs": {
                    "申购费": [
                        r"申购费[A-Z][:：]本基金(?P<dst>不(支付|收取)申购费用?)",
                        r"申购费[:：]该费率为(?P<dst>[\d.%％零]+)",
                    ],
                    "基金名称": [
                        r"申购费(?P<dst>[A-Z])[:：]本基金不(支付|收取)申购费",
                    ],
                    "申购区间": [],
                    "购买金额": [],
                    "区间起始值": [],
                    "区间结束值": [],
                    "销售平台": [],
                    "销售对象": [],
                },
            },
            {
                "name": "partial_text",
                "neglect_patterns": [r"申购本基金管理人管理的其他基金不收取申购费"],
                "regs": {
                    "申购费": [
                        r"基金的?申购费率?为(?P<dst>[\d.%％零]+)",
                        rf"(?P<dst>不(支付|收取|涉及)([{R_CN}]{{2}}费?用?[、和及与])*申购费用?)",
                        rf"(?P<dst>不(支付|收取|涉及)申购([、和及与][{R_CN}]{{2}})*费用?)",
                        r"基金份额时?(?P<dst>不(支付|收取)申购费)",
                        r"基金份额的?申购费率?为(?P<dst>[\d.%％零]+)",
                        r"本基金的?申购[、和及与]赎回费率为(?P<dst>[\d.%％零]+)",
                    ],
                    "基金名称": [
                        r"(?P<dst>([A-Z]类[、和及与])*[A-Z]类)(基金)?份额时?不(支付|收取)申购费",
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
            {
                "name": "table_row",
                "multi_elements": True,
                "header_regs": [r"申购费"],
                "neglect_row": [
                    r"(不收取?|无)申购费",
                    r"赎回费|认购费",
                    r"投资人在申购本基金时.申购赎回代理机",
                ],
                "elements_nearby": {
                    "regs": [
                        "申购费率",
                        r"以下费用在(认购.)?申购.赎回基金过程中收取",
                    ],
                    "amount": 3,
                    "step": -1,
                },
                "distinguish_header": False,
                "lazy_match": True,
                "feature_white_list": {
                    "申购区间": [
                        r"__regex__[金份]额|期限",
                    ],
                    "购买金额": [
                        r"__regex__[金份]额|期限",
                    ],
                    "区间起始值": [
                        r"__regex__[金份]额|期限",
                    ],
                    "区间结束值": [
                        r"__regex__[金份]额|期限",
                    ],
                    "申购费": [
                        r"__regex__费率",
                    ],
                    "基金名称": [],
                    "销售平台": [],
                    "销售对象": [
                        r"__regex__备注",
                    ],
                },
                "neglect_patterns": [
                    r"(申购|基金)(费率|[金份]额)",
                    r"情形|费率|金额",
                ],
                "cell_regs": {
                    "区间起始值": R_INTERVAL_START,
                    "区间结束值": R_INTERVAL_END,
                    "销售对象": [
                        r"(?P<dst>非?养老金用户)",
                        r".*",
                    ],
                },
                "special_title_pattern": P_FUND_NAME_TITLE,
                "基金名称": {
                    "from_title": P_FUND_NAME_TITLE,
                    "from_above_row": [
                        r"(?P<dst>([A-Z]类[、和及与])*[A-Z]类)基金份额",
                    ],
                },
                "销售平台": {
                    "from_title": gen_platform_regex("申购"),
                },
                "销售对象": {
                    "from_title": [
                        r"(?P<dst>(上述|其他)投资(群体|者))",
                    ],
                },
            },
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "regs": {
                    "申购费": [
                        r"(?P<dst>(不收取?|无)申购费)",
                        r"申购费.*?额(?P<dst>[\d.\s%％]+)的标准",
                    ],
                    "基金名称": [
                        r"(?P<dst>[A-Z]类份额)(不收取?|无)申购费",
                    ],
                    "申购区间": [],
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
        "path": ["赎回费率"],
        "models": [
            {
                "name": "partial_text",
                "multi_elements": True,
                "regs": {
                    "赎回费": [
                        r"赎回费[A-Z][:：]本基金(在一般情况下)?(?P<dst>不(支付|收取)赎回费用?)",
                    ],
                    "基金名称": [
                        r"赎回费(?P<dst>[A-Z])[:：]本基金(在一般情况下)?不(支付|收取)赎回费",
                    ],
                    "赎回区间": [],
                    "购买金额": [],
                    "区间起始值": [],
                    "区间结束值": [],
                    "销售平台": [],
                    "销售对象": [],
                },
            },
            {
                "name": "partial_text",
                "neglect_patterns": [
                    r"赎回本基金管理人管理的其他基金不收取赎回费",
                    r"持续持有期不少于\d+日的基金份额持有人不收取赎回费",
                ],
                "regs": {
                    "赎回费": [
                        r"基金的?(申购费[用率]?[、和及与])?赎回费率?为(?P<dst>[\d.%％零]+)",
                        rf"(?P<dst>不(支付|收取|涉及)([{R_CN}]{{2}}费?用?[、和及与])*赎回费用?)",
                        r"基金份额时?(?P<dst>不(支付|收取)(申购费用[、和及与])?赎回费)",
                        r"基金份额的?(申购费[用率]?[、和及与])?赎回费[用率]?为(?P<dst>[\d.%％零]+)",
                        r"赎回费[用率]?为(?P<dst>[\d.%％零]+)",
                    ],
                    "基金名称": [
                        r"(?P<dst>([A-Z]类[、和及与])*[A-Z]类)(基金)?份额时?不(支付|收取)(申购费[用率]?[、和及与])?赎回费",
                        r"(?P<dst>([A-Z]类[、和及与])*[A-Z]类)(基金)?份额的?(申购费[用率]?[、和及与])?赎回费率?为",
                    ],
                    "赎回区间": [],
                    "购买金额": [],
                    "区间起始值": [],
                    "区间结束值": [],
                    "销售平台": [],
                    "销售对象": [],
                },
            },
            {
                "name": "table_row",
                "multi_elements": True,
                "row_header_regs": [r"赎回费"],
                "neglect_row": [
                    r"不收取?赎回费",
                    r"赎回费..(不收取?|无)",
                    r"投资人在申购本基金时.申购赎回代理机",
                    r"申购费|认购费",
                ],
                "elements_nearby": {
                    "regs": [
                        "赎回费率",
                        r"以下费用在(认购.)?申购.赎回基金过程中收取",
                        r"基金销售相关费用",
                    ],
                    "amount": 7,
                    "step": -1,
                },
                "distinguish_header": False,
                "lazy_match": True,
                "feature_white_list": {
                    "赎回区间": [
                        r"__regex__持有期",
                    ],
                    "购买金额": [
                        r"__regex__持有期",
                    ],
                    "区间起始值": [
                        r"__regex__持有期",
                    ],
                    "区间结束值": [
                        r"__regex__持有期",
                    ],
                    "赎回费": [
                        r"__regex__费率",
                    ],
                    "基金名称": [],
                    "销售平台": [],
                    "销售对象": [
                        r"__regex__备注",
                    ],
                },
                "neglect_patterns": [
                    r"(赎回|基金)(费率|[金份]额)",
                    r"情形|费率|金额|持有期",
                ],
                "cell_regs": {
                    "区间起始值": R_INTERVAL_START,
                    "区间结束值": R_INTERVAL_END,
                    "销售对象": [
                        r"(?P<dst>非?养老金用户)",
                        r".*",
                    ],
                },
                "special_title_pattern": P_FUND_NAME_TITLE,
                "基金名称": {
                    "from_title": P_FUND_NAME_TITLE,
                    "from_above_row": [
                        r"(?P<dst>([A-Z]类[、和及与])*[A-Z]类)基金份额",
                    ],
                },
                "销售平台": {
                    "from_title": gen_platform_regex("赎回"),
                },
                "销售对象": {
                    "from_title": [
                        r"(?P<dst>(上述|其他)投资(群体|者))",
                    ],
                },
            },
            {
                "name": "table_row",
                "elements_nearby": {
                    "regs": [
                        "^赎回费$",
                    ],
                    "amount": 1,
                    "step": -1,
                },
                "distinguish_header": False,
                "lazy_match": True,
                "feature_white_list": {
                    "赎回区间": [
                        r"__regex__持有期",
                    ],
                    "购买金额": [
                        r"__regex__持有期",
                    ],
                    "区间起始值": [
                        r"__regex__持有期",
                    ],
                    "区间结束值": [
                        r"__regex__持有期",
                    ],
                    "赎回费": [
                        r"__regex__费率",
                    ],
                    "基金名称": [],
                    "销售平台": [],
                    "销售对象": [
                        r"__regex__备注",
                    ],
                },
                "neglect_patterns": [
                    r"(赎回|基金)(费率|[金份]额)",
                    r"情形|费率|金额|持有期",
                ],
                "cell_regs": {
                    "区间起始值": R_INTERVAL_START,
                    "区间结束值": R_INTERVAL_END,
                    "销售对象": [
                        r"(?P<dst>非?养老金用户)",
                        r".*",
                    ],
                },
                "基金名称": {
                    "from_title": [
                        r"(?P<dst>([A-Z]类[、和及与])*[A-Z]类)基金份额.(具体)?赎回费率",
                        r"(?P<dst>.*混合[A-Z])",
                    ],
                    "from_above_row": [
                        r"(?P<dst>([A-Z]类[、和及与])*[A-Z]类)基金份额",
                    ],
                },
                "销售平台": {
                    "from_title": gen_platform_regex("赎回"),
                },
                "销售对象": {
                    "from_title": [
                        r"(?P<dst>(上述|其他)投资(群体|者))",
                    ],
                },
            },
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "regs": {
                    "赎回费": [
                        r"(?P<dst>(不收取?|无)赎回费)",
                        r"赎回费..(?P<dst>(不收取?|无))",
                        r"赎回费.*?额(?P<dst>[\d.\s%％]+)的标准",
                    ],
                    "基金名称": [],
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
                "name": "cell_partial_text",
            },
            {
                "name": "cell_partial_text",
                "model_alternative": True,
                "filter_by": "col",
                "from_cell": False,
                "费用类型": {"regs": [r"(?P<dst>([申认]购费))（前收费）"]},
            },
        ],
    },
]


prophet_config = {
    "depends": {},
    "predictor_options": get_predictor_options(predictor_options),
}
