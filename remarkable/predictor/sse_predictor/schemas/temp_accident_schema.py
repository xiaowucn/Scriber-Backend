"""
52: "13 临时公告-事故"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()
predictor_options.extend(
    [
        {
            "path": ["事故类别"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["是否子公司"],
            "models": [
                {
                    "name": "partial_text",
                    "enum": {
                        "default": "否",
                        "patterns": [("是", [r"(子公司|所属)"])],
                    },
                },
            ],
        },
        {
            "path": ["事故主体"],
            "models": [
                {"name": "partial_text", "multi": True},
            ],
        },
        {
            "path": ["与上市公司关系"],
            "models": [
                {"name": "partial_text", "multi": True},
            ],
        },
        {
            "path": ["事故时间"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["事故描述"],
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
