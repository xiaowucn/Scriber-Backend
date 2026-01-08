"""
schema id: 51
schema name: "12 境内会计师事务所报酬"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors(exclude=("公司全称",))

predictor_options.extend(
    [
        {
            "path": ["公司全称"],
            "models": [
                {"name": "fixed_position", "positions": (0,), "regs": [r"(?P<dst>.*公司)"], "use_crude_answer": True}
            ],
        },
        {
            "path": [
                "（二级）",
            ],
            "models": [
                {
                    "name": "table_kv",
                }
            ],
        },
    ]
)

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
