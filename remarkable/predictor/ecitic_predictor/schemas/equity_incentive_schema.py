"""中信交易部_股权激励合并"""

predictor_options = [
    {
        "path": ["工具类型"],
        "models": [
            {
                "name": "partial_text",
                "multi": True,
                "model_alternative": True,
                "regs": [
                    r"本(激励)?计划所?采[取用]的激励(工具|形式)为(?P<dst>(股票期权|限制性股票(（(第一类限制性股票及第二类限制性股票|第\w类限制性股票）))?))",
                    r"本次激励计划公司授予激励对象.*?份(?P<dst>股票期权)",
                    r"本计划拟授予的(?P<dst>股票期权|限制性股票)数量",
                    r"(本激励计划)?拟向激励对象授予.*?(?P<dst>股票期权|限制性股票)",
                ],
            },
        ],
    },
    {
        "path": ["安排表"],
        "crude_answer_path": ["安排表", "期间"],
        "models": [
            {
                "name": "performance",
                "multi_elements": True,
                "page_range": list(range(4, 100)),
                "neglect_title_patterns": [
                    r"业绩考核|绩效考核|考核目标",
                    r"激励对象获授的各批次限制性股票自其授予之日起至各批次归属日",
                    r"摊薄效应",
                    r"无风险收益率",
                ],
                "neglect_syllabus_regs": [
                    r"特别提示",
                    r"公允价值的测算",
                ],
                "比例": {
                    "feature_white_list": [r"__regex__比例"],
                },
                "期间": {
                    "feature_white_list": [r"__regex__解除限售期"],
                },
                "时间": {
                    "feature_white_list": [
                        "__regex__行权安排",
                    ],
                    "neglect_patterns": [r"第\w个行权期"],
                },
                "授予类型": {
                    "feature_black_list": [
                        "__regex__行权安排",
                    ],
                },
                "from_title": {
                    "授予类型": [
                        r"(?P<dst>(首次授予|预留部分|预留))",
                    ],
                    "工具类型": [
                        r"(?P<dst>(股票期权|股票增值权|限制性股票|第一类限制性股票))",
                    ],
                    "激励对象类型": [
                        r"(?P<dst>第[一二]类激励对象|中层管理人员|核心骨干员工)",
                    ],
                },
            },
        ],
    },
    {
        "path": ["业绩考核"],
        "crude_answer_path": ["业绩考核", "期间"],
        "models": [
            {
                "name": "performance",
                "multi_elements": True,
                "page_range": list(range(4, 100)),
                "激励对象类型": {
                    "feature_black_list": [r"__regex__解除限售期"],
                },
                "业绩考核目标": {
                    "feature_white_list": [
                        r"__regex__业绩考核条件",
                        r"__regex__业绩指标",
                    ],
                },
                "期间": {
                    "feature_white_list": [
                        r"__regex__(行权期|行权安排)",
                    ],
                    "neglect_patterns": [
                        r"(预留|首次)授予的(限制性股票|股票期权)$",
                        r"^行权安排$",
                    ],
                },
                "neglect_syllabus_regs": [
                    r"特别提示",
                ],
                "neglect_title_patterns": [
                    r"时间安排",
                ],
                "title_patterns": [
                    r"业绩考核|绩效考核|考核目标",
                ],
                "from_title": {
                    "授予类型": [
                        r"(?P<dst>(首次授予|预留部分|预留))",
                    ],
                    "工具类型": [
                        r"(?P<dst>(股票期权|股票增值权|限制性股票|第一类限制性股票))",
                    ],
                    "激励对象类型": [
                        r"(?P<dst>第[一二]类激励对象|中层管理人员|核心骨干员工)",
                    ],
                },
            },
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
