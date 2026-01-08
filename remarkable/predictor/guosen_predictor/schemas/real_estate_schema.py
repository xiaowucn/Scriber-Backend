"""
不动产权证
"""

predictor_options = [
    {
        "path": ["权证编号"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>.*不动产权第.*号)",
                    r"(?P<dst>.*不动产权第\d+)",
                ],
            },
            {
                "name": "fixed_position",
                "positions": list(range(0, 5)),
                "regs": [
                    r"(?P<dst>.*不动产权第.*号)",
                    r"(?P<dst>.*不动产权第\d+)",
                ],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"不动产权第"],
                "content_pattern": [
                    r"(?P<dst>.*不动产权第.*号)",
                    r"(?P<dst>.*不动产权第\d+)",
                ],
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
                "regs": [
                    r"(?P<dst>单独所有)",
                    r"^共有情况(?P<dst>.+)",
                ],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"共有情况"],
                "content_pattern": [
                    r"(?P<dst>单独所有)",
                    r"共有情况(?P<dst>.+)",
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
        "path": ["坐落"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(0, 20)),
                "regs": [r"^坐落(?P<dst>.+)"],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"坐落"],
                "content_pattern": [
                    r"坐落(?P<dst>.+)",
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
        "path": ["不动产单元号"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(0, 20)),
                "regs": [r"^不动产单元号(?P<dst>.+)"],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"不动产单元号"],
                "content_pattern": [
                    r"不动产单元号(?P<dst>.+)",
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
        "path": ["权利类型"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(0, 20)),
                "regs": [r"^权利类型(?P<dst>.+)"],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"权利类型"],
                "content_pattern": [
                    r"权利类型(?P<dst>.+)",
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
        "path": ["权利性质"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(0, 20)),
                "regs": [r"^权利性质(?P<dst>.+)"],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"权利性质"],
                "content_pattern": [
                    r"权利性质(?P<dst>.+)",
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
        "path": ["用途"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(0, 20)),
                "regs": [r"^用途(?P<dst>.+)"],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"用途"],
                "content_pattern": [
                    r"用途(?P<dst>.+)",
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
        "path": ["面积"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(0, 20)),
                "regs": [r"^面积(?P<dst>.+)"],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"面积"],
                "content_pattern": [
                    r"面积(?P<dst>.+)",
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
        "path": ["使用期限"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(0, 20)),
                "regs": [r"^使用期限(?P<dst>.+)"],
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"使用期限"],
                "content_pattern": [
                    r"使用期限(?P<dst>.+)",
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
        "path": ["权利其他状况"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"权利其他状况"],
                "content_pattern": [
                    r"权利其他状况(?P<dst>.+)",
                ],
            },
            {
                "name": "table_kv",
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
