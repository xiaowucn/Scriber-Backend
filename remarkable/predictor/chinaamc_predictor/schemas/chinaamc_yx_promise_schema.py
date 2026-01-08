"""承诺函V1"""

predictor_options = [
    {
        "path": ["001基金名称"],
        "models": [
            {
                "name": "auto",
                "use_answer_pattern": False,
                "multi_elements": True,
                "model_alternative": True,
                "elements_nearby": {
                    "regs": [r"中国证券监督管理委员会[:：]$"],
                    "amount": 2,
                    "step": -1,
                },
                "order_by_index": True,
                "regs": [
                    "(?P<dst>华夏.*(投资|基金中)基金.*联接基金([(（]?[a-zA-Z]+[）)])?)",
                    "(?P<dst>华夏.*(投资|基金中)基金([(（]?[a-zA-Z]+[）)])?)",
                    "(?P<dst>华夏.*)",
                    "(?P<dst>.*)的基金经理",
                ],
                "neglect_patterns": [
                    r"华夏基金管理有限公司",
                ],
            },
        ],
    },
    {
        "path": ["002基金名称"],
        "models": [
            {
                "name": "auto",
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    "并以显著、清晰的方式揭示了投资于(?P<dst>华夏.*(投资|基金中)基金.*联接基金([(（]?[a-zA-Z]+[）)])?)",
                    "并以显著、清晰的方式揭示了投资于(?P<dst>华夏.*(投资|基金中)基金([(（]?[a-zA-Z]+[）)])?)",
                ],
            },
        ],
    },
    {
        "path": ["003基金名称"],
        "models": [
            {
                "name": "auto",
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    "司申报的?(?P<dst>华夏.*(投资|基金中)基金.*联接基金([(（]?[a-zA-Z]+[）)])?).?在募集",
                    "司申报的?(?P<dst>华夏.*(投资|基金中)基金([(（]?[a-zA-Z]+[）)])?).?在募集",
                ],
            },
        ],
    },
    {
        "path": ["004基金名称"],
        "models": [
            {
                "name": "auto",
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    "司对于(?P<dst>华夏.*(投资|基金中)基金.*联接基金([(（]?[a-zA-Z]+[）)])?)",
                    "司对于(?P<dst>华夏.*(投资|基金中)基金([(（]?[a-zA-Z]+[）)])?)",
                ],
            },
        ],
    },
    {
        "path": ["005基金名称"],
        "models": [
            {
                "name": "auto",
                "use_answer_pattern": False,
                "regs": [
                    "司申报的?(?P<dst>华夏.*(投资|基金中)基金.*联接基金([(（]?[a-zA-Z]+[）)])?).?不投资于",
                    "司申报的?(?P<dst>华夏.*(投资|基金中)基金([(（]?[a-zA-Z]+[）)])?).?不投资于",
                ],
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
