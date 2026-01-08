"""
72: "1801 回购方案"
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
            "path": ["公告类型"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
            "sub_primary_key": ["拟回购股份的用途"],
        },
        {
            "path": ["（二级）", "拟回购股份的用途"],
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
            "path": ["（二级）", "拟回购股份数量上限"],
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
            "path": ["（二级）", "拟回购股份数量上限单位"],
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
            "path": ["（二级）", "拟回购股份数量下限"],
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
            "path": ["（二级）", "拟回购股份数量下限单位"],
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
            "path": ["（二级）", "拟回购股份占公司总股本的比例上限"],
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
            "path": ["（二级）", "拟回购股份占公司总股本的比例下限"],
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
            "path": ["（二级）", "拟回购资金总额上限"],
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
            "path": ["（二级）", "拟回购资金总额上限单位"],
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
            "path": ["（二级）", "拟回购资金总额下限"],
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
            "path": ["（二级）", "拟回购资金总额下限单位"],
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
            "path": ["回购价格或价格上限"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["回购价格或价格上限单位"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["回购价格或价格下限"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["回购价格或价格下限单位"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["回购方式"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["回购期限", "起始日"],
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
            "path": ["回购期限", "到期日"],
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
            "path": ["回购资金来源"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "para_match",
                    "paragraph_pattern": r"公司自有资金|自筹资金",
                },
            ],
        },
        {
            "path": ["回购方案的实施情况"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["本次回购股份的目的"],
            "models": [
                {
                    "name": "para_match",
                    "paragraph_pattern": r"回购.*(股权激励|持股计划|注销)",
                },
            ],
        },
        {
            "path": [
                "可能导致特别表决权比例提高的，采集公司采取的将相应数量特别表决权股份转换为普通股份等具体措施内容，保证特别表决权比例不高于原有水平"
            ],
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
