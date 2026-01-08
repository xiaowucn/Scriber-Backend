"""
67: "1214 控股股东或实际控制人发生变动的提示"
"""

from remarkable.predictor.sse_predictor.predictor_config import SPECIAL_ATTR_PATTERNS, filter_predictors

predictor_options = filter_predictors()

predictor_options.extend(
    [
        {
            "path": ["公告日期"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(-10, 0))[::-1],
                    "regs": SPECIAL_ATTR_PATTERNS["date"],
                }
            ],
        },
        {
            "path": ["增持或减持"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["是否触及要约收购"],
            "models": [
                {"name": "partial_text", "regs": [r"(?P<dst>触及要约收购.*)", r"(?P<dst>免于向.*豁免要约收购)"]},
            ],
        },
        {
            "path": ["二级"],
            "sub_primary_key": ["股东名称"],
        },
        {
            "path": ["二级", "股东名称"],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                    "neglect_patterns": [
                        r"[合总小]并?计",
                    ],
                },
                {
                    "name": "partial_text",
                    "regs": [
                        r"，(?P<dst>.{2,3})先生",
                        r"公司控股股东(?P<dst>.*?)[(（]",
                        r"(?P<dst>.*?)[(（].*于近日接到",
                    ],
                    "multi": True,
                },
                {
                    "name": "table_kv",
                },
            ],
        },
        {
            "path": ["二级", "变动前股份数量"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                    "multi": True,
                    "neglect_patterns": [
                        r"[合总小]并?计",
                    ],
                },
            ],
            "sub_primary_key": ["股东名称"],
        },
        {
            "path": ["二级", "变动前股份数量单位"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                    "multi": True,
                    "neglect_patterns": [
                        r"[合总小]并?计",
                    ],
                },
            ],
            "sub_primary_key": ["股东名称"],
        },
        {
            "path": ["二级", "变动前股份占比"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                    "multi": True,
                    "neglect_patterns": [
                        r"[合总小]并?计",
                    ],
                },
            ],
            "sub_primary_key": ["股东名称"],
        },
        {
            "path": ["二级", "变动后股份数量"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                    "multi": True,
                    "neglect_patterns": [
                        r"[合总小]并?计",
                    ],
                },
            ],
            "sub_primary_key": ["股东名称"],
        },
        {
            "path": ["二级", "变动后股份数量单位"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                    "multi": True,
                    "neglect_patterns": [
                        r"[合总小]并?计",
                    ],
                },
            ],
            "sub_primary_key": ["股东名称"],
        },
        {
            "path": ["二级", "变动后股份数量占比"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                    "multi": True,
                    "neglect_patterns": [
                        r"[合总小]并?计",
                    ],
                },
            ],
            "sub_primary_key": ["股东名称"],
        },
        {
            "path": ["变动是否使公司控股股东及实际控制人发生变化"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "para_match",
                    "paragraph_pattern": r"(?P<dst>实际控制人.*变更)",
                },
            ],
        },
    ]
)

prophet_config = {
    "depends": {},
    # 'merge_schema_answers': True,
    "predictor_options": predictor_options,
}
