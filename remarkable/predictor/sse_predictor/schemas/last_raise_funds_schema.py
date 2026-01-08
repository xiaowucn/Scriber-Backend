"""
99: "0709 前次募集资金使用情况报告"
"""

from remarkable.predictor.sse_predictor.predictor_config import SPECIAL_ATTR_PATTERNS, filter_predictors

predictor_options = filter_predictors(exclude=("公告时间", "公司全称"))

predictor_options.extend(
    [
        {
            "path": ["公司全称"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(0, 5)),
                    "regs": [r"(?P<dst>.*?公司)"],
                }
            ],
        },
        {
            "path": ["公告时间"],
            "models": [{"name": "fixed_position", "regs": SPECIAL_ATTR_PATTERNS["date"], "use_crude_answer": True}],
        },
        {
            "path": [
                "募集资金净额",
            ],
            "models": [
                {"name": "partial_text", "multi_elements": True},
            ],
        },
        {
            "path": [
                "募集资金余额",
            ],
            "models": [
                {"name": "partial_text", "multi_elements": True},
            ],
        },
        {
            "path": [
                "前次募集资金和本次有什么差异",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "差异的原因和情况",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "是否存在变更",
            ],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
