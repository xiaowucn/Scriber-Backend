"""
111: "1613 重大资产重组终止"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()
predictor_options.extend(
    [
        {
            "path": ["终止的阶段"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["终止的原因"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["承诺事项"],
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
