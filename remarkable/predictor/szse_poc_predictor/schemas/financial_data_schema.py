"""
2: 深交所信息抽取-创业板-注册制-财务基础数据
"""

from remarkable.predictor.common_pattern import DATE_PATTERN

REPORT_YEAR_PATTERN = r"(?:1\d|20|21)\d{2}.*"

predictor_options = [
    {
        "path": [
            "合并资产负债表",
        ],
        "sub_primary_key": ["报告期"],
        "models": [
            {
                "name": "consolidated_balance_sheet",
                "distinguish_year": False,
                "multi_elements": True,
                "filter_later_elements": True,
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": [REPORT_YEAR_PATTERN],
                    }
                ],
                "归属于母公司所有者权益": {
                    "feature_white_list": [
                        r"DATE|股东权益合计",
                    ],
                    "feature_black_list": [
                        r"DATE|所有者权益合计",
                    ],
                },
            },
        ],
        # 'location_threshold': 0.08,
    },
    {
        "path": [
            "合并利润表",
        ],
        "sub_primary_key": ["报告期"],
        "models": [
            {
                "name": "table_tuple",
                "distinguish_year": False,
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": [REPORT_YEAR_PATTERN],
                    }
                ],
                "营业收入": {
                    "feature_black_list": [r"__regex__DATE|营业总收入"],
                },
                "归属于母公司所有者的净利润": {
                    "feature_white_list": [
                        r"__regex__DATE|^净利润$",
                        r"__regex__DATE|归属于母公司所有者综合收益总额",
                    ],
                },
                "基本每股收益（元）": {
                    "feature_white_list": [r"DATE|基本每股收益"],
                    "feature_black_list": [r"__regex__DATE|稀释每股收益"],
                },
            },
        ],
        # 'location_threshold': 0.08,
    },
    {
        "path": [
            "合并现金流量表",
        ],
        "sub_primary_key": ["报告期"],
        "models": [
            {
                "name": "table_tuple",
                "distinguish_year": False,
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": [REPORT_YEAR_PATTERN],
                    }
                ],
                "筹资活动产生的现金流量净额": {
                    "feature_white_list": [
                        r"DATE|筹资活动使用现金流量净额",
                    ]
                },
            },
        ],
        # 'location_threshold': 0.04,
    },
    {
        "path": [
            "非经常性损益表",
        ],
        "sub_primary_key": ["报告期"],
        "models": [
            {
                "name": "nonrecurring_income",
                "distinguish_year": False,
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": [REPORT_YEAR_PATTERN],
                    }
                ],
                "扣除所得税影响后的非经常性损益": {
                    "feature_white_list": [
                        r"DATE|归属于母公司股东非经常性损益合计",
                        r"DATE|扣除少数股东损益和所得税影响后非经常性损益金额",
                        r"DATE|归属于母公司股东税后非经常性损益",
                    ]
                },
                "扣除非经常性损益后的归属于母公司所有者净利润": {
                    "feature_white_list": [
                        # r'DATE|扣除非经常性损益后归属于母公司股东净利润',
                        r"DATE|扣除非经常性损益后净利润",
                    ],
                    "feature_black_list": [
                        r"DATE|非经常性损益净额",
                        r"DATE|合计",
                    ],
                },
            },
        ],
        # 'location_threshold': 0.1,
    },
    {
        "path": ["八-主要财务指标表"],
        "sub_primary_key": ["报告期"],
        "models": [
            {
                "name": "table_tuple",
                "multi_elements": True,
                "distinguish_year": False,
                "filter_later_elements": True,
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": [REPORT_YEAR_PATTERN],
                    }
                ],
                "归属于母公司所有者的每股净资产": {
                    "feature_black_list": [
                        r"__regex__DATE|研发投入占营业收入比例",
                    ]
                },
                "应收账款周转率（次）": {
                    "feature_white_list": [
                        r"__regex__DATE|应收账款周转率年化",
                        r"__regex__DATE|应收账款及合同资产周转率",
                    ]
                },
                "存货周转率（次）": {
                    "feature_white_list": [
                        r"__regex__DATE|存货周转率年化",
                    ]
                },
                "资产负债率（母公司报表）（%）": {
                    "feature_black_list": [
                        r"__regex__DATE|资产负债率",
                    ],
                    "feature_white_list": [
                        r"__regex__DATE|资产负债率母公司",
                        r"__regex__DATE|母公司资产负债率",
                    ],
                },
                "归属于母公司所有者的净利润": {
                    "feature_white_list": [
                        r"__regex__DATE|归属于母公司所有者净利润",
                    ]
                },
                "归属于母公司所有者权益": {
                    "feature_white_list": [
                        r"__regex__DATE|归属于母公司所有者权益",
                    ]
                },
                "每股净现金流量（元）": {
                    "feature_black_list": [
                        r"__regex__DATE|每股经营活动产生现金流量净额",
                    ]
                },
                "每股净资产（元）": {
                    "feature_white_list": [
                        r"__regex__DATE|归属于发行人股东每股净资产",
                    ]
                },
            },
        ],
        # 'location_threshold': 0.3,
    },
    {
        "path": [
            "八-净资产收益率表",
        ],
        "sub_primary_key": ["报告期"],
        "models": [
            {
                "name": "return_on_net_assets",
                "distinguish_year": False,
                "lazy_match": "True",
                # 'neglect_title_patterns': [r'主要财务指标'],
            },
        ],
        "location_threshold": 0.04,
    },
    {
        "path": [
            "二-主要财务指标表",
        ],
        "sub_primary_key": ["报告期"],
        "models": [
            {
                "name": "table_tuple",
                "distinguish_year": False,
                "filter_later_elements": True,
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": [REPORT_YEAR_PATTERN],
                    }
                ],
                "归属于母公司所有者的净利润": {
                    "feature_white_list": [
                        r"__regex__DATE|归属于母公司所有者净利润",
                    ]
                },
                "归属于母公司所有者权益": {
                    "feature_white_list": [
                        r"__regex__DATE|归属于母公司所有者权益",
                    ]
                },
            },
        ],
        # 'location_threshold': 0.3,
    },
    {
        "path": [
            "期间费用表",
        ],
        "sub_primary_key": ["报告期"],
        "models": [
            {
                "name": "period_fee_schedule",
                "multi_elements": True,
                "filter_later_elements": True,
                "distinguish_year": False,
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": [REPORT_YEAR_PATTERN],
                    }
                ],
                "管理费用/营业收入（%）": {
                    "feature_black_list": [
                        r"__regex__DATE|增长率|管理费用",
                    ],
                    "feature_white_list": [
                        r"__regex__DATE|管理费用占营业收入比例",
                    ],
                },
                "销售费用/营业收入（%）": {
                    "feature_black_list": [
                        r"__regex__DATE|增长率|销售费用",
                    ],
                    "feature_white_list": [
                        r"__regex__DATE|销售费用占营业收入比例",
                    ],
                },
                "财务费用/营业收入（%）": {
                    "feature_black_list": [
                        r"__regex__DATE|增长率|财务费用",
                        r"__regex__DATE|金额|财务费用",
                        r"__regex__DATE|金额|销售费用",
                    ],
                    "feature_white_list": [
                        r"__regex__DATE|财务费用占营业收入比例",
                    ],
                },
            },
        ],
        # 'location_threshold': 0.3,
    },
    {
        "path": [
            "风险因素",
        ],
        "sub_primary_key": ["报告期"],
        "models": [
            {
                "name": "complex_gross_margin",
                "multi": True,
            },
        ],
        "location_threshold": 0.003,
    },
    {
        "path": [
            "经营成果表",
        ],
        "sub_primary_key": ["报告期"],
        "models": [
            {
                "name": "table_tuple",
                "distinguish_year": False,
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": [REPORT_YEAR_PATTERN],
                    }
                ],
            },
        ],
        "location_threshold": 0.03,
    },
    {
        "path": [
            "盈利能力表",
        ],
        "sub_primary_key": ["报告期"],
        "models": [
            {
                "name": "complex_gross_margin",
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": [REPORT_YEAR_PATTERN],
                    }
                ],
            },
        ],
    },
    {
        "path": [
            "毛利表",
        ],
        "sub_primary_key": ["报告期"],
        "models": [
            {
                "name": "gross_profit_table",
                "distinguish_year": False,
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": [REPORT_YEAR_PATTERN],
                    }
                ],
                "neglect_title_patterns": [
                    r"主营业务毛利率变动分析",
                    r"主营业务毛利和毛利率",
                    r"主营业务毛利率",
                    r"扣除.*?费用影响后.*?毛利率",
                ],
            },
        ],
        "location_threshold": 0.01,
    },
    {
        "path": [
            "综合毛利率（其他）",
        ],
        "sub_primary_key": ["报告期"],
        "models": [
            {
                "name": "complex_gross_margin",
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": [REPORT_YEAR_PATTERN],
                    }
                ],
            },
            {
                "name": "table_tuple",
                "distinguish_year": False,
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": [REPORT_YEAR_PATTERN],
                    }
                ],
                "neglect_title_patterns": [
                    r"同行业可比公司及泛半导体行业代表公司的毛利率",
                    r"销售占比",
                ],
                "综合毛利率（%）": {
                    "feature_white_list": [
                        r"DATE|主营业务毛利率",
                    ]
                },
            },
        ],
        # 'location_threshold': 0.1,
    },
    {
        "path": [
            "偿债能力表",
        ],
        "sub_primary_key": ["报告期"],
        "models": [
            {
                "name": "table_tuple",
                "distinguish_year": False,
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": [REPORT_YEAR_PATTERN],
                    }
                ],
            },
        ],
        "location_threshold": 0.08,
    },
    {
        "path": [
            "员工人数表",
        ],
        "sub_primary_key": ["报告期"],
        "models": [
            {
                "name": "employees_num",
                "multi_elements": True,
                "filter_later_elements": True,
                "distinguish_year": False,
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": [
                            r"(?P<dst>\d{4}\s?年\s?\d{1,2}\s?月\s?末?(\d{1,2}?\s?日)?)员工结构",
                            r"(?P<dst>\d{4}\s?年\s?\d{1,2}月\d{1,2}\s?日)",
                            DATE_PATTERN,
                        ],
                    }
                ],
            },
        ],
        "location_threshold": 0.051,
    },
    {
        "path": [
            "员工薪酬表",
        ],
        "sub_primary_key": ["报告期"],
        "models": [
            {
                "name": "table_tuple",
                "distinguish_year": False,
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": [REPORT_YEAR_PATTERN],
                    }
                ],
            },
        ],
        "location_threshold": 0.036,
    },
    {
        "path": [
            "其他指标（临时）",
        ],
        "sub_primary_key": ["报告期"],
        "models": [
            {
                "name": "table_tuple",
                "distinguish_year": False,
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": [REPORT_YEAR_PATTERN],
                    }
                ],
            },
        ],
        "location_threshold": 0.1,
    },
    {
        "path": [
            "一-释义",
        ],
        "sub_primary_key": [
            "简称",
        ],
        "models": [
            {
                "name": "interpretation",
            },
        ],
        "strict_group": True,
    },
    {
        "path": [
            "二-发行人基本情况",
        ],
        "models": [
            {
                "name": "basic_information",
            },
        ],
    },
    {
        "path": ["二-发行人基本情况", "实际控制人情况"],
        "sub_primary_key": [
            "名称",
        ],
        "models": [
            {
                "name": "actual_control_situation",
            },
        ],
    },
    {
        "path": ["二-发行人基本情况", "行业分类（证监会）"],
        "models": [
            {
                "name": "industry_classification",
            },
        ],
    },
    {
        "path": ["二-发行人基本情况", "行业分类（申万）"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": [
            "二-本次发行概况",
        ],
        "models": [
            {
                "name": "distribution_profile",
            },
        ],
    },
    {
        "path": [
            "二-主营业务",
        ],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "keep_parent": True,
                "match_method": "similarity",
                "only_first": True,
            },
        ],
    },
    {
        "path": [
            "二-发行人上市标准",
        ],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": [
            "三-本次发行的基本情况",
        ],
        "models": [
            {
                "name": "distribution_profile",
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": [
            "三-本次发行的有关机构",
        ],
        "sub_primary_key": ["名称", "机构类型"],
        "models": [
            {
                "name": "institutions_concerned",
            },
        ],
    },
    {
        "path": [
            "五-发行人基本情况",
        ],
        "models": [
            {
                "name": "five_basic_information",
                "table_model": "table_kv",
                "para_config": {
                    "申报企业（全称）": {"use_answer_pattern": False},
                },
                "inject_syllabus_features": [r"发行人基本情况|基本情况"],
            },
        ],
    },
    {
        "path": [
            "五-最近一次增资",
        ],
        "models": [
            {
                "name": "last_capital_increase",
                "table_model": "table_row",
                "table_config": {
                    "multi": False,
                    "multi_elements": False,
                    "filter_later_elements": False,
                },
                "para_config": {
                    "multi": False,
                },
            },
        ],
    },
    {
        "path": ["五-最近一次增资", "原文"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "keep_parent": True,
                "match_method": "similarity",
            },
        ],
    },
    {
        "path": [
            "五-控股股东和实际控制人情况",
        ],
        "sub_primary_key": ["全称"],
        "models": [
            {
                "name": "szse_holder_info",
                "multi": True,
                "para_config": {
                    "全称": {"use_answer_pattern": False},
                },
                "table_config": {
                    "multi": True,
                },
            },
        ],
        "group": {"lookup_strategy": "lookahead", "range_num": 10},
    },
    {
        "path": [
            "五-发行人股本情况",
        ],
        "sub_primary_key": [
            "名称",
        ],
        "models": [
            {
                "name": "table_row",
                "neglect_patterns": [
                    r"[合总小]并?计|社会公众股",
                    r"本次(公开|拟)发行(的新股)?股份",
                    r"有限售条件的(流通股|股份)",
                    r"^\d+$",
                ],
                "neglect_title_patterns": [r"前十名"],
                "名称": {
                    "feature_white_list": [r"姓名/名称"],
                },
            },
        ],
    },
    {
        "path": [
            "五-发行人股本情况-总股本",
        ],
        "models": [
            {
                "name": "table_tuple",
                "neglect_title_patterns": [r"本次发行前，公司前十名股东持股情况如下："],
            },
        ],
    },
    {
        "path": [
            "五-国有股东和外资股东情况",
        ],
        "sub_primary_key": [
            "名称",
        ],
        "models": [
            {
                "name": "syllabus_based",
                "multi_elements": True,
                "use_crude_answer": False,
                "table_model": "table_row",
                "para_config": {
                    "名称": {"use_answer_pattern": False},
                    "multi": True,
                },
            },
        ],
    },
    {
        "path": [
            "五-董监高核情况-表格",
        ],
        "sub_primary_key": [
            "姓名",
            "董监高身份",
        ],
        "models": [
            {
                "name": "syllabus_based",
                "multi_elements": True,
                "table_model": "table_row",
                "table_config": {
                    "multi": True,
                    "multi_elements": True,
                    "neglect_patterns": [
                        r"^/$",
                    ],
                    "neglect_title_patterns": [
                        r"股份.*?变动|领取薪酬|领取津贴|持有公司股份|对外投资情况|亲属直接|亲属持股|占利润总额的比重|股权激励计划|股份转让"
                    ],
                },
                "syllabus_level": 2,
            },
        ],
    },
    {
        "path": [
            "五-董监高核情况-段落",
        ],
        "sub_primary_key": [
            "姓名",
        ],
        "element_candidate_count": 20,
        "models": [
            {
                "name": "director_information",
                "multi_elements": True,
                "姓名": {
                    "use_answer_pattern": False,
                },
            },
        ],
    },
    {
        "path": ["五-员工持股与股权激励计划", "是否存在员工持股计划"],
        "models": [
            {
                "name": "score_filter",
                "aim_types": ["PARAGRAPH"],
                "threshold": 0.1,
            },
        ],
    },
    {
        "path": ["五-员工持股与股权激励计划", "是否存在股权激励计划"],
        "models": [
            {
                "name": "score_filter",
                "aim_types": ["PARAGRAPH"],
                "threshold": 0.1,
            },
        ],
    },
    {
        "path": [
            "员工持股与股权激励计划（临时）",
        ],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": [
            "六-主营业务",
        ],
        "models": [
            {"name": "syllabus_elt_v2", "keep_parent": True, "match_method": "similarity", "only_first": True},
        ],
    },
    {
        "path": [
            "六-行业基本情况（证监会）",
        ],
        "models": [
            {
                "name": "six_industry_classification",
            },
        ],
    },
    {
        "path": [
            "六-行业基本情况（申万）",
        ],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": [
            "行业基本情况（证监会）（临时）",
        ],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": [
            "行业基本情况（申万）（临时）",
        ],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": [
            "八-财务报表编制基础",
        ],
        "models": [
            {
                "name": "syllabus_elt",
            },
        ],
    },
    {
        "path": [
            "八-注册会计师的审计意见",
        ],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": [
            "项目基本情况表（临时）",
        ],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": [
            "主要产品市场占有率（临时）",
        ],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": [
            "重大科技专场（临时）",
        ],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": [
            "参与标准制定情况（临时）",
        ],
        "models": [
            {
                "name": "table_row",
            },
        ],
    },
    {
        "path": [
            "产品实现进口替代情况（临时）",
        ],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
]


prophet_config = {"depends": {}, "predictor_options": predictor_options}
