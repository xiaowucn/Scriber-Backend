"""
中信-发行结果公告
"""

predictor_options = [
    {
        "path": ["本期最终发行规模（单品种）"],
        "models": [
            {
                "name": "issuing_scale_single",
            },
        ],
    },
    {
        "path": ["票面利率（单品种）"],
        "models": [
            {
                "name": "issuing_scale_single",
            },
        ],
    },
    {
        "path": ["多品种情况"],
        "sub_primary_key": ["债券品种"],
        "models": [
            {
                "name": "issuing_scale_multi",
                "group_by_position_on": "债券品种",
                "multi": True,
                "multi_elements": True,
                "merge_char_result": False,
                "本期最终发行规模": {"regs": [r"品种[一二三四五六七八九].*?发行规模为?(?P<dst>[\d.,]+)"]},
                "票面利率": {"regs": [r"品种[一二三四五六七八九].*?票面利率[为:：]?(?P<dst>[\d.,]+[%％])"]},
                "债券品种": {"regs": [r"(?P<dst>品种[一二三四五六七八九])"]},
                "model_alternative": True,
            },
        ],
    },
]


prophet_config = {"depends": {}, "predictor_options": predictor_options}
