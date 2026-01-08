"""基金合同"""

LOCK_UP_PERIOD_PATTERN = [
    r"本基金的?(份额)?锁定期[为是].*?锁定期内不得赎回。",
    r"本基金自份额确认日起.*?内禁止赎回。",
    r"本基金的?(份额)?锁定期[为是].*?[。]",
]

predictor_options = [
    {
        "path": [
            "产品全称",
        ],
        "models": [
            {
                "name": "partial_text",
                "multi_elements": True,
                "use_answer_pattern": False,
            }
        ],
        "location_threshold": 0.1,
    },
    {
        "path": [
            "基金规模",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "运作方式",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "募集期描述",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "存续期方式",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "存续期限",
        ],
        "models": [
            {
                "name": "partial_text",
                "multi_elements": True,
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "是否有锁定期",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": LOCK_UP_PERIOD_PATTERN,
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"申购和赎回的开放日及时间"],
                "only_inject_features": True,
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": LOCK_UP_PERIOD_PATTERN,
                },
            },
        ],
    },
    {
        "path": [
            "份额锁定期描述",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": LOCK_UP_PERIOD_PATTERN,
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"申购和赎回的开放日及时间"],
                "only_inject_features": True,
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": LOCK_UP_PERIOD_PATTERN,
                },
            },
        ],
    },
    {
        "path": [
            "是否有封闭期",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"申购和赎回的开放日及时间"],
                "only_inject_features": True,
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        r"本基金的?封闭期[为是].*?[，。]",
                    ],
                },
            },
        ],
    },
    {
        "path": [
            "产品封闭期描述",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"申购和赎回的开放日及时间"],
                "only_inject_features": True,
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        r"本基金的?封闭期[为是].*?[，。]",
                    ],
                },
            },
        ],
    },
    {
        "path": [
            "开放日描述",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>本基金的?开放日[为是].*?)。",
                ],
            }
        ],
    },
    {
        "path": [
            "临时开放日描述",
        ],
        "models": [
            {
                "name": "middle_paras",
                "use_top_crude_neighbor": False,
                "include_top_anchor": True,
                "include_bottom_anchor": True,
                "top_anchor_regs": [r"增设临时开放日"],
                "bottom_anchor_regs": [r"基金管理人因基金投资运作需求进行流动性管理"],
            },
        ],
    },
    {
        "path": [
            "管理人全称",
        ],
        "models": [
            {
                "name": "partial_text",
                "multi_elements": True,
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "管理人注册地址",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "法定代表人",
        ],
        "models": [
            {
                "name": "account",
                "anchor_regs": [r"基金管理人"],
                "use_answer_pattern": False,
                "must_preset": False,
            }
        ],
    },
    {
        "path": [
            "联系人通讯地址",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": ["联系人（基本情况）", "联系人姓名"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": ["联系人（基本情况）", "联系人电话"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": ["联系人（基本情况）", "联系人电子邮箱"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": ["联系人（基本情况）", "联系人邮箱"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "联系人（业务联系表）",
        ],
        "sub_primary_key": ["联系人姓名", "联系人电话", "联系人邮箱"],
        "models": [
            {
                "name": "table_row",
                "multi": True,
                "联系人姓名": {
                    "feature_white_list": [r"__regex__姓名|公司"],
                },
                "联系人电话": {
                    "feature_white_list": [r"__regex__联系电话|公司"],
                },
                "联系人邮箱": {
                    "feature_white_list": [r"__regex__邮箱|公司"],
                },
            },
        ],
    },
    {
        "path": [
            "管理人登记编码",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "基金经理",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "投资经理简介",
        ],
        "models": [
            {
                "name": "investment_scope",
            },
            {
                "name": "syllabus_elt",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
            },
        ],
    },
    {
        "path": [
            "投资范围",
        ],
        "models": [
            {
                "name": "investment_scope",
            },
            {
                "name": "para_match",
                "paragraph_pattern": r"(?P<content>(^[（(]三[）)]投资范围|^投资于).*)",
                "multi_elements": True,
            },
        ],
    },
    {
        "path": [
            "投资目标",
        ],
        "models": [
            {
                "name": "investment_scope",
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>^[（(]二[）)]投资目标.*)",
                    r"(?P<content>^本基金.*投入的资金.*稳定增值)",
                ),
                "multi_elements": True,
            },
        ],
    },
    {
        "path": [
            "投资策略",
        ],
        "models": [
            {
                "name": "investment_scope",
            },
            {
                "name": "syllabus_elt",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
                "multi": True,
            },
        ],
    },
    {
        "path": [
            "投资限制",
        ],
        "models": [
            {
                "name": "syllabus_elt",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
                "multi": True,
            }
        ],
    },
    {
        "path": [
            "投资禁止行为",
        ],
        "models": [
            {
                "name": "syllabus_elt",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
                "multi": True,
            }
        ],
    },
    {
        "path": [
            "注册登记机构",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "风险登记描述",
        ],
        "models": [
            {
                "name": "partial_text",
                "multi": True,
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": [
            "有无预警线",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "预警线",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "预警措施",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "有无止损线",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "止损线",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "止损措施",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "是否收取赎回费",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>本基金不收取赎回费)",
                    r"(?P<dst>本基金的赎回费率[为是].*?)[，。]",
                    r"(?P<dst>本基金的赎回费用[为是].*?持有超过.*?天以上不收取赎回费用)",
                    r"(?P<dst>(本基金投资者|对于投资者份额)持有期不足.*?赎回费.*?持有期满.*?赎回费.*?持有期满.*?免赎回费)",
                ],
            }
        ],
    },
    {
        "path": [
            "赎回费",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>本基金不收取赎回费)",
                    r"(?P<dst>本基金的赎回费率[为是].*?)[，。]",
                    r"(?P<dst>本基金的赎回费用[为是].*?持有超过.*?天以上不收取赎回费用)",
                    r"(?P<dst>(本基金投资者|对于投资者份额)持有期不足.*?赎回费.*?持有期满.*?赎回费.*?持有期满.*?免赎回费)",
                ],
            }
        ],
    },
    {
        "path": [
            "赎回费描述",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>本基金不收取赎回费)",
                    r"(?P<dst>本基金的赎回费用[为是].*?持有超过.*?天以上不收取赎回费用)",
                    r"(?P<dst>本基金投资者持有期不足.*?赎回费.*?持有期满.*?赎回费.*?持有期满.*?免赎回费)",
                ],
            }
        ],
    },
    {
        "path": [
            "基金份额持有人赎回费归属",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "是否收取申购费",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>本基金的申购费率[为是].*?)[，。]",
                ],
            }
        ],
    },
    {
        "path": [
            "申购费描述",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>本基金的申购费率[为是].*?)[，。]",
                ],
            }
        ],
    },
    {
        "path": [
            "是否收取认购费",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>本基金对募集期认购的客户收取认购费，认购费.*?)[，。]",
                ],
            }
        ],
    },
    {
        "path": [
            "认购费描述",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>本基金对募集期认购的客户收取认购费，认购费.*?)[，。]",
                ],
            }
        ],
    },
    {
        "path": [
            "个人首次认购最低金额",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "个人认购追加最低金额",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "机构首次认购最低金额",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "机构认购追加最低金额",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "是否巨额赎回",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "巨额赎回比例",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "是否允许收益分配",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "收益分配方式",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "是否有收益分配次数",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "收益分配次数",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "前台人员姓名",
        ],
        "models": [
            {
                "name": "table_tuple",
            }
        ],
    },
    {
        "path": [
            "前台人员电话",
        ],
        "models": [
            {
                "name": "table_tuple",
            }
        ],
    },
    {
        "path": [
            "前台人员电子邮件",
        ],
        "models": [
            {
                "name": "table_tuple",
            }
        ],
    },
    {
        "path": [
            "中台人员姓名",
        ],
        "models": [
            {
                "name": "table_tuple",
            }
        ],
    },
    {
        "path": [
            "中台人员电话",
        ],
        "models": [
            {
                "name": "table_tuple",
            }
        ],
    },
    {
        "path": [
            "中台人员电子邮件",
        ],
        "models": [
            {
                "name": "table_tuple",
            }
        ],
    },
    {
        "path": [
            "是否收取业绩报酬",
        ],
        "models": [
            {
                "name": "syllabus_elt",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
            }
        ],
    },
    {
        "path": [
            "户名（业绩报酬）",
        ],
        "models": [
            {
                "name": "account",
                "anchor_regs": [r"业绩报酬"],
                "use_answer_pattern": False,
                "must_preset": False,
            },
        ],
    },
    {
        "path": [
            "业绩报酬收款账号",
        ],
        "models": [
            {
                "name": "account",
                "anchor_regs": [r"业绩报酬"],
                "use_answer_pattern": False,
                "must_preset": False,
            },
        ],
    },
    {
        "path": [
            "大额支付号（业绩报酬）",
        ],
        "models": [
            {
                "name": "account",
                "anchor_regs": [r"业绩报酬"],
                "use_answer_pattern": False,
                "must_preset": False,
            },
        ],
    },
    {
        "path": [
            "开户行（业绩报酬）",
        ],
        "models": [
            {
                "name": "account",
                "anchor_regs": [r"业绩报酬"],
                "use_answer_pattern": False,
                "must_preset": False,
            },
        ],
    },
    {
        "path": [
            "托管费",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "multi": True,
                "model_alternative": True,
                "regs": [
                    r"基金的托管费率[为是](基金资产总值的)?(?P<dst>.*?)[，。]",
                    # r'本基金托管费[为是](?P<dst>.*?)与.*?孰高原则收取',
                    # r'本基金托管费[为是].*?与(?P<dst>.*?)孰高原则收取',
                    r"(?P<dst>本基金托管费[为是].*?与.*?孰高原则收取)",
                ],
            }
        ],
    },
    {
        "path": [
            "管理费",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    r"本?基金的管理费率[为是](?P<dst>.*?)[，。]",
                    r"本?基金的管理费率[为是]基金资产总值的(?P<dst>.*?)[，。]",
                    r"本?基金的管理费按前一日基金资产净值的(?P<dst>.*?)年费率计提",
                ],
            }
        ],
    },
    {
        "path": [
            "管理费收款账户户名",
        ],
        "models": [
            {
                "name": "account",
                "anchor_regs": [r"管理费"],
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": [
            "管理费收款账户账号",
        ],
        "models": [
            {
                "name": "account",
                "anchor_regs": [r"管理费"],
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "管理费收款账户开户行",
        ],
        "models": [
            {
                "name": "account",
                "anchor_regs": [r"管理费"],
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "管理收款账户大额支付号",
        ],
        "models": [
            {
                "name": "account",
                "anchor_regs": [r"管理费"],
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "行政服务费",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "multi": True,
                "model_alternative": True,
                "regs": [
                    r"本?基金的年?行政服务费率[为是]基金资产总值的?(?P<dst>.*?)[，。]",
                ],
            }
        ],
    },
    {
        "path": [
            "行政服务费收款账户户名",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "行政服务费收款账户",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "行政服务费收款账户开户行",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "行政服务费收款大额支付号",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "募集监督收款账户户名",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "募集监督收款账户",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "募集监督收款账户开户行",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "募集监督收款大额支付号",
        ],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": [
            "章节对比",
        ],
        "models": [
            {
                "name": "syllabus_elt",
                "前言": {
                    "feature_white_list": [
                        r"目录|前言",
                    ]
                },
                "释义": {
                    "feature_white_list": [
                        r"目录|释义",
                    ]
                },
                "基金的财产": {
                    "feature_white_list": [
                        r"目录|基金的财产",
                    ]
                },
                "指令的发送、确认与执行": {
                    "feature_white_list": [
                        r"目录|指令的发送、确认与执行",
                    ]
                },
                "交易及清算交收安排": {
                    "feature_white_list": [
                        r"目录|交易及清算交收安排",
                    ]
                },
                "越权交易": {
                    "feature_white_list": [
                        r"目录|越权交易",
                    ]
                },
                "基金财产的估值和会计核算": {
                    "feature_white_list": [
                        r"目录|基金财产的估值和会计核算",
                    ]
                },
                "信息披露与报告": {
                    "feature_white_list": [
                        r"目录|信息披露与报告",
                    ]
                },
                "基金份额的非交过户和冻结、解冻": {
                    "feature_white_list": [
                        r"目录|基金份额的非交易过户和冻结、解冻",
                    ]
                },
                "基金合同的成立、生效": {
                    "feature_white_list": [
                        r"目录|基金合同的成立、生效",
                    ]
                },
                "基金合同的效力、变更、解除与终止": {
                    "feature_white_list": [
                        r"目录|基金合同的效力、变更、解除与终止",
                    ]
                },
                "违约责任": {
                    "feature_white_list": [
                        r"目录|违约责任",
                    ]
                },
                "法律适用和争议的处理": {
                    "feature_white_list": [
                        r"目录|法律适用和争议的处理",
                    ]
                },
            }
        ],
    },
]


prophet_config = {"depends": {}, "predictor_options": predictor_options}
