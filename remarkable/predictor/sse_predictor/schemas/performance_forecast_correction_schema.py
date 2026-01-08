"""
schema id: 86
schema name: "0809 业绩预告更正"
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
            "path": ["业绩预告区间", "起始日"],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [rf"{SPECIAL_ATTR_PATTERNS['date'][0]}[至到]"],
                },
            ],
        },
        {
            "path": ["业绩预告区间", "到期日"],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [rf"[至到]{SPECIAL_ATTR_PATTERNS['date'][0]}"],
                },
            ],
        },
        {
            "path": ["更正前预告内容", "业绩预告类别"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["更正前预告内容", "本期扣非前归属于母公司的净利润"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["更正前预告内容", "本期扣非后归属于母公司的净利润"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["更正前预告内容", "本期营业收入"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["更正前预告内容", "本期净资产"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["更正前预告内容", "上年同期扣非前归属于母公司的净利润"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["更正前预告内容", "上年同期扣非后归属于母公司的净利润"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["更正前预告内容", "上年同期营业收入"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["更正前预告内容", "上年同期净资产"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["更正后预告内容", "业绩预告类别"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["更正后预告内容", "本期扣非前归属于母公司的净利润"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["更正后预告内容", "本期扣非后归属于母公司的净利润"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["更正后预告内容", "本期营业收入"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["更正后预告内容", "本期净资产"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["更正后预告内容", "上年同期扣非前归属于母公司的净利润"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["更正后预告内容", "上年同期扣非后归属于母公司的净利润"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["更正后预告内容", "上年同期营业收入"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["更正后预告内容", "上年同期净资产"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["本期业绩变化的原因"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
