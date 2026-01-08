"""
68: "1213 因股东披露权益变动报告书或收购报告书的提示"
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
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["二级", "股东名称"],
            "models": [
                {"name": "partial_text", "regs": [r"收购人姓名[:：]?\s?(?P<dst>.*)[（(]"]},
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
                },
            ],
        },
        {
            "path": ["二级", "变动前股份数量单位"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["二级", "变动前股份占比"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["二级", "变动后股份数量"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["二级", "变动后股份数量单位"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["二级", "变动后股份数量占比"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["变动是否使公司控股股东及实际控制人发生变化"],
            "models": [
                {
                    "name": "partial_text",
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
