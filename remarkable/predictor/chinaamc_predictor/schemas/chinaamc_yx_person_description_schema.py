# 港股人员说明


predictor_options = [
    {
        "path": ["001基金名称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    r"(?P<dst>华夏.*)参",
                ],
                "neglect_patterns": [
                    r"本基金",
                ],
            },
            {
                "name": "middle_paras",
                "page_range": [0],
                "top_anchor_regs": [
                    r"关于华夏",
                ],
                "bottom_anchor_regs": [r"参与"],
                "top_anchor_content_regs": [
                    r"关于(?P<content>华夏.*)",
                ],
                "bottom_anchor_content_regs": [
                    r"(?P<content>.*)参与",
                ],
                "include_bottom_anchor": True,
            },
            {
                "name": "fund_name",
                "use_answer_pattern": False,
                "regs": [
                    r"(?P<dst>华夏.*)",
                ],
            },
        ],
    },
    {"path": ["002基金名称"], "models": [{"name": "auto", "use_answer_pattern": False}]},
    {
        "path": ["003基金经理"],
        "models": [
            {"name": "auto"},
            {
                "name": "partial_text",
                "model_alternative": True,  # 配置的regs未能提取时用模型提
                "regs": ["拟任基金经理为(?P<dst>.*?)，介绍如下"],
            },
        ],
    },
    {
        "path": ["004基金经理介绍"],
        "models": [
            {
                "name": "middle_paras",
                "use_top_crude_neighbor": False,
                "include_top_anchor": False,
                "top_anchor_regs": [
                    r"经理.*?介绍如下",
                ],
                "bottom_anchor_regs": [r"介绍如下"],
            },
            {"name": "auto"},
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
