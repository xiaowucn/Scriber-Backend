"""
10: "1002 澄清或说明"
todo：
    1、多组传闻+澄清
    2、传闻（澄清）没有所属章节
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()

predictor_options.extend(
    [
        {
            "path": ["（二级）", "传闻基本情况"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["（二级）", "澄清内容：真实情况"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["（二级）", "澄清内容：如传闻涉及及控制权变更或重大资产重组等事项的声明"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
