predictor_options = [
    {
        "path": ["详情"],
        "sub_primary_key": ["股票名称", "股票代码", "资产情况"],
        "models": [
            {
                "name": "multi_group",
            }
        ],
    },
    {
        "path": ["日期"],
        "models": [
            {
                "name": "auto",
                "custom_regs": [r"日期.(?P<dst>.*日)", r"\d{4}-\d{2}-\d{2}", r"\d{4}年\d{2}月\d{2}日"],
            },
        ],
    },
]
prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
