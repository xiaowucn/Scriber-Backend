"""董监高"""

predictor_options = [
    {
        "path": ["董监高持股"],
        "sub_primary_key": ["姓名"],
        "models": [
            {
                "name": "table_row",
                "multi": True,
                "multi_elements": True,
            },
        ],
        "location_threshold": 0.2,
    }
]


prophet_config = {"depends": {}, "predictor_options": predictor_options}
