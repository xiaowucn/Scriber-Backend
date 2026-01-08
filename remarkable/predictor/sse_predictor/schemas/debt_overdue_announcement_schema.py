"""
schema id: 50
schema name: "11 债务逾期公告"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors(exclude=("公司全称",))

predictor_options.extend(
    [
        {
            "path": ["公司全称"],
            "models": [
                {"name": "fixed_position", "positions": (0,), "regs": [r"(?P<dst>.*?公司)"], "use_crude_answer": True}
            ],
        },
        {
            "path": ["（二级）"],
            "models": [
                {
                    "name": "partial_text",
                    "multi": True,
                },
                {
                    "name": "table_row",
                    "neglect_patterns": [r"[小共总合][计共]"],
                    "multi": True,
                },
            ],
            "sub_primary_key": ["借款方", "债权方", "到期日"],
            "unit_depend": {
                "逾期金额（本金）": "单位",
            },
        },
    ]
)

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
