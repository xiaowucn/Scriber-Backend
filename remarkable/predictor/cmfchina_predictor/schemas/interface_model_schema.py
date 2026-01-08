predictor_options = [
    {
        "path": ["interface_model"],
        "fake_leaf": True,
        "models": [
            {
                "name": "interface_model",
            }
        ],
    }
]
prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
