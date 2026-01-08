"""
schema id: 71
schema name: "2710 变更会计政策或者会计估计"
"""

from remarkable.predictor.sse_predictor.predictor_config import SPECIAL_ATTR_PATTERNS, filter_predictors

predictor_options = filter_predictors(exclude=("公司全称", "公告时间"))

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
            "path": ["公司全称"],
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
            "path": ["说明类型"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["简单说明本次会计差错、会计政策或会计估计变更的内容"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["对公司的影响"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
    ]
)

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
