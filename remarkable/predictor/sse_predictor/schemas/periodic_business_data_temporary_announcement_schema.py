"""
schema id: 38
schema name: "02 定期经营数据-临时公告"
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
            "path": ["会计年度"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": (0, 1, 2, 3, 4, 5),
                    "regs": [
                        r"(?P<dst>\d+.*?季度)",
                        r"(?P<dst>\d+年.*?月)",
                    ],
                }
            ],
        },
        {
            "path": ["主要产品"],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                },
                {
                    "name": "partial_text",
                },
            ],
            "sub_primary_key": ["名称"],
            "unit_depend": {
                "销售收入": "销售收入单位",
                "销量": "销量单位",
                "产量": "产量单位",
                "平均售价": "平均售价单位",
            },
            "strict_group": True,
        },
        {
            "path": ["原材料"],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                },
                {
                    "name": "partial_text",
                },
            ],
            "sub_primary_key": ["名称"],
            "unit_depend": {"平均采购单价": "平均采购单价单位"},
        },
        {
            "path": ["销售收入（按地区）"],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                },
            ],
            "sub_primary_key": ["区域"],
            "unit_depend": {"金额": "单位"},
        },
        {
            "path": ["销售收入（按渠道）"],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                },
            ],
            "sub_primary_key": ["渠道"],
            "unit_depend": {"金额": "单位"},
        },
    ]
)

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
