"""资管合同要素"""

predictor_options = [
    {
        "path": ["产品基本信息"],
        "models": [
            {
                "name": "partial_text",
                "multi_elements": True,
            },
        ],
        "location_threshold": 0.2,
    },
    {
        "path": ["管理人"],
        "models": [
            {
                "name": "partial_text",
                "multi_elements": True,
            },
        ],
        "location_threshold": 0.2,
    },
    {
        "path": ["关联机构"],
        "models": [
            {
                "name": "partial_text",
                "multi_elements": True,
            },
        ],
        "location_threshold": 0.2,
    },
    {
        "path": ["产品募集与开放"],
        "models": [
            {
                "name": "partial_text",
                "multi_elements": True,
            },
        ],
        "location_threshold": 0.2,
    },
    {
        "path": ["产品投资情况"],
        "models": [
            {"name": "syllabus_elt_v2", "keep_parent": True, "match_method": "similarity"},
        ],
    },
    {
        "path": ["产品费用及收益"],
        "models": [
            {
                "name": "partial_text",
                "multi_elements": True,
            },
        ],
        "location_threshold": 0.2,
    },
]


prophet_config = {"depends": {}, "predictor_options": predictor_options}
