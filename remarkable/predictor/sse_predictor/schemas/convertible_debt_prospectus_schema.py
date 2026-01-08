"""
113: "1921 可转债募集说明书摘要"
"""

from remarkable.predictor.sse_predictor.predictor_config import SPECIAL_ATTR_PATTERNS, filter_predictors

predictor_options = filter_predictors(exclude=("公司全称", "公告时间"))
predictor_options.extend(
    [
        {
            "path": ["公司名称"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": (0,),
                    "regs": [r"(?P<dst>.*?公司)"],
                    "use_crude_answer": True,
                }
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
            "path": ["可转债发行的金额", "金额"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["可转债发行的金额", "单位"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["可转债发行的存续期"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["可转债发行的利率"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["可转债的利率调整机制"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["可转债的赎回条款"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["可转债的回售条款"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["可转债的转股价格调整机制（如有）"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["是否存在老股东优先配售"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["募集资金补充流动资金（补流）的说明"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["是否有担保"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["主体资信评级"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["可转债资信评级"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["初始转股价", "金额"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["初始转股价", "单位"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["可转债面值", "金额"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["可转债面值", "单位"],
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
    "predictor_options": predictor_options,
}
