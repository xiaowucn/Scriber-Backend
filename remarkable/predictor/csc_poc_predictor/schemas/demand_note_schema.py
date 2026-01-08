"""中信建投 缴款通知书POC"""

predictor_options = [
    {
        "path": ["缴款价位-中标量"],
        "sub_primary_key": ["缴款价位", "中标量"],
        "models": [
            {
                "name": "table_row",
                "multi": True,
                "neglect_patterns": [
                    r"[合总小]并?计",
                    r"-",
                    r"中标价位|中标额",
                    r"制表时间|中标量",
                    r"缴款金额",
                ],
                "neglect_header_regs": [
                    r"[合总小]并?计",
                    r"固定承销额",
                    r"缴款金额",
                ],
                "缴款价位": {
                    "feature_white_list": [r"__regex__中标价位__regex__.*?公司"],
                },
                "中标量": {
                    "feature_white_list": [r"__regex__中标量__regex__.*?公司"],
                },
            },
        ],
    },
    {
        "path": ["中标量（合计）"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["缴款金额（合计）"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
