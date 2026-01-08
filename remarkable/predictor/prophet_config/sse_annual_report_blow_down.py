"""
54: "14 年报-排污"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()
predictor_options.extend(
    [
        {
            "path": ["是否属于重点排污单位"],
            "models": [
                {
                    "name": "partial_text",
                    "enum": {
                        "default": "否",
                        "patterns": [("是", [r"适用"])],
                    },
                },
            ],
        }
    ]
)

prophet_config = {
    "depends": {},
    # 'merge_schema_answers': True,
    "predictor_options": predictor_options,
}
