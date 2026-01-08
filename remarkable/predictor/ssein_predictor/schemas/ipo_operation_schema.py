"""经营模式"""

predictor_options = [
    {
        "path": ["公司主要经营模式"],
        "sub_primary_key": [
            "标题",
        ],
        "models": [
            {
                "name": "chapter",
                "title_column": "标题",
                "content_column": "正文",
                "multi": True,
            },
        ],
    },
    # {
    #     'path': ['公司主要经营模式', '标题'],
    #     'models': [
    #         {
    #             'name': 'score_filter',
    #             'threshold': 0.2,
    #         },
    #     ],
    # },
    # {
    #     'path': ['公司主要经营模式', '正文'],
    #     'models': [
    #         {
    #             'name': 'score_filter',
    #             'threshold': 0.2,
    #         },
    #     ],
    # },
]


prophet_config = {"depends": {}, "predictor_options": predictor_options}
