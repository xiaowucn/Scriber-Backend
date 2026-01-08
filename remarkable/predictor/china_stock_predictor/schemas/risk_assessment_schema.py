"""银河证券 30 风险评估协议"""

table_kv_black_feature = [r"终止情形"]
table_kv_white_feature = ["投资范围与投资比例"]

predictor_options = [
    {
        "path": ["投资范围"],
        "models": [
            {
                "name": "table_kv_expand",
                "use_complete_table": True,
                "table_regarded_as_paras": True,
                "top_anchor_regs": [
                    r"^.\d.本信托计划主要投资于",
                ],
                "include_bottom_anchor": True,
                "bottom_anchor_regs": [
                    r"本信托计划主要投资由.*担任管理人.*担任托管人的",
                ],
                "bottom_anchor_content_regs": [r"(?P<content>\d.*类*金融产品.*)本信托计划主要投资由.*担任管理人"],
            },
            {
                "name": "table_kv_expand",
                "feature_black_list": table_kv_black_feature,
                "feature_white_list": table_kv_white_feature,
                "use_complete_table": True,
                "top_anchor_regs": [r"本信托计划的投资范围", r"本信托计划可根据资金管理的需求，投资于现金"],
                "bottom_anchor_regs": [
                    r"^本.*的?投资(组合)?比例",
                    r"基金的投资策略",
                    r"本信托计划的投资策略",
                    r"本产品将根据宏观分析和市场估值水平及流动性的变化自上而下进行.*优选投资标的.*追求目标收益",
                ],
                "top_anchor_content_regs": [
                    r"(?P<content>本信托计划的投资范围.*)",
                    r"(?P<content>本信托计划可根据资金管理的需求，投资于现金.*)",
                ],
            },
            {
                "name": "table_kv_expand",
                "feature_black_list": table_kv_black_feature,
                "feature_white_list": table_kv_white_feature,
                "use_complete_table": True,
                "top_anchor_regs": [
                    r"^.\d.本信托计划主要投资于",
                ],
                "include_bottom_anchor": True,
                "bottom_anchor_regs": [
                    r"本信托计划主要投资由.*担任管理人.*担任托管人的",
                ],
                "bottom_anchor_content_regs": [r"(?P<content>特别提请委托人注意.*)本信托计划主要投资由.*担任管理人"],
            },
            {
                "name": "table_kv_expand",
                "feature_black_list": table_kv_black_feature,
                "feature_white_list": table_kv_white_feature,
                "use_complete_table": True,
                "top_anchor_regs": [
                    r"^本.*的投资范围",
                    r"本.*投资范围的调整",
                    r"本信托计划主要投资于",
                    r"现金及债权类资产.*股权类资产",
                ],
                "bottom_anchor_regs": [
                    r"^本.*的?投资(组合)?比例",
                    r"基金的投资策略",
                    r"本信托计划的投资策略",
                    r"本集合计划可基于谨慎原则",
                ],
            },
            {
                "name": "table_kv",
                "feature_black_list": table_kv_black_feature,
                "feature_white_list": table_kv_white_feature,
            },
        ],
    },
    {
        "path": ["特别提示"],
        "models": [
            {
                "name": "middle_paras",
                "top_page_offset": 10,
                "possible_element_counts": 400,
                "top_anchor_regs": [
                    r"^.{,3}特别提示",
                ],
                "include_top_anchor": False,
                "bottom_anchor_regs": [
                    r"客户确认.",
                    r"客户签字",
                ],
                "include_bottom_anchor": False,
            },
            {
                "name": "middle_paras",
                "top_page_offset": 10,
                "possible_element_counts": 400,
                "top_anchor_regs": [
                    r"一般风险揭示",
                ],
                "include_top_anchor": False,
                "bottom_anchor_regs": [
                    r"客户确认.",
                    r"客户签字",
                ],
                "include_bottom_anchor": False,
            },
        ],
    },
]


prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
