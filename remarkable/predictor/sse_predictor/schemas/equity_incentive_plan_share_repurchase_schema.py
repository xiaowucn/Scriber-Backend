"""
schema id: 81
schema name: "2106 股权激励计划股份回购开始"
"""

from remarkable.predictor.sse_predictor.predictor_config import SPECIAL_ATTR_PATTERNS, filter_predictors

predictor_options = filter_predictors(exclude=("公司全称", "公告时间"))

predictor_options.extend(
    [
        {
            "path": ["公司全称"],
            "models": [
                {"name": "fixed_position", "positions": (0,), "regs": [r"(?P<dst>.*?公司)"], "use_crude_answer": True}
            ],
        },
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
            "path": ["拟回购股份的用途"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["拟回购股份数量上限"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["拟回购股份数量上限单位"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["拟回购股份数量下限"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["拟回购股份数量下限单位"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["拟回购股份占公司总股本的比例上限"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["拟回购股份占公司总股本的比例下限"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["拟回购资金总额上限"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["拟回购资金总额上限单位"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["拟回购资金总额下限"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["拟回购资金总额下限单位"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["回购价格或价格区间上限"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["回购价格或价格区间上限"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["回购价格或价格区间上限单位"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["回购价格或价格区间下限"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["回购价格或价格区间下限单位"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["回购方式"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["回购期限", "起始日"],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [rf"{SPECIAL_ATTR_PATTERNS['date'][0]}[至到]"],
                },
            ],
        },
        {
            "path": ["回购期限", "到期日"],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [rf"[至到]{SPECIAL_ATTR_PATTERNS['date'][0]}"],
                },
            ],
        },
        {
            "path": ["回购资金来源"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["回购方案的实施情况"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["本次回购股份的目的"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["已实际回购股份数量"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["已实际回购股份数量单位"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["已实际回购股份数量占公司总股本的比例"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["已实际回购股份数量占回购规模上限的比例"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["已实际回购股份数量占回购规模下限的比例"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": [
                "可能导致特别表决权比例提高的，采集公司采取的将相应数量特别表决权股份转换为普通股份等具体措施内容，保证特别表决权比例不高于原有水平"
            ],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["购买的最高价"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["购买的最高价单位"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["购买的最低价"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["购买的最低价单位"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["购买支付的金额"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["购买支付的金额单位"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
