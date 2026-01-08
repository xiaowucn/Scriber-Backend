"""“小而分散”类资产"""

from remarkable.predictor.sse_predictor.predictor_config import SPECIAL_ATTR_PATTERNS

from . import R_IGNORE_HEADER_PATTERNS, R_REPORT_TITLE_PATTERNS

predictor_options = [
    {
        "path": ["基本情况"],
        "models": [
            {
                "name": "table_kv",
                "multi_elements": True,
                "基础资产买方": {
                    "regs": [r"(?P<dst>.*公司)"],
                },
                "基础资产卖方": {
                    "regs": [r"(?P<dst>.*公司)"],
                },
                "可用于购买新增基础资产的价款总额（万元）": {
                    "feature_white_list": [
                        "__regex__可用于购买新增基础资产的价款总额",
                        "__regex__当期实收的回收款总额",
                        "__regex__可用于购买的新增基础资产的价款总额",
                        "__regex__可用于购买新增基础资产的价款总额",
                        "__regex__实际循环购买的基础资产本金金额",
                    ],
                },
                "可供购买的基础资产总额（万元）": {
                    "feature_white_list": [
                        "__regex__可供购买的基础资产总额",
                        "__regex__当期循环发放贷款本金总额",
                        "__regex__可供购买的基础资产总额",
                        "__regex__可供购买的基础资产总额",
                        "__regex__实际循环购买的基础资产本金金额",
                    ],
                },
            },
        ],
    },
    {
        "path": ["基本情况", "报告名称"],
        "models": [
            {
                "name": "middle_paras",
                "top_greed": False,
                "use_top_crude_neighbor": True,
                "include_top_anchor": False,
                "include_bottom_anchor": True,
                "possible_element_counts": 200,
                "top_anchor_regs": [r"证券代码.*?\d+.*?证券简称"],
                "bottom_anchor_regs": R_REPORT_TITLE_PATTERNS,
                "bottom_anchor_content_regs": R_REPORT_TITLE_PATTERNS,
            },
            {
                "name": "para_match",
                "paragraph_pattern": R_REPORT_TITLE_PATTERNS,
                "use_crude_answer": False,
                "combine_paragraphs": True,
                "multi_elements": True,
                "index_range": (0, 10),
            },
        ],
    },
    {
        "path": ["基本情况", "循环购买时间"],
        "models": [
            {
                "name": "re_buy_date",
                "anchor_regs": r"循环购买.*?情况$",
                "paragraph_pattern": r"^本.*?第.+次.+买",
                "content_pattern": SPECIAL_ATTR_PATTERNS["date"],
                "use_crude_answer": False,
                "index_range": (0, 100),
            }
        ],
    },
    {
        "path": ["基本情况", "循环购买时间（报告期间）"],
        "models": [
            {
                "name": "re_buy_date",
                "anchor_regs": R_REPORT_TITLE_PATTERNS,
                "paragraph_pattern": r"^报告期间",
                "content_pattern": SPECIAL_ATTR_PATTERNS["date"],
                "use_crude_answer": False,
                "index_range": (0, 20),
            }
        ],
    },
    {
        "path": ["基本情况", "基础资产买方（段落）"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"由(?P<dst>\w+)[(（]\w+?简称",
                ],
            }
        ],
    },
    {
        "path": ["基本情况", "基础资产卖方（段落）"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"[，；。](?P<dst>\w+)[(（]\w+?简称.*?原始权益",
                ],
            }
        ],
    },
    {
        "path": ["基本情况", "循环购买账户资金划转情况"],
        "models": [{"name": "found_trans", "keep_parent": False, "match_method": "similarity"}],
    },
    {
        "path": ["新增基础资产情况"],
        "models": [
            {
                "name": "auto",
                "custom_models": {
                    "table_kv": "table_kv",
                },
                "model|table_kv": {
                    "neglect_title_patterns": [
                        "资产池",
                        "变化",
                        "剩余",
                        "[账帐]期",
                        "利率",
                    ],
                    "新增基础资产债务人数量（个）": {
                        "feature_white_list": [r"__regex__新增.*债务人数"],
                    },
                },
            },
        ],
    },
    {
        "path": ["新增基础资产利率分布"],
        "sub_primary_key": ["基础资产利率分布(%)"],
        "models": [
            {
                "name": "table_row",
                "multi": True,
                "location_threshold": 0.05,
                "title_patterns": [
                    r"新增基础资产.*?率",
                ],
                "neglect_header_regs": R_IGNORE_HEADER_PATTERNS,
                "基础资产利率分布(%)": {
                    "feature_white_list": [r"__regex__^(利|费)率$"],
                },
                "未偿余额（万元）": {
                    "feature_white_list": [r"__regex__(本金|未偿|贷款)(本金|余额|规模)"],
                },
                "占比(%）": {
                    "feature_white_list": [
                        r"__regex__^占比$",
                        r"__regex__(规模|余额)占比",
                    ],
                },
            }
        ],
    },
    {
        "path": ["新增基础资产剩余期限分布"],
        "sub_primary_key": ["基础资产剩余期限分布（月）"],
        "models": [
            {
                "name": "extra_date_info",
                # 'name': 'table_row',
                "location_threshold": 0.05,
                "multi": True,
                "neglect_header_regs": R_IGNORE_HEADER_PATTERNS,
                "title_patterns": [
                    r"新增",
                ],
                "基础资产剩余期限分布（月）": {
                    "feature_white_list": [r"__regex__(合同)?剩余期限"],
                },
                "未偿余额（万元）": {
                    "feature_white_list": [r"__regex__(本金|未偿|贷款)(本金|余额|规模)"],
                },
                "占比(%）": {
                    "feature_white_list": [
                        r"__regex__^占比$",
                        r"__regex__(规模|余额)占比",
                    ],
                },
            }
        ],
    },
    {
        "path": ["新增基础资产账期分布"],
        "sub_primary_key": ["基础资产账期分布（月）"],
        "models": [
            {
                "name": "extra_date_info",
                "multi": True,
                "neglect_header_regs": R_IGNORE_HEADER_PATTERNS,
            }
        ],
    },
    # TODO: 以下字段标注暂缺
    # {
    #     'path': ['新增债务人所属地区分布'],
    # },
    # {
    #     'path': ['新增债务人年龄分布'],
    # },
    {
        "path": ["基础资产变化情况-循环购买前"],
        "models": [
            {
                "name": "auto",
                "custom_models": {
                    "table_kv": "table_kv",
                    "table_tuple": "table_row",
                },
                "model|table_row": {
                    "parse_by": "col",
                    "neglect_header_regs": [r"(末|终|结|后)", r"([增加]减|变化)"],
                },
            },
        ],
    },
    {
        "path": ["基础资产变化情况-循环购买后"],
        "models": [
            {
                "name": "auto",
                "custom_models": {
                    "table_kv": "table_kv",
                    "table_tuple": "table_row",
                },
                "model|table_row": {
                    "parse_by": "col",
                    "neglect_header_regs": [r"(初|首|始|前)", r"([增加]减|变化)"],
                },
                "model|table_kv": {
                    "债务人数量（个）": {
                        "feature_white_list": [r"__regex__期末.*?债务人数"],
                    },
                },
            },
        ],
    },
    {
        "path": ["资产池基本情况"],
        "models": [
            {
                "name": "auto",
                "custom_models": {
                    "table_kv": "table_kv",
                },
            },
        ],
    },
    {
        "path": ["基础资产利率分布"],
        "sub_primary_key": ["基础资产利率分布(%)"],
        "models": [
            {
                "name": "table_row",
                "multi": True,
                "location_threshold": 0.05,
                "neglect_header_regs": R_IGNORE_HEADER_PATTERNS,
                "基础资产利率分布(%)": {
                    "feature_white_list": [r"__regex__^(利|费)率$"],
                },
                "未偿余额（万元）": {
                    "feature_white_list": [r"__regex__(本金|未偿|贷款)(本金|余额|规模)"],
                },
                "占比(%）": {
                    "feature_white_list": [
                        r"__regex__^占比$",
                        r"__regex__(规模|余额)占比",
                    ],
                },
            }
        ],
    },
    {
        "path": ["基础资产剩余期限分布"],
        "sub_primary_key": ["基础资产剩余期限分布（月）"],
        "models": [
            {
                "name": "extra_date_info",
                "multi": True,
                "location_threshold": 0.05,
                "neglect_header_regs": R_IGNORE_HEADER_PATTERNS,
                "基础资产剩余期限分布（月）": {
                    "feature_white_list": [r"__regex__(合同)?剩余期限"],
                },
                "未偿余额（万元）": {
                    "feature_white_list": [r"__regex__(本金|未偿|贷款)(本金|余额|规模)"],
                },
                "占比(%）": {
                    "feature_white_list": [
                        r"__regex__^占比$",
                        r"__regex__(规模|余额)占比",
                    ],
                },
            },
        ],
    },
    {
        "path": ["基础资产账期分布"],
        "sub_primary_key": ["基础资产账期分布（月）"],
        "models": [
            {
                "name": "extra_date_info",
                "multi": True,
                "neglect_header_regs": R_IGNORE_HEADER_PATTERNS,
            }
        ],
    },
    # TODO: 以下字段标注暂缺
    # {
    #     'path': ['债务人所属地区分布'],
    # },
    # {
    #     'path': ['债务人年龄分布'],
    # },
    {
        "path": ["其他与本报告事项相关且管理人认为应当披露的信息"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "keep_parent": False,
                "match_method": "similarity",
                "break_para_pattern": [
                    r"^特[别此][报披公][露告示]",
                ],
            },
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
