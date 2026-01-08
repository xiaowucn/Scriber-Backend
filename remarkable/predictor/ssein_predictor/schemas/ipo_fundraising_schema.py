"""募集资金"""

predictor_options = [
    {
        "path": ["募集资金运用"],
        "sub_primary_key": ["募投项目名称"],
        "models": [
            {
                "name": "table_row",
                "multi": True,
                "multi_elements": True,
                "filter_serial_number": True,
            },
        ],
        "location_threshold": 0.2,
    },
    {
        "path": ["募集资金明细"],
        "sub_primary_key": ["募投项目名称", "明细项目名称"],
        "models": [
            {
                "name": "syllabus_based",
                "multi_elements": True,
                "table_model": "table_row",
                "table_config": {
                    "multi": True,
                    # "multi_elements": True,
                    # 'neglect_patterns': [
                    #     r'^/$',
                    # ],
                    # 'neglect_title_patterns': [r'股份.*?变动|领取薪酬|领取津贴|持有公司股份|对外投资情况|亲属直接|亲属持股|占利润总额的比重|股权激励计划|股份转让'],
                },
                # 'syllabus_level': 2,
            },
        ],
        "location_threshold": 0.2,
    },
]


prophet_config = {"depends": {}, "predictor_options": predictor_options}
