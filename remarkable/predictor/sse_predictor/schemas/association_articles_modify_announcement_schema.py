"""
03 公司章程公告-关于修改公司章程的公告
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()

predictor_options.extend(
    [
        {
            "path": ["修改内容"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["是否涉及董事会改选"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
    ]
)

prophet_config = {"predictor_options": predictor_options}
