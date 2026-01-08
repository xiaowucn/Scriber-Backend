"""
schema id: 132
schema name: "21 资产查封冻结公告"
"""

predictor_options = [
    {
        "path": ["分组"],
        "models": [
            {
                "name": "table_row",
                "multi": True,
                "neglect_patterns": [
                    r"[合总小]计",
                ],
            },
            {
                "name": "table_kv",
                "multi": True,
                "neglect_patterns": [
                    r"[合总小]计",
                ],
            },
            {
                "name": "partial_text",
            },
        ],
        "distinguish_shape": True,
        "sub_primary_key": ["股东名称"],
        "unit_depend": {"持股数量": "单位"},
        "group": {"lookup_strategy": "lookahead"},
    },
]


prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
