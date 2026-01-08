"""
公募招募说明书
"""

predictor_options = [
    {
        "path": ["基金托管人"],
        "models": [
            {
                "name": "fixed_position",
                "pages": [0],
                "regs": [r"基金托管人.(?P<dst>.*)"],
            }
        ],
    },
    {
        "path": ["管理费率"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["基金份额的自动升降级"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": [r"申购与赎回的数量限制", r"类基金份额单笔申购份额为1份或1份的整数倍。"],
                "break_para_pattern": [
                    r"^[(（]?[一二三四五六七八九十]+[）)、.]?",
                ],
            },
            {
                "name": "syllabus_based",
                "include_title": False,
                "inject_syllabus_features": [r"__regex__基金份额分级$"],
                "only_inject_features": True,
                "paragraph_model": "middle_paras",
                "para_config": {
                    "include_bottom_anchor": True,
                    "top_anchor_regs": [r".*[ABC]类基金份额(自动)?[升降]级为[ABC]类基金份额"],
                    "bottom_anchor_regs": [r".*[ABC]类基金份额(自动)?[升降]级为[ABC]类基金份额"],
                },
            },
            {
                "name": "partial_text",
                "regs": [
                    r".*[ABC]类基金份额(自动)?[升降]级为[ABC]类基金份额.*[ABC]类基金份额(自动)?[升降]级为[ABC]类基金份额"
                ],
            },
        ],
    },
    {
        "path": ["基金份额自动升降级"],
        "sub_primary_key": ["条件"],
        "divide_answers": True,
        "models": [
            {
                "name": "fund_share",
                "depends": ["基金份额的自动升降级"],
                "multi": True,
                "multi_elements": True,
                "column_from_multi_elements": True,
                "model_alternative": True,
                "merge_char_result": False,
                "regs": {
                    "条件": [
                        r"(?P<dst>若(本基金)?[ABC]类基金份额持有人在?单个基金账户.*?保留的基金份额.*?(时|份）))",
                        r"(?P<dst>本基金份额持有人单个基金账户.*?基金份额.*?(时|份）))",
                        r"(?P<dst>当?投资[者人]在(所有)?销售机构保留的[ABC]级基金份额.*(时|份）))",
                        # r"(?P<dst>基金份额分[类级]后，在基金存续期内的任何一个开放日.*?基金账户内?保留的.*?基金份额.*?(时|份）))",
                        r"(?P<dst>相应的,当[低高]于.*?(时|份）))",
                    ],
                    "结果": [
                        r"(时|份）).(?P<dst>本基金.*?机构自动将.*?([ABC][类级]|可用)基金份额[升降]级为[ABC][类级]基金份额)"
                    ],
                },
            },
        ],
    },
]


prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
