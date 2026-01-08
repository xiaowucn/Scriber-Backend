"""
82 : "1809 回购实施结果暨股份变动"
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
            "path": [
                "实际回购股份数量",
            ],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [
                        r"回购.*?股份(?P<dst>[\d,\s]*股)",
                    ],
                },
            ],
        },
        {
            "path": [
                "实际回购股份数量单位",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "实际回购股份数量占公司比例",
            ],
            "models": [
                {"name": "partial_text", "regs": [r"回购.*?股份占公司总股本的?(?P<dst>[\s\d\.]*%)"]},
            ],
        },
        {
            "path": [
                "回购价格最高价",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "回购价格最高价单位",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "回购价格最低价",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "回购价格最低价单位",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "回购均价",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "回购均价单位",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "使用资金总额",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "使用资金总额单位",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "本次股份回购方案的实施对公司的影响",
            ],
            "models": [
                {
                    "name": "para_match",
                    "paragraph_pattern": r"本次(股份)?回购.*?上市(公司)?(地位|条件)",
                },
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "回购股份的用途",
            ],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [r"(?P<dst>公司.*?股权激励计划)", r"维护公司价值及股东权益所必需"],
                },
            ],
        },
        {
            "path": [
                "股份用于注销的实际注销的股数",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "股份用于注销的实际注销的股数单位",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["计划与实际执行情况对比", "是否有差异"],
            "models": [
                {
                    "name": "para_match",
                    "paragraph_pattern": r"(回购(方案实际执行|实施)情况|实际执行情况).*?不?(存在差异|符合)",
                },
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["计划与实际执行情况对比", "差异原因"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["计划与实际执行情况对比", "差异情况"],
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
