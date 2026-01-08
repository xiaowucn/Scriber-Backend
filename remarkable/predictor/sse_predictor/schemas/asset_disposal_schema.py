"""
28: "01 资产处置公告"
"""

from remarkable.predictor.sse_predictor.predictor_config import SPECIAL_ATTR_PATTERNS, filter_predictors

predictor_options = filter_predictors(exclude=("公告时间"))
predictor_options.extend(
    [
        {
            "path": ["公告时间"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(-10, 0))[::-1],
                    "regs": SPECIAL_ATTR_PATTERNS["anno_time"],
                }
            ],
        },
        {
            "path": [
                "（二级）",
            ],
            "sub_primary_key": ["处置资产"],
        },
        {
            "path": ["（二级）", "是否构成重大资产重组"],
            "models": [
                {
                    "name": "partial_text",
                    "multi": True,
                },
            ],
            "share_column": True,
        },
        {
            "path": ["（二级）", "处置资产"],
            "models": [
                {"name": "partial_text", "multi_elements": True},
            ],
        },
        {
            "path": ["（二级）", "处置资产说明"],
            "models": [
                {
                    "name": "syllabus_elt",
                    "neglect_patterns": [
                        r"重[要大]内容提示",
                    ],
                },
            ],
            "group": {"lookup_strategy": "lookahead"},
        },
        {
            "path": ["（二级）", "资产价值"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
            "group": {"lookup_strategy": "lookahead", "range_num": 10},
        },
        {
            "path": ["（二级）", "处置日期"],
            "models": [
                {"name": "partial_text"},
            ],
            "share_column": True,
        },
    ]
)

prophet_config = {
    "depends": {},
    # 'merge_schema_answers': True,
    "predictor_options": predictor_options,
}
