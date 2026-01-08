"""
31: "2802 实施退市风险警示"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()

predictor_options.extend(
    [
        {
            "path": ["（二级）", "实施退市风险警示的起始日"],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [
                        r"(?P<dst>2.*日)被实施退市风险警示",
                        r"退市风险警示的起始日[:：：].{0,4}(?P<dst>2.*日)",
                        r"(?P<dst>公司股票被继续实施退市风险警示)",
                    ],
                },
            ],
        },
        {
            "path": ["（二级）", "实施退市风险警示后的股票简称"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "实施退市风险警示后的扩位股票简称"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "实施退市风险警示后的股票代码"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "实施退市风险警示的适用情形"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
