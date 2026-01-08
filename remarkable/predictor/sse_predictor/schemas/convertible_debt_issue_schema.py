"""
100: "1922 可转债发行"
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
                    "positions": (0,),
                    "regs": [r"(?P<dst>.*?公司)"],
                    "use_crude_answer": True,
                }
            ],
        },
        {
            "path": ["股权登记日"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["网上申购日"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["网下申购日"],
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
