"""信托合同"""

predictor_options = [
    {
        "path": ["资产类"],
        "models": [
            {
                "name": "syllabus_elt",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
            },
        ],
    },
    {
        "path": ["资产类", "信托财产/专项计划资产"],
        "models": [
            {
                "name": "clearance_repo",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
                "信托财产/专项计划资产": {
                    "feature_white_list": [
                        r"信托财产的范围$",
                        r"信托财产的范围、种类、标准和状况$",
                    ],
                },
            },
        ],
    },
    {
        "path": ["资产类", "封包期利息是否入池"],
        "models": [
            {
                "name": "period_interest",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
                "封包期利息是否入池": {
                    "feature_white_list": [r"信托财产的范围$"],
                },
            },
        ],
    },
    {
        "path": ["归集划付类"],
        "models": [
            {
                "name": "syllabus_elt",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
                "账户划付设置": {
                    "feature_white_list": [
                        r"质押资产回收款的转付流程$",
                        r"回收款的转付$",
                        r"发行载体的分配实施流程$",
                    ],
                },
            },
            {
                "name": "score_filter",
                "threshold": 0.5,
                "aim_types": ["PARAGRAPH"],
            },
        ],
    },
    {
        "path": ["现金流类"],
        "models": [
            {
                "name": "cash_flow",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
                "include_title": True,
                "multi": True,
                "违约事件发生前，收入分账户项下资金的分配（分账）": {
                    "feature_black_list": [
                        r"__regex__回收款的转付、核算与分配|合格投资",
                    ],
                    "feature_white_list": [
                        r"科目一项下回收款的分配顺序",
                        r"科目二项下回收款的分配顺序",
                        r"违约事件发生前，?(信托)?收益账项下资金的?分配",
                        r"违约事件发生前的回收款分配",
                    ],
                },
                "违约事件发生前，本金分账户项下资金的分配（分账）": {
                    "feature_white_list": [
                        r"科目一项下回收款的分配顺序",
                        r"科目二项下回收款的分配顺序",
                        r"违约事件发生前，?(信托)?本金账项下资金的?分配",
                        r"违约事件发生前的回收款分配",
                    ],
                },
                "违约事件发生前的回收款分配（不分账）": {
                    "feature_white_list": [
                        r"违约事件/信托清算事件发生前的回收款的?分配",
                        r"正常情况下的信托利益的?分配",
                        r"违约事件发生前的处置收入的?分配",
                        r"违约事件发生前信托收款账户的?(处置收入的?)?分配",
                        r"违约事件发生前的?可分配现金账户的?分配",
                        r"未发生合伙企业临时分配事件和违约事件时的?分配顺序",
                        r"信托终止前信托财产的分配",
                    ],
                },
                "违约事件发生后的回收款分配": {
                    "feature_white_list": [
                        r"违约事件/信托清算事件发生后的回收款的?分配",
                        r"违约事件或提前还款事件发生后的回收款的?分配",
                        r"违约事件发生后的信托利益的?分配",
                        r"违约事件发生后的信托财产的?分配",
                        r"违约事件发生后的回收款的?分配",
                        r"违约事件发生后的处置收入的?分配",
                        r"违约事件发生后信托收款账户的?(处置收入的?)?分配",
                        r"违约事件发生后的?可分配现金账户的?分配",
                        r"发生合伙企业临时分配事件或违约事件后的?分配顺序",
                    ],
                },
            },
        ],
    },
    {
        "path": ["其他类"],
        "models": [
            {
                "name": "syllabus_elt",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
                "neglect_patterns": [
                    r"报告后5个“工作日”内",
                    r"信托财产的管理及委托代理信托事务|货币类信托财产的保管|委托资金保管机构",
                ],
                "清仓回购": {
                    "feature_white_list": [r"\d+清仓回购$"],
                },
                "不合格基础资产赎回": {
                    "feature_white_list": [r"不合格基础资产的?赎回$"],
                },
                "逾期基础资产赎回/置换": {
                    "feature_white_list": [r"[\d\.]+超期基础资产的提前变现$"],
                },
            },
        ],
    },
    {
        "path": ["其他类", "清仓回购"],
        "models": [
            {
                "name": "clearance_repo",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
                "neglect_patterns": [
                    r"报告后5个“工作日”内",
                    r"信托财产的管理及委托代理信托事务|货币类信托财产的保管|委托资金保管机构",
                ],
                "add_para_pattern": [
                    r"满足本合同第(?P<dst>([\d.]+))[条款]约定的条件的情况下",
                ],
                "清仓回购": {
                    "feature_white_list": [r"\d+清仓回购$"],
                },
                "multi": True,
            },
        ],
    },
]


prophet_config = {"depends": {}, "predictor_options": predictor_options}
