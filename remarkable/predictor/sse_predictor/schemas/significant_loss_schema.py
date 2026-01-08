# -*- coding: utf-8 -*-

"""
Mole id: 129
Mole name: 2601 重大亏损或重大损失
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()


predictor_options.extend(
    [
        {
            "path": ["对当年利润影响数"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["出现重大亏损或重大损失的原因"],
            "models": [
                {
                    "name": "partial_text",
                    "multi": True,
                },
            ],
        },
        {
            "path": ["金额"],
            "models": [
                {
                    "name": "partial_text",
                    "multi": True,
                },
            ],
        },
        {
            "path": ["对公司生产经营的影响"],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [r"(?P<dst>预计.*?出现亏损.*?净利润.*)"],
                    "multi": True,
                },
            ],
        },
        {
            "path": ["后续扭亏措施"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
                {
                    "name": "partial_text",
                    "multi": True,
                },
            ],
        },
    ]
)

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
