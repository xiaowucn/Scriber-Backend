"""申万宏源
3: 	债券评级报告
"""

report_year_pattern = r"(?:1\d|20|21)\d{2}.*"

predictor_options = [
    {
        "path": ["EBITDA"],
        "sub_primary_key": ["年份"],
        "models": [
            {
                "name": "table_tuple",
                "dimensions": [
                    {
                        "column": "年份",
                        "pattern": [report_year_pattern],
                    }
                ],
            }
        ],
    },
    {
        "path": ["长期债务"],
        "sub_primary_key": ["年份"],
        "models": [
            {
                "name": "table_tuple",
                "dimensions": [
                    {
                        "column": "年份",
                        "pattern": [report_year_pattern],
                    }
                ],
                "金额": {
                    "feature_white_list": [r"largest_year_minus_2|其中长期有息债务"],
                },
            }
        ],
    },
    {
        "path": ["短期债务"],
        "sub_primary_key": ["年份"],
        "models": [
            {
                "name": "table_tuple",
                "dimensions": [
                    {
                        "column": "年份",
                        "pattern": [report_year_pattern],
                    }
                ],
            }
        ],
    },
    {
        "path": ["X放大倍数（融资担保放大倍数）"],
        "sub_primary_key": ["年份"],
        "models": [
            {
                "name": "compensatory_rate",
                "dimensions": [
                    {
                        "column": "年份",
                        "pattern": [report_year_pattern],
                    }
                ],
                "金额": {
                    "feature_white_list": [
                        r"largest_year_minus_3|融资担保放大倍数合计*",
                    ],
                },
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["代偿额", "代偿额"],
        "sub_primary_key": ["年份"],
        "models": [
            {
                "name": "table_tuple",
                "dimensions": [
                    {
                        "column": "年份",
                        "pattern": [report_year_pattern],
                    }
                ],
            }
        ],
    },
    {
        "path": ["代偿额", "累计代偿额"],
        "sub_primary_key": ["年份"],
        "models": [
            {
                "name": "table_tuple",
                "dimensions": [
                    {
                        "column": "年份",
                        "pattern": [report_year_pattern],
                    }
                ],
            }
        ],
    },
    {
        "path": ["代偿额", "应收代偿额"],
        "sub_primary_key": ["年份"],
        "models": [
            {
                "name": "table_tuple",
                "dimensions": [
                    {
                        "column": "年份",
                        "pattern": [report_year_pattern],
                    }
                ],
            }
        ],
    },
    {
        "path": ["代偿额", "代偿率"],
        "sub_primary_key": ["年份"],
        "models": [
            {
                "name": "compensatory_rate",
                "dimensions": [
                    {
                        "column": "年份",
                        "pattern": [report_year_pattern],
                    }
                ],
            }
        ],
    },
    {
        "path": ["代偿额", "收到归还代偿款"],
        "sub_primary_key": ["年份"],
        "models": [
            {
                "name": "table_tuple",
                "dimensions": [
                    {
                        "column": "年份",
                        "pattern": [report_year_pattern],
                    }
                ],
            }
        ],
    },
    {
        "path": ["代偿额", "担保代偿支付的现金"],
        "sub_primary_key": ["年份"],
        "models": [
            {
                "name": "table_tuple",
                "dimensions": [
                    {
                        "column": "年份",
                        "pattern": [report_year_pattern],
                    }
                ],
            }
        ],
    },
    {
        "path": ["前X大对外担保"],
        "sub_primary_key": ["担保对象", "担保金额"],
        "models": [
            {
                "name": "guarantee_object",
                "multi": True,
                "neglect_patterns": [r"[合总小]并?计", r"^-+$", r"^\d+$"],
                "neglect_title_patterns": [
                    r"公司获得银行授信明细",
                    r"公司债券融资业务情况",
                    r"公司期间费用",
                    r"控股子公司情况",
                    r"前五大客户销售",
                ],
            },
            {
                "name": "partial_text",
            },
        ],
        "pick_answer_strategy": "all",
    },
    {
        "path": ["长期债务（母公司）"],
        "sub_primary_key": ["年份"],
        "models": [
            {
                "name": "table_tuple",
                "dimensions": [
                    {
                        "column": "年份",
                        "pattern": [report_year_pattern],
                    }
                ],
                "neglect_title_patterns": [r"^((?!(母公司|本部)).)*$"],
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["短期债务（母公司）"],
        "sub_primary_key": ["年份"],
        "models": [
            {
                "name": "table_tuple",
                "dimensions": [
                    {
                        "column": "年份",
                        "pattern": [report_year_pattern],
                    }
                ],
                "neglect_title_patterns": [r"^((?!(母公司|本部)).)*$"],
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["代偿额（母公司）", "代偿额"],
        "sub_primary_key": ["年份"],
        "models": [
            {
                "name": "table_tuple",
                "dimensions": [
                    {
                        "column": "年份",
                        "pattern": [report_year_pattern],
                    }
                ],
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["代偿额（母公司）", "累计代偿额"],
        "sub_primary_key": ["年份"],
        "models": [
            {
                "name": "table_tuple",
                "dimensions": [
                    {
                        "column": "年份",
                        "pattern": [report_year_pattern],
                    }
                ],
            }
        ],
    },
    {
        "path": ["代偿额（母公司）", "应收代偿额"],
        "sub_primary_key": ["年份"],
        "models": [
            {
                "name": "table_tuple",
                "dimensions": [
                    {
                        "column": "年份",
                        "pattern": [report_year_pattern],
                    }
                ],
            }
        ],
    },
    {
        "path": ["代偿额（母公司）", "代偿率"],
        "sub_primary_key": ["年份"],
        "models": [
            {
                "name": "table_tuple",
                "dimensions": [
                    {
                        "column": "年份",
                        "pattern": [report_year_pattern],
                    }
                ],
                "比率": {
                    "feature_white_list": [
                        r"largest_year_minus_0|当期担保代偿率*",
                        r"largest_year_minus_1|当期担保代偿率*",
                        r"largest_year_minus_2|当期担保代偿率*",
                        r"largest_year_minus_3|当期担保代偿率*",
                    ],
                },
            }
        ],
    },
    {
        "path": ["代偿额（母公司）", "收到归还代偿款"],
        "sub_primary_key": ["年份"],
        "models": [
            {
                "name": "table_tuple",
                "dimensions": [
                    {
                        "column": "年份",
                        "pattern": [report_year_pattern],
                    }
                ],
            }
        ],
    },
    {
        "path": ["代偿额（母公司）", "担保代偿支付的现金"],
        "sub_primary_key": ["年份"],
        "models": [
            {
                "name": "table_tuple",
                "dimensions": [
                    {
                        "column": "年份",
                        "pattern": [report_year_pattern],
                    }
                ],
            }
        ],
    },
]


prophet_config = {"depends": {}, "predictor_options": predictor_options}
