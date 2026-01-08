# -*- coding: utf-8 -*-

"""
Mole id: 95
Mole name: 2105 股权激励计划终止
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()


predictor_options.extend(
    [
        {
            "path": ["终止原因"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["是否涉及回购注销"],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [
                        r"(?P<dst>并对.*?进行回购注销.*?)[,，]",
                        r"(?P<dst>同时回购注销.*?全部限制性.*?)[,，。]",
                        r"(?P<dst>(同时|并)回购注销.*?)[,，。]",
                    ],
                },
            ],
        },
    ]
)

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
