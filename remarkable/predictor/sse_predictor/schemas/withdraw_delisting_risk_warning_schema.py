"""
126: "2806 撤销退市风险警示"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors(exclude=("公司全称",))

predictor_options.extend(
    [
        {
            "path": ["公司全称"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(0, 5)),
                    "regs": [r"(?P<dst>.*?公司)"],
                }
            ],
        },
        {
            "path": [
                "撤销退市风险警示的起始日",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "撤销退市风险警示后的股票简称",
            ],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [
                        r'简称.*?[“"].*?[”"]变更.*?[“"](?P<dst>.*?)[”"]',
                    ],
                },
            ],
        },
        {
            "path": [
                "撤销退市风险警示后的扩位股票简称",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "撤销退市风险警示后的股票代码",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "撤销退市风险警示的适用情形",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
