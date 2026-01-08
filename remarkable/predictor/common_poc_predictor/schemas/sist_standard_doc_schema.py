"""
深圳标准研究院 深圳标准研究院_标准文件
"""

predictor_options = [
    {
        "path": ["起草单位"],
        "models": [
            # {
            #     "name": "partial_text",
            #     "multi": True,
            #     "use_answer_pattern": False,
            #     "neglect_answer_patterns": [
            #         "、|。"
            #     ]
            # },
            {
                "name": "drafting_unit",
                "multi": True,
                "use_answer_pattern": False,
                "model_alternative": False,
                "regs": [
                    r"(?P<dst>[\u4e00-\u9fa5（）()!]+)",
                ],
                "neglect_answer_patterns": [
                    # "、|。",
                    "起草单位",
                ],
            }
        ],
    },
    {
        "path": ["起草人"],
        "models": [
            {
                "name": "partial_text",
                "multi": True,
                "use_answer_pattern": False,
                "model_alternative": False,
                "regs": [
                    r"(?P<dst>[\u4e00-\u9fa5]+)",
                    r"(?P<dst>[\u4e00-\u9fa5]+)本标准为首次制定",  # 元素块解析错误的特例
                ],
                "neglect_answer_patterns": [
                    # "、|。",
                    "起草人",
                    "本标准为首次制定",
                ],
            }
        ],
    },
    {
        "path": ["术语和定义"],
        "sub_primary_key": ["术语"],
        "strict_group": True,
        "models": [
            {
                "name": "terms_and_definitions",
            }
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
