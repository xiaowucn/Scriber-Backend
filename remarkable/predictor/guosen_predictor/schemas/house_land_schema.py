"""
房屋土地证
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
        "path": ["权利人"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(0, 20)),
                "regs": [r"^权利人(?P<dst>.+)"],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"权利人"],
                "content_pattern": [
                    r"权利人(?P<dst>.+)",
                ],
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
                "regs": [r"^共有权情况(?P<dst>.+)"],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"共有权情况"],
                "content_pattern": [
                    r"共有权情况(?P<dst>.+)",
                ],
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
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"房屋坐落"],
                "content_pattern": [
                    r"房屋坐落(?P<dst>.+)",
                ],
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
        "path": ["使用权类型"],
        "models": [
            {
                "name": "table_kv",
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"使用权类型"],
                "content_pattern": [
                    r"使用权类型(?P<dst>.+)",
                ],
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
        "path": ["批准土地用途"],
        "models": [
            {
                "name": "table_kv",
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"批准土地用途"],
                "content_pattern": [
                    r"批准土地用途(?P<dst>.+)",
                ],
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
        "path": ["批准使用期限"],
        "models": [
            {
                "name": "table_kv",
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"批准使用期限"],
                "content_pattern": [
                    r"批准使用期限(?P<dst>.+)",
                ],
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
        "path": ["总用地面积"],
        "models": [
            {
                "name": "table_kv",
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"总用地面积"],
                "content_pattern": [
                    r"总用地面积(?P<dst>.+)",
                ],
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
]


prophet_config = {"depends": {}, "predictor_options": predictor_options}
