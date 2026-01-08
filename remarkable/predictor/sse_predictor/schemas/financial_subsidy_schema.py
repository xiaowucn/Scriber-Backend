"""
120: "2619 获得财政补贴"
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
                "（二级）",
            ],
            "sub_primary_key": ["收到补助的时间", "收到补助的金额"],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                    "neglect_patterns": [
                        r"[合总小]并?计",
                    ],
                },
                {
                    "name": "partial_text",
                    "multi": True,
                },
            ],
            "unit_depend": {"收到补助的金额": "收到补助的金额单位"},
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
