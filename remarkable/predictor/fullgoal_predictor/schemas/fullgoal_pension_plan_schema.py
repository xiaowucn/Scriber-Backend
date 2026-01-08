predictor_options = [
    {
        "path": ["配置资产"],
        "sub_primary_key": ["资产类型"],
        "models": [
            {
                "name": "pension_plan",
                "one_result_per_feature": False,
                "multi": True,
                "include_title": True,
            },
        ],
    },
]


prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
