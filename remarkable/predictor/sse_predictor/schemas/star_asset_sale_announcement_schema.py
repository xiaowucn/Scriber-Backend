"""
schema id: 23
schema name: "0402 出售资产"
TODO: 类似"10 出售资产公告"
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
            "path": ["交易事项"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["交易详情"],
            "sub_primary_key": ["出售或购买的标的名称"],
            "models": [
                {"name": "partial_text"},
            ],
        },
        {
            "path": ["交易标的情况"],
            "sub_primary_key": ["出售或购买的标的名称"],
            "models": [
                {"name": "table_row", "multi": True},
            ],
        },
        {
            "path": ["交易标的情况", "被担保人是否是关联方"],
            "sub_primary_key": ["出售或购买的标的名称"],
            "models": [
                {
                    "name": "enum_value",
                    "simple": "资产",
                },
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
