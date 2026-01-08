"""
29: "0204 董事会审议变更证券简称"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()

predictor_options.extend(
    [
        {
            "path": ["（二级）", "变更前的简称"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(0, 3)),
                    "regs": [
                        r"(?<=简称[:：])(?P<dst>.*?)(?=\s?(公告|证券|股票|编[号码]))",
                        r"简称[:：](?P<dst>.*)",
                    ],
                }
            ],
        },
        {
            "path": ["（二级）", "变更后的简称"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "变更前的扩位简称"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "变更后的扩位简称"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "变更原因"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
