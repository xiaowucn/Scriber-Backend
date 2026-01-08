"""
2: 上交所合规检查POC2
"""

from remarkable.predictor.sse_predictor.models.top_five_customers import REPORT_PERIOD_PATTERN

TRANSACTION_NEGLECT_PATTERN = [r"[合小总]计$", r"公司名称$", r"比例|金额"]

predictor_options = [
    {
        "path": ["新增股东"],
        "models": [
            {
                "name": "holder_info",
                "keep_parent": True,
                "multi": True,
                "aim_chapter_pattern": "股东",  # 比 '新增' 效果要好
            },
        ],
        "sub_primary_key": ["名称"],
    },
    {
        "path": ["股东情况"],
        "models": [
            {
                "name": "holder_info",
                "keep_parent": True,
                "multi": True,
                "aim_chapter_pattern": "股东",
            },
        ],
        "sub_primary_key": ["名称"],
    },
    {
        "path": ["董监高核（核心技术人员情况）", "核心技术人员认定情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": [r"依据$"],
                "keep_parent": True,
            },
        ],
    },
    {
        "path": ["董监高核（核心技术人员情况）", "核心技术人员认定依据"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": [r"情况$"],
                "keep_parent": True,
            },
        ],
    },
    {
        "path": ["董监高核（业务与技术）", "核心技术人员认定情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": [r"依据$"],
                "keep_parent": True,
            },
        ],
    },
    {
        "path": ["董监高核（业务与技术）", "核心技术人员认定依据"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": [r"情况$"],
                "keep_parent": True,
            },
        ],
    },
    {
        "path": ["业务与技术-前五客户"],
        "sub_primary_key": ["报告期", "名称"],
        "element_candidate_count": 25,
        "strict_group": True,
        "models": [
            {
                "name": "top_five_customers",
                "neglect_patterns": [r"[合总小]计"],
                "multi": True,
                "multi_elements": True,
                "title_patterns": [
                    r"前五|分大类|主要客户销售情况",
                ]
                + REPORT_PERIOD_PATTERN,
                "title_neglect_patterns": [
                    r"供应商|招标|公司主要客户情况如下|销售退回|获取订单",
                ],
            },
        ],
        "location_threshold": 0.1,
    },
    {
        "path": ["业务与技术-前五客户注释"],
        "sub_primary_key": ["注释内容"],
        "element_candidate_count": 15,
        "models": [
            {
                "name": "top_five_customers_notes",
                "threshold": 0.036,
                "aim_types": ["PARAGRAPH"],
                "multi": True,
                "patterns": [r"^备?注?释?\s?\d{0,}\s?[:：、]"],
            }
        ],
    },
    {
        "path": ["业务与技术-前五客户段落"],
        "models": [
            {
                "name": "partial_text",
                "aim_types": ["PARAGRAPH"],
                "multi": True,
            },
            {
                "name": "score_filter",
                "threshold": 0.05,
                "aim_types": ["PARAGRAPH"],
            },
        ],
    },
    {
        "path": ["公司治理与独立性-经常性关联交易情况"],
        "sub_primary_key": ["关联交易对手"],
        "strict_group": True,
        "models": [
            {
                "name": "connected_transaction",
                "aim_types": ["TABLE"],
                "neglect_patterns": TRANSACTION_NEGLECT_PATTERN,
                "text_split_patterns": {"关联交易对手": [r"[、]"]},
                "lazy_match": True,
                "multi": True,
                "multi_elements": True,
            },
            {
                "name": "partial_text",
                "aim_types": ["PARAGRAPH"],
                "multi": True,
            },
        ],
        "location_threshold": 0.06,
    },
    {
        "path": ["公司治理与独立性-偶发性关联交易情况"],
        "sub_primary_key": ["关联交易对手"],
        "strict_group": True,
        "models": [
            {
                "name": "connected_transaction",
                "aim_types": ["TABLE"],
                "neglect_patterns": TRANSACTION_NEGLECT_PATTERN,
                "text_split_patterns": {"关联交易对手": [r"[、]"]},
                "title_neglect_patterns": ["员工购房借款"],
                # 'lazy_match': True,
                "multi": True,
                "multi_elements": True,
            },
            {
                "name": "partial_text",
                "aim_types": ["PARAGRAPH"],
                "multi": True,
            },
        ],
        "location_threshold": 0.1,
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
