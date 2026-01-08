# -*- coding: utf-8 -*-

"""
Mole id: 130
Mole name: 2602 发生重大债务或重大债权到期未获清偿
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()


predictor_options.extend(
    [
        {
            "path": ["债务债权的规模"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["对公司的影响"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["债务债权类型"],
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
