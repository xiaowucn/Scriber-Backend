"""
房屋所有权证
"""

predictor_options = [
    {
        "path": ["权证编号"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
            {
                "name": "fixed_position",
                "positions": list(range(0, 5)),
                "regs": [r"(?P<dst>.*证.*号)"],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [
                    r"证.*号",
                    r"证.*第",
                ],
                "content_pattern": [
                    r"(?P<dst>.*证.*号)",
                    r"(?P<dst>.*证.*第\d+)",
                ],
            },
            {
                "name": "score_filter",
                "multi_elements": False,
                "threshold": 0.2,
            },
        ],
    },
    {
        "path": ["房屋所有权人"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(0, 20)),
                "regs": [r"^房地产权利人(?P<dst>.+)"],
            },
            {
                "name": "table_kv",
            },
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
            {
                "name": "score_filter",
                "multi_elements": False,
                "threshold": 0.2,
            },
        ],
    },
    {
        "path": ["共有情况"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(0, 20)),
                "regs": [r"^共有情况(?P<dst>.+)"],
            },
            {
                "name": "table_kv",
            },
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
            {
                "name": "score_filter",
                "multi_elements": False,
                "threshold": 0.2,
            },
        ],
    },
    {
        "path": ["房屋坐落"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(0, 20)),
                "regs": [r"^房屋坐落(?P<dst>.+)"],
            },
            {
                "name": "table_kv",
            },
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
            {
                "name": "score_filter",
                "multi_elements": False,
                "threshold": 0.2,
            },
        ],
    },
    {
        "path": ["房屋（权属）性质"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(0, 20)),
                "regs": [r"^房屋.*?性质(?P<dst>.+)"],
            },
            {
                "name": "table_kv",
            },
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
            {
                "name": "score_filter",
                "multi_elements": False,
                "threshold": 0.2,
            },
        ],
    },
    {
        "path": ["规划用途"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(0, 20)),
                "regs": [r"^规划用途(?P<dst>.+)"],
            },
            {
                "name": "table_kv",
            },
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
            {
                "name": "score_filter",
                "multi_elements": False,
                "threshold": 0.2,
            },
        ],
    },
    {
        "path": ["房屋状况"],
        "models": [
            {
                "name": "table_kv",
            },
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
            {
                "name": "score_filter",
                "multi_elements": False,
                "threshold": 0.2,
            },
        ],
    },
    {
        "path": ["使用年限"],
        "models": [
            {
                "name": "table_kv",
            },
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
            {
                "name": "score_filter",
                "multi_elements": False,
                "threshold": 0.2,
            },
        ],
    },
    {
        "path": ["附记"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
]


prophet_config = {"depends": {}, "predictor_options": predictor_options}
