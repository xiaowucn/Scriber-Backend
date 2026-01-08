"""非“小而分散”类资产"""

from remarkable.predictor.sse_predictor.predictor_config import SPECIAL_ATTR_PATTERNS

from . import R_REPORT_TITLE_PATTERNS

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
        "path": ["基本情况", "循环购买账户资金划转情况"],
        "models": [{"name": "found_trans", "keep_parent": False, "match_method": "similarity"}],
    },
    {
        "path": ["新增基础资产情况"],
        "models": [
            {
                "name": "table_kv",
            }
        ],
    },
    # TODO: 以下字段标注暂缺
    # {
    #     'path': ['新增债务人所属地区分布'],
    # },
    {
        "path": ["基础资产变化情况-循环购买前"],
        "models": [
            {
                "name": "table_kv",
            }
        ],
    },
    {
        "path": ["基础资产变化情况-循环购买后"],
        "models": [
            {
                "name": "table_kv",
            }
        ],
    },
    {
        "path": ["资产池基本情况"],
        "models": [
            {
                "name": "table_kv",
            }
        ],
    },
    {
        "path": ["债务人所在行业分布"],
        "sub_primary_key": ["债务人所在行业"],
        "models": [
            {
                "name": "table_row",
                "multi": True,
                "neglect_patterns": [
                    r"[合总小共]计$",
                ],
            }
        ],
    },
    # TODO: 以下字段标注暂缺
    # {
    #     'path': ['债务人所属地区分布'],
    # },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
