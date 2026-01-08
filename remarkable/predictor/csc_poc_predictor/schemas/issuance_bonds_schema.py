"""
中信建投 发行情况公告
"""

predictor_options = [
    {
        "path": ["实际发行总额"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["发行利率（%）"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["债券基本信息"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
