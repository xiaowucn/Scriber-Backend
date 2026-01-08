# -*- coding: utf-8 -*-

"""
Mole id: 97
Mole name: 2130 员工持股计划草案
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()


predictor_options.extend(
    [
        {
            "path": ["计划参与对象"],
            "models": [
                {"name": "partial_text", "regs": []},
                {
                    "name": "para_match",
                    "paragraph_pattern": r"本激励计划.*需要激励的人员",
                },
            ],
        },
        {
            "path": ["资金来源及金额", "资金来源"],
            "models": [
                {"name": "partial_text", "regs": []},
            ],
        },
        {
            "path": ["资金来源及金额", "资金金额", "金额"],
            "models": [
                {"name": "partial_text", "regs": []},
            ],
        },
        {
            "path": ["资金来源及金额", "资金金额", "单位"],
            "models": [
                {"name": "partial_text", "regs": []},
            ],
        },
        {
            "path": ["股份来源"],
            "models": [
                {"name": "partial_text", "regs": [r"(?P<dst>股票来源为.*?公司.*?普通股股?票?)"]},
            ],
        },
        {
            "path": ["持股计划存续期"],
            "models": [
                {"name": "partial_text", "regs": []},
            ],
        },
    ]
)

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
