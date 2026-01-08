"""银河证券 7 私募-基金合同"""

FUND_INVESTORS = "基金(投资者|委托人)"

predictor_options = [
    {
        "path": ["基金名称-封面"],
        "models": [
            {
                "name": "middle_paras",
                "include_bottom_anchor": True,
                "top_anchor_regs": [r"私募证券.*基金(?!合同)$"],
                "bottom_anchor_regs": [r"投资基金基金合同"],
                "bottom_anchor_content_regs": [r"(?P<content>.*投资基金)"],
            },
            {
                "name": "fixed_position",
                "positions": list(range(0, 3))[::-1],
                "regs": [r"(?P<dst>[^:：]+?基金)"],
                "neglect_patterns": [r"基金管理人"],
            },
        ],
    },
    {
        "path": ["基金名称"],
        "models": [
            {
                "name": "fund_name",
            },
        ],
    },
    {
        "path": ["基金管理人-名称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "need_match_length": False,
                "regs": [r"基金管理人[:：](?P<dst>.*?)基金托管人"],
                "model_alternative": True,
            }
        ],
    },
    {
        "path": ["基金管理人概况"],
        "models": [
            {
                "name": "kv_cell_text",
                "multi": True,
                "merge_same_key_pairs": True,
                "cell_text_patterns": {
                    "名称": r"名称[:：](?P<dst>.*(?:公司|企业|有限合伙[)）]))住所",
                    "住所": r"住所[:：](?P<dst>.*?)通讯地址",
                    "通讯地址": r"通讯地址[:：](?P<dst>.*?)(法定代表人)",
                    "法定代表人/执行事务合伙人（委派代表）（如有）": r"(法定代表人|执行事务合伙人|法定代表人/执行事务合伙人（委派代表）（如有）)[:：](?P<dst>.*?)在基金业协会(登记|备案)编号",
                    "在基金业协会登记编号": r"在基金业协会(登记|备案)编号[:：](?P<dst>.*?)联系人",
                    "联系人": r"联系人[:：](?P<dst>.*?)联系电话",
                    "联系电话": [
                        r"联系电话[:：](?P<dst>.*?)(传真|网站)",
                        r"联系电话[:：](?P<dst>[\d-]+)",
                    ],
                    "传真": r"传真[:：](?P<dst>(?:(?!网站).)*)",
                    "网站": r"网站[:：](?P<dst>.*)",
                },
            }
        ],
    },
    {
        "path": ["基金托管人-名称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": ["基金托管人概况"],
        "models": [
            {
                "name": "kv_cell_text",
                "cell_text_patterns": {
                    "名称": r"名称[:：](?P<dst>.*公司)",
                    "住所": r"住所[:：](?P<dst>.*?)通讯地址",
                    "通讯地址": r"通讯地址[:：](?P<dst>.*?)(法定代表人|执行事务合伙人)",
                    "法定代表人": r"(法定代表人)[:：](?P<dst>.*?)(联系人|联系电话)",
                    "联系人": r"联系人[:：](?P<dst>.*?)联系电话",
                    "联系电话": r"联系电话[:：](?P<dst>.*)",
                },
            }
        ],
    },
    {
        "path": ["基金服务机构名称及备案编号"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [r"__regex__基金服务机构名称及备案编号"],
            }
        ],
    },
    {
        "path": ["运作方式"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [r"__regex__运作方式"],
            }
        ],
    },
    {
        "path": ["存续期"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [r"__regex__存续期"],
                "regs": ["(?P<dst>.*)封闭期"],
            }
        ],
    },
    {
        "path": ["封闭期"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [r"__regex__封闭期"],
            },
            {
                "name": "row_match",
                "row_pattern": [r"封闭期"],
                "content_pattern": [
                    r"封闭期.*?(?P<dst>(?:\d+个月|无))",
                ],
            },
        ],
    },
    {
        "path": ["开放日"],
        "models": [
            {
                "name": "open_day",
            }
        ],
    },
    {
        "path": ["临时开放日"],
        "models": [
            {
                "name": "open_day",
            },
            {
                "name": "row_match",
                "row_pattern": [r"临时开放日"],
                "content_pattern": [
                    r"临时开放日(?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["结构化安排"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [r"__regex__结构化安排"],
            }
        ],
    },
    {
        "path": ["投资顾问"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [r"__regex__投资顾问"],
            }
        ],
    },
    {
        "path": ["基金投资经理"],
        "sub_primary_key": ["名称"],
        "models": [
            {
                "name": "fund_account",
                "cell_text_patterns": {
                    "名称": [
                        r"姓名和简历[:：](?P<dst>.{2,4})，",
                        r"姓名[:：](?P<dst>.{2,4})(简[历介]|，|先生|女士)",
                        r"。(?P<dst>.{2,4})[，]?简历",
                    ],
                    "简介": [
                        r"简[历介][:：；](?P<dst>.*?(硕士|本科).*?(擅长信用债等固定收益类资产的投资|已取得基金从业资格并在协会完成注册)。)",
                        r"姓名和简历[:：].{2,4}，(?P<dst>.*?)姓名",
                        r"简[历介][:：](?P<dst>[^姓]+)",
                        r"(^(\d[.])?.{2,4}|姓名[:：].{2,4})[，先生女士]+(?P<dst>[^姓]*)",
                    ],
                },
                "row_tag_pattern": [r"基金投资经理"],
                "reassemble_with_supervision": True,
                "multi": True,
            },
            {
                "name": "fund_account",
                "cell_text_patterns": {
                    "名称": [
                        r"姓名[:：](?P<dst>.{2,4})(简[历介]|，|先生|女士)",
                        r"^(\d[.])?(?P<dst>.{2,4})(简[历介]|，|先生|女士)",
                    ],
                    "简介": [
                        r"简[历介][:：](?P<dst>[^姓]*)",
                        r"(^(\d[.])?.{2,4}|姓名[:：].{2,4})[，先生女士]+(?P<dst>[^姓]*)",
                    ],
                },
                "row_tag_pattern": [r"基金投资经理"],
                "reassemble_with_supervision": True,
                "multi": True,
            },
            {
                "name": "fund_account",
                "cell_text_patterns": {
                    "名称": [
                        r"投资经理名称及简介[:：](?P<dst>.{2,4})，",
                        r"。(?P<dst>.{2,4})[，]现任",
                    ],
                    "简介": [
                        r"，(?P<dst>现任.*?。)",
                    ],
                },
                "row_tag_pattern": [r"基金投资经理"],
                "reassemble_with_supervision": True,
                "multi": True,
            },
        ],
    },
    {
        "path": ["基金管理团队"],
        "models": [
            {
                "name": "investment_scope",
                "row_tag_pattern": r"基金管理团队",
            }
        ],
    },
    {
        "path": ["投资目标、投资方式"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [
                    r"__regex__投资目标、投资方式",
                    r"__regex__投资目标",
                ],
            }
        ],
    },
    {
        "path": ["基金投资策略", "基金投资策略-基金基本情况表"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [r"__regex__基金投资策略"],
            }
        ],
    },
    {
        "path": ["基金投资策略", "正文-投资策略"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金投资范围", "基金投资范围-基金基本情况表"],
        "models": [
            {
                "name": "investment_scope",
                "row_tag_pattern": r"基金投资范围",
                "table_config": {
                    "split_pattern": r"[;；。]",
                    "keep_separator": True,
                    "garbage_frag_pattern": [r"^[)）]$"],
                },
            }
        ],
    },
    {
        "path": ["基金投资范围", "正文-投资范围"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["投资比例、限制", "投资比例、限制-基金基本情况表"],
        "models": [
            {
                "name": "investment_scope",
                "use_complete_table": True,
                "row_tag_pattern": [
                    r"投资比例、?限制",
                    r"投资限制",
                ],
                "table_config": {
                    "split_pattern": r"[;；。]",
                },
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"投资者声明", r"基金基本情况表"],
                "extract_from": "same_type_elements",
                "only_inject_features": True,
                "table_model": "table_kv",
                "table_config": {
                    "use_complete_table": True,
                    "split_pattern": r"[;；。]",
                    "feature_white_list": [
                        r"__regex__投资限制",
                        r"__regex__投资比例[、及]?限制",
                    ],
                },
            },
        ],
    },
    {
        "path": ["投资比例、限制", "投资比例、限制-正文"],
        "models": [
            {
                "name": "syllabus_elt",
                "feature_white_list": [r"__regex__投资限制"],
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
            }
        ],
    },
    {
        "path": ["由托管人开展日常监控的具体项目"],
        "models": [
            {
                "name": "monitor_procedures",
                "row_tag_pattern": [r"由托管人开展日常监控的具体项目|托管人日常监督具体项目"],
                "aim_index": 1,
                "multi": True,
            }
        ],
    },
    {
        "path": ["初始募集面值"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [r"__regex__初始募集面值"],
                "regs": [
                    r"(?P<dst>[\d.]+元)",
                    r"(?P<dst>.*)预计募集总额",
                ],
            }
        ],
    },
    {
        "path": ["预计募集总额"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "use_complete_table": True,
                "feature_white_list": [r"__regex__预计募集总额"],
            },
            {
                "name": "row_match",
                "row_pattern": [r"预计募集总额"],
                "content_pattern": [
                    r"预计募集总额(?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["募集方式"],
        "models": [
            {
                "name": "table_kv",
                "feature_white_list": [r"__regex__募集方式"],
                "use_complete_table": True,
            },
            {
                "name": "row_match",
                "row_pattern": [r"募集方式"],
                "content_pattern": [
                    r"(?P<dst>代销$)",
                ],
            },
        ],
    },
    {
        "path": ["募集期限"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [r"__regex__募集期限"],
            }
        ],
    },
    {
        "path": ["募集机构"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [r"__regex__募集机构"],
                "regs": [r"(?P<dst>.+)"],
                "only_matched_value": True,
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"投资者声明"],
                "only_inject_features": True,
                "table_model": "table_kv",
                "table_config": {
                    "use_complete_table": True,
                    "feature_white_list": [r"__regex__募集机构及.*?机构"],
                    "regs": [
                        r"(?P<dst>基金管理人（直销）)",
                        r"(?P<dst>基金管理人委托基金销售机构（代销）)",
                    ],
                    "only_matched_value": True,
                },
            },
        ],
    },
    {
        "path": ["募集结算资金专用账户及监督机构"],
        "sub_primary_key": ["账户类型", "账户号"],
        "models": [
            {
                "name": "fund_account",
                "use_complete_table": True,
                "cell_text_patterns": {
                    "账户类型": [
                        r"(?P<dst>直销情况下募集结算资金归集账户)信息如下",
                        r"(?P<dst>注册登记账户)信息如下.*?[：:]",
                        r"(?P<dst>募集结算资金归集账户-代销机构[付收]款账户)",
                    ],
                    "账户名称": r"账户名称?[:：](?P<dst>.*?)(账户?号|(开户银?行))",
                    "账户号": [
                        r"账户?号[:：]?(?P<dst>.*?)((开户银?行)|账户名)",
                        r"账户?号[:：]?(?P<dst>\d+)$",
                    ],
                    "开户银行": r"(开户银?行)[:：](?P<dst>.{,50}[银支分]行(营业部)?)",
                    "大额支付系统号": r"大额支付系统号[:：](?P<dst>\d{3,})",
                },
                "row_tag_pattern": [
                    r"募集结算资金专用账户及监督机构",
                    r"募集结算资金专用账户$",
                ],
                "reassemble_with_supervision": True,
                "multi": True,
                "multi_elements": True,
            },
            {
                "name": "syllabus_based",
                "extract_from": "same_type_elements",
                "inject_syllabus_features": [r"投资者声明"],
                "only_inject_features": True,
                "paragraph_model": "empty_answer",
                "table_model": "fund_account",
                "table_config": {
                    "use_complete_table": True,
                    "cell_text_patterns": {
                        "账户类型": [
                            r"(?P<dst>直销情况下募集结算资金归集账户)信息如下",
                            r"(?P<dst>注册登记账户)信息如下.*?[：:]",
                            r"(?P<dst>募集结算资金归集账户-代销机构[付收]款账户)",
                        ],
                        "账户名称": r"账户名称?[:：](?P<dst>.*?)(账户?号|(开户银?行))",
                        "账户号": [
                            r"账户?号[:：]?(?P<dst>.*?)((开户银?行)|账户名)",
                            r"账户?号[:：]?(?P<dst>\d{8,}$)",
                        ],
                        "开户银行": r"(开户银?行)[:：](?P<dst>.{,50}[银支分]行(营业部)?)",
                        "大额支付系统号": r"大额支付系统号[:：](?P<dst>\d{3,})",
                    },
                    "row_tag_pattern": [
                        r"募集结算资金专用账户及监督机构",
                        r"募集结算资金专用账户$",
                    ],
                    "reassemble_with_supervision": True,
                    "multi": True,
                },
            },
        ],
    },
    {
        "path": ["募集机构的回访确认制度"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [r"__regex__募集机构的回访确认制度"],
            }
        ],
    },
    {
        "path": ["募集对象"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [r"__regex__募集对象"],
            }
        ],
    },
    {
        "path": ["本基金的风险等级"],
        "models": [
            {
                "name": "row_match",
                "use_complete_table": True,
                "row_pattern": [r"风险收益特征"],
                "content_pattern": [
                    r"本基金属于【?(?P<dst>R\d)】?风险等级",
                ],
            }
        ],
    },
    {
        "path": ["适合的投资者风险承受能力等级"],
        "models": [
            {
                "name": "row_match",
                "use_complete_table": True,
                "row_pattern": [r"风险收益特征.*承受能力为.{,4}(及以上)?等级"],
                "content_pattern": [
                    r"风险收益特征.*承受能力为(?P<dst>【?.{,2}】?(及以上)?等级.*投资者)",
                ],
            },
        ],
    },
    {
        "path": ["认购费", "正文-认购费"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["认购费", "认购费-基金基本情况表"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [r"__regex__认购费"],
            }
        ],
    },
    {
        "path": ["申购费"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [r"__regex__申购费"],
            }
        ],
    },
    {
        "path": ["最小追加认/申购单位"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [r"__regex__最小追加认[/]申购单位"],
            }
        ],
    },
    {
        "path": ["赎回费", "赎回费"],
        "models": [
            {
                "name": "fund_account",
                "cell_text_patterns": {
                    "赎回费": [
                        r"(?P<dst>份额持有期限低于.*赎回费率为.*份额持有期限.*以上.*赎回费率为.*%)",
                        r"(?P<dst>自委托人认购.+收取.+赎回费.*不收取)",
                        rf"(?P<dst>本{FUND_INVESTORS}持有期不足.*赎回费费率为.*本{FUND_INVESTORS}持有期.*免赎回费)",
                        r"(?P<dst>本基金份额持有.*%)",
                        r"(?P<dst>赎回费率?为?.+%?)",
                        r"(?P<dst>不限金额，赎回费率为0)",
                        r"(?P<dst>(本基金)?不收取赎回费)",
                        r"(?P<dst>本基金的赎回费率随基金份额持有期限的增加而递减.*进行计算)",
                        r"(?P<dst>持有份额不满.*不收取赎回费)",
                        r"(?P<dst>^无。?$)",
                    ],
                },
                "row_tag_pattern": [r"赎回费"],
            }
        ],
    },
    {
        "path": ["赎回费", "赎回费是否归属基金资产"],
        "models": [
            {
                "name": "fund_account",
                "cell_text_patterns": {
                    "赎回费是否归属基金资产": r"(?P<dst>赎回费(是否|不)?归属(基金资产|管理人).*)",
                },
                "row_tag_pattern": [r"赎回费"],
            }
        ],
    },
    {
        "path": ["基金管理费"],
        "models": [
            {
                "name": "operate_expenses",
                "regs": [
                    r"(?P<dst>(本基金[ABC]类|[ABC]类份额.)?基金(份额的?)?管理年?费率.*?(%|元/年))",
                    r"基金(份额的?)?管理年?费率.*?(?P<dst>[ABC]类份额.无)",
                    r"基金管理费[:：](?P<dst>.*)",
                    r"(?P<dst>本基金不按天计提管理费，仅在产品终止时计提管理费.*管理费收取方式不变。)",
                    r"基金管理人的管理费年费率[:：](?P<dst>.*?/年)",
                ],
            }
        ],
    },
    {
        "path": ["基金管理费-计提方法、计提标准和支付方式"],
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
        "path": ["基金托管费"],
        "models": [
            {
                "name": "operate_expenses",
                "regs": [
                    r"(?P<dst>基金托管年?费率.*)",
                    r"基金托管人的托管费年费率[:：](?P<dst>.*?/年)",
                ],
            }
        ],
    },
    {
        "path": ["基金托管费-计提方法、计提标准和支付方式"],
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
        "path": ["基金服务费"],
        "models": [
            {
                "name": "operate_expenses",
                "regs": [
                    r"(?P<dst>基金服务年?费率.*)",
                    r"基金服务机构的基金服务费年费率[:：](?P<dst>.*?/年)",
                ],
            }
        ],
    },
    {
        "path": ["基金服务费-计提方法、计提标准和支付方式"],
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
        "path": ["其他费用", "其他费用-基金基本情况表"],
        "models": [
            {
                "name": "operate_expenses",
                "regs": [
                    r"(?P<dst>其他费用.*([元无]|以实际发生金额为准))",
                ],
            }
        ],
    },
    {
        "path": ["其他费用", "正文-其他费用"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["估值核对频率", "估值核对频率"],
        "models": [
            {
                "name": "fund_account",
                "cell_text_patterns": {
                    "估值核对频率": [
                        r"本基金管理人和托管人按照以下频率进行估值核对[:：](?P<dst>.?[工作日自然周月季度]+)",
                        r"(?P<dst>(本基金管理人和托管人按照)?.*?进行估值核对)",
                    ],
                },
                "row_tag_pattern": r"估值核对频率",
            }
        ],
    },
    {
        "path": ["估值核对频率", "估值核对频率补充内容"],
        "models": [
            {
                "name": "fund_account",
                "cell_text_patterns": {
                    "估值核对频率补充内容": r"(?P<dst>若按周、月、季进行估值核对，则分别在每周、月、季（1、4、7、10月）的第一个工作日.*)",
                },
                "row_tag_pattern": r"估值核对频率",
            }
        ],
    },
    {
        "path": ["业绩报酬-计算方式"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"基金基本情况表"],
                "only_inject_features": True,
                "extract_from": "same_type_elements",
                "table_model": "table_kv",
                "table_config": {
                    "use_complete_table": True,
                    "feature_white_list": [r"__regex__业绩报酬计算方式"],
                    "regs": [r"(?P<dst>.*业绩报酬计算公式如下.*)"],
                    "only_matched_value": True,
                    "multi": True,
                },
            },
            {
                "name": "performance_calc",
                "row_tag_pattern": [r"业绩报酬计算方式"],
            },
        ],
    },
    {
        "path": ["业绩报酬-支付方式"],
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
        "path": ["基金管理费收费账户（业绩报酬收费账户）"],
        "models": [
            {
                "name": "fund_account",
                "cell_text_patterns": {
                    "账户名称": r"账户名称[:：](?P<dst>(.*?[(（]?(公司|有限合伙)[)）]?|[XYWA]+))",
                    "开户行": r"开户(?:行|银行全称)[:：](?P<dst>.*[银支分]行(营业部)?)(账号|大额支付系统号)",
                    "账号": r"账户?号[:：](?P<dst>[\dXYWA]+)(账号|开户(?:行|银行全称)|大额支付系统号)",
                    "大额支付系统号": r"(大额支付系统号)[:：](?P<dst>[\dXYWA]+)",
                },
                "row_tag_pattern": [r"基金管理费?收费账户|业绩报酬收费账户"],
                "multi": True,
            }
        ],
    },
    {
        "path": ["基金托管费收费账户"],
        "models": [
            {
                "name": "fund_account",
                "cell_text_patterns": {
                    "账户名称": r"账户名称[:：](?P<dst>(.*?[(（]?(公司|有限合伙)[)）]?|[XYWA]+))",
                    "开户行": r"开户行[:：](?P<dst>.*[银支分]行(营业部)?)(账号|大额支付系统号)",
                    "账号": [
                        r"账户?号[:：](?P<dst>[\dXYWA]+)(账号|开户行|大额支付系统号)",
                        r"账户?号[:：](?P<dst>[\d]+)$",
                    ],
                    "大额支付系统号": r"(大额支付系统号)[:：](?P<dst>[\dXYWA]+)",
                },
                "row_tag_pattern": [r"基金托管费收费账户"],
                "multi": True,
            },
        ],
    },
    {
        "path": ["基金服务费收费账户"],
        "models": [
            {
                "name": "fund_account",
                "cell_text_patterns": {
                    "账户名称": r"账户名称[:：](?P<dst>.*?公司)",
                    "开户行": r"开户行[:：](?P<dst>.*)账号",
                    "账号": r"账号[:：](?P<dst>.*)大额支付系统号",
                    "大额支付系统号": r"(大额支付系统号)[:：](?P<dst>.*)",
                },
                "row_tag_pattern": [r"基金服务费收费账户"],
                "multi": True,
            }
        ],
    },
    {
        "path": ["基金委托人人数上限"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"基金委托人人数(规模)?上限为(?P<dst>.*?人)"],
                "model_alternative": True,
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"认购申请的确认及认购金额限制"],
                "only_inject_features": True,
                "extract_from": "same_type_elements",
                "paragraph_model": "partial_text",
                "para_config": {"regs": [r"基金委托人人数(规模)?上限为(?P<dst>.*?人)"]},
            },
        ],
    },
    {
        "path": ["基金募集失败的处理方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__私募基金的募集__regex__基金募集失败的处理方式",
                ],
                "only_inject_features": True,
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
        "path": ["基金合同的签署方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["赎回款支付时限"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(?P<content>基金份额持有人赎回申请确认成功后.*)",
            }
        ],
    },
    {
        "path": ["巨额赎回的认定"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>开放日.*?本私募基金发生了巨额赎回)",
                    r"(?P<content>本基金不设置巨额赎回条款)",
                    r"(?P<content>基金的成立日.*)",
                    r"(?P<content>募集资金划转至托管资金账户后.*)",
                ),
            }
        ],
    },
    {
        "path": ["基金管理人的权利"],
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
        "path": ["基金管理人的义务"],
        "models": [
            {
                "name": "syllabus_elt",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"基金管理人的义务"],
            },
        ],
    },
    {
        "path": ["私募基金托管人的权利"],
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
        "path": ["私募基金托管人的义务"],
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
        "path": ["基金委托人的权利"],
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
        "path": ["基金委托人的义务"],
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
        "path": ["召开基金份额持有人大会的情形"],
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
        "path": ["建仓期及投资比例调整"],
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
        "path": ["投资禁止行为"],
        "models": [
            {
                "name": "syllabus_elt",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__投资(比例及)?限制"],
                "extract_from": "same_type_elements",
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": False,
                    "include_bottom_anchor": True,
                    "top_anchor_regs": [r"本(私募)?基金财产禁止从事下列行为"],
                    "bottom_anchor_regs": [r"法律法规.*以及本基金合同规定禁止从事的其它行为"],
                },
            },
        ],
    },
    {
        "path": ["预警止损机制", "预警止损机制-正文"],
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
        "path": ["预警机制"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__正文目录__regex__私募基金的投资__regex__预警止损机制"],
                "only_inject_features": True,
                "extract_from": "same_type_elements",
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"基金份额净值不高于预警线时"],
                },
            }
        ],
    },
    {
        "path": ["止损机制"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__正文目录__regex__私募基金的投资__regex__预警止损机制"],
                "only_inject_features": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"(?P<content>.*本基金提前终止并进入清算程序)"],
                },
            }
        ],
    },
    {
        "path": ["预警非现金仓位控制"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__正文目录__regex__私募基金的投资__regex__预警止损机制"],
                "only_inject_features": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"非现金基金资产占基金净值的比例下降至(?P<content>.*)以内"],
                },
            }
        ],
    },
    {
        "path": ["预警止损机制", "预警线"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [
                    r"__regex__预警线.(基金)?份额净值.",
                    r"__regex__预警线",
                ],
                "regs": [r"(?P<dst>.*?)止损线"],
                "only_matched_value": True,
            },
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [
                    r"__regex__预警线.(基金)?份额净值.",
                    r"__regex__预警线",
                ],
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__正文目录__regex__私募基金的投资__regex__预警止损机制"],
                "only_inject_features": True,
                "extract_from": "same_type_elements",
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"预警线为.?(?P<content>[\d.]+)"],
                },
            },
        ],
    },
    {
        "path": ["预警止损机制", "止损线"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "feature_white_list": [
                    r"__regex__预警线.(基金)?份额净值.",
                    r"__regex__预警线",
                ],
                "regs": [
                    r"止损线.(基金)?份额净值.(?P<dst>.*)",
                    r"止损线(?P<dst>.*)",
                ],
                "only_matched_value": True,
            },
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "use_complete_table": True,
                "feature_white_list": [r"__regex__止损线.(基金)?份额净值."],
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__正文目录__regex__私募基金的投资__regex__预警止损机制"],
                "only_inject_features": True,
                "extract_from": "same_type_elements",
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"止损线为.?(?P<content>[\d.]+)"],
                },
            },
        ],
    },
    {
        "path": ["选择证券经纪机构的数量"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["选择期货经纪机构的数量"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["估值时间"],
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
        "path": ["估值方法"],
        "models": [
            {
                "name": "syllabus_elt",
                "feature_white_list": ["估值依据和方法"],
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
            }
        ],
    },
    {
        "path": ["估值对象"],
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
        "path": ["估值错误的处理"],
        "models": [
            {
                "name": "split_by_reg",
                "split_pattern": r"(?P<dst>估值错误的处理)",
            }
        ],
    },
    {
        "path": ["暂停估值的情形"],
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
        "path": ["收益分配的执行方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__收益分配的执行方式",
                ],
                "only_inject_features": True,
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
        "path": ["基金运作期间的信息披露种类、内容和频率"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金合同变更的条件和程序"],
        "models": [
            {
                "name": "syllabus_elt",
                "feature_white_list": [r"基金合同的效力、变更、解除与终止|基金合同变更的条件和程序"],
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
            }
        ],
    },
    {
        "path": ["基金合同终止的情形"],
        "models": [
            {
                "name": "syllabus_elt",
                "feature_white_list": [r"基金合同的效力、变更、解除与终止|基金合同终止的情形"],
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
            }
        ],
    },
    {
        "path": ["基金合同的展期"],
        "models": [
            {
                "name": "syllabus_elt",
                "feature_white_list": [r"基金合同的效力、变更、解除与终止|基金合同的展期"],
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
            }
        ],
    },
    {
        "path": ["争议处理方式"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (r"(?P<content>协商.*?调解.*?仲裁委员会.*?申请仲裁)",),
            }
        ],
    },
    {
        "path": ["投资范围-监督程序和频率"],
        "models": [
            {
                "name": "monitor_procedures",
                "row_tag_pattern": [r"投资范围"],
                "overhead_cell_pattern": [r"监督程序和频率"],
            }
        ],
    },
    {
        "path": ["由托管人开展日常监控的具体项目-监督程序和频率"],
        "models": [
            {
                "name": "monitor_procedures",
                "row_tag_pattern": [r"由托管人开展日常监控的具体项目|托管人日常监督具体项目"],
            }
        ],
    },
    {
        "path": ["投资风格-监督程序和频率"],
        "models": [
            {
                "name": "monitor_procedures",
                "row_tag_pattern": [r"投资风格"],
            }
        ],
    },
    {
        "path": ["关联交易-监督程序和频率"],
        "models": [
            {
                "name": "monitor_procedures",
                "row_tag_pattern": [r"关联交易"],
            }
        ],
    },
    {
        "path": ["预警止损机制-监督程序和频率"],
        "models": [
            {
                "name": "monitor_procedures",
                "row_tag_pattern": [r"预警止损机制"],
                "need_next_element": True,
            }
        ],
    },
    {
        "path": ["管理人风控经理联系方式"],
        "models": [
            {
                "name": "fund_account",
                "use_complete_table": True,
                "cell_text_patterns": {
                    "联系人（风控经理）": r"联系人（风控经理）[:：](?P<dst>.*)",
                    "电子邮箱": r"电子邮箱[:：](?P<dst>.*)",
                    "固定电话": r"固定电话[:：](?P<dst>.*)",
                    "手机号码": r"手机号码[:：](?P<dst>.*)",
                },
                "row_tag_pattern": r"管理人(提供)?风控经理联系方式",
            },
            {
                "name": "table_kv",
                "use_complete_table": True,
                "only_matched_value": True,
                "feature_white_list": [
                    r"__regex__^管理人提供$|^风控经理联$|^系方式，用$|^于托管人沟$|^通管理人投$|^资监督事项$",
                ],
                "联系人（风控经理）": {
                    "regs": [r"联系人（风控经理）[:：](?P<dst>.*)"],
                },
                "电子邮箱": {
                    "regs": [
                        r"电子邮箱[:：](?P<dst>.*)",
                    ],
                },
                "固定电话": {
                    "regs": [
                        r"固定电话[:：](?P<dst>.*)",
                    ],
                },
                "手机号码": {
                    "regs": [
                        r"手机号码[:：](?P<dst>.*)",
                    ],
                },
            },
        ],
    },
    {
        "path": ["募集结算资金归集账户监督机构"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"投资者声明"],
                "extract_from": "same_type_elements",
                "paragraph_model": "empty_answer",
                "table_model": "fund_account",
                "table_config": {
                    "multi": True,
                    "row_tag_pattern": [r"募集结算资金专用账户及监督机构"],
                    "cell_text_patterns": {
                        "募集结算资金归集账户监督机构": r"募集结算资金归集账户监督机构[:：](?P<dst>.*?公司)",
                    },
                },
            },
        ],
    },
    {
        "path": ["业绩报酬提取条件"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"投资者声明"],
                "extract_from": "same_type_elements",
                "paragraph_model": "empty_answer",
                "table_model": "fund_account",
                "table_config": {
                    "row_tag_pattern": [r"业绩报酬计算方式"],
                    "cell_text_patterns": {
                        "业绩报酬提取条件": [
                            r"(?P<dst>本基金针?对.类份额投资者不?收取业绩报酬.对.类.*?收取业绩报酬)",
                            r"(?P<dst>当R.*时.*业绩报酬E\s*=.*?[%％])；E=该笔投资对应",
                            r"(?P<dst>A类份额基金管理人提取全部收益部分的[\d.]{1,5}%作为业绩报酬；B类份额基金管理人不提取业绩报酬)",
                            r"(?P<dst>年化收益率（R）业绩报酬（E）R.*365)",
                            r"(?P<dst>本基金在.*?时计提业绩报酬。)",
                            r"(?P<dst>本基金.类份额不计提业绩报酬.(基金)?.类份额.*)业绩报酬的计算方法",
                            r"(?P<dst>期间年化收益率收取比例业绩报酬计算公式R.*\d+.*365[)])E=该笔投资对应",
                            r"(?P<dst>本基金针?对.类.*不?收取业绩报酬.本基金对.类基金份额类别条款如下)",
                            r"(?P<dst>业绩报酬计提标准.*R.*\d+.*365)",
                            r"(?P<dst>R.*\d+.*365)E=该笔投资对应",
                        ]
                    },
                },
            },
        ],
    },
    {
        "path": ["业绩报酬提取比例"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"投资者声明"],
                "extract_from": "same_type_elements",
                "paragraph_model": "empty_answer",
                "table_model": "fund_account",
                "table_config": {
                    "multi": True,
                    "row_tag_pattern": [r"业绩报酬计算方式"],
                    "cell_text_patterns": {
                        "业绩报酬提取比例": [
                            r"E=.*?×(?P<dst>[\d.]{1,5}[%％])",
                            r"业绩报酬的?(计提|提取)比例.{0,3}为(?P<dst>[\d.【】]{1,5}[%％])",
                            r"E=.*?[^×\d](?P<dst>[\d.]{1,5}[%％])(.T/365|×[(]T÷365[)])",
                            r"R=(?P<dst>[\d.]{1,5}[%％]).为基金份额业绩报酬提取比例",
                            r"基金管理人提取全部收益部分的(?P<dst>[\d.]{1,5}[%％])作为业绩报酬",
                        ]
                    },
                },
            },
        ],
    },
    {
        "path": ["订立基金合同的目的、依据和原则"],
        "models": [
            {
                "name": "middle_paras",
                "include_top_anchor": False,
                "top_anchor_regs": [r"订立基金合同的目的"],
                "bottom_anchor_regs": [r"基金合同是规定基金合同当事人之间权利义务关系的基本法律文件"],
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金委托人的声明与承诺"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"基金委托人的声明与承诺"],
            }
        ],
    },
    {
        "path": ["基金管理人的声明与承诺"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金托管人的声明与承诺"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["投资冷静期"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"从签署.*?算.*?基金委托人有.*?投资冷静期"],
                "model_alternative": True,
            }
        ],
    },
    {
        "path": ["募集机构、对象、方式及期限"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["特殊合格投资者"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"私募基金的募集"],
                "extract_from": "same_type_elements",
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": False,
                    "include_bottom_anchor": True,
                    "top_anchor_regs": [r"特殊合格投资者"],
                    "neglect_top_anchor": [r"[^\u4e00-\u9fa5]合格投资者包括"],
                    "bottom_anchor_regs": [
                        r"规定的其他投资者",
                        r"本私募基金的基金委托人人数规模上限",
                    ],
                    "top_anchor_range_regs": [r"合格投资者"],
                    "bottom_anchor_range_regs": [r"认购申请的确认"],
                },
            },
            {
                "name": "para_match",
                "paragraph_pattern": (r"特殊合格投资者.*?[:：](?P<content>.*)",),
                "content_pattern": (r"特殊合格投资者.*?[:：](?P<content>.*)",),
            },
        ],
    },
    {
        "path": ["认购申请的确认及认购金额限制"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["募集-投资者冷静期及回访确认"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__投资者冷静期及回访确认",
                ],
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__私募基金的募集",
                ],
                "ignore_syllabus_children": True,
                "paragraph_model": "middle_paras",
                "extract_from": "same_type_elements",
                "para_config": {
                    "use_direct_elements": True,
                    "top_anchor_regs": [r"基金委托人有.*?投资冷静期"],
                    "bottom_anchor_regs": [r"基金份额持有限额"],
                },
            },
        ],
    },
    {
        "path": ["基金份额的计算"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金成立的条件"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金的成立日"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"管理人有权决定基金的具体成立日期.*?基金的成立日以基金管理人发布的公告所载日期为准。"
                ],
            },
        ],
    },
    {
        "path": ["基金的备案"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["申购和赎回的办理机构"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["申购和赎回的开放日"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["申购和赎回的预约登记"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"申购和赎回的预约申请方式",
                ],
            }
        ],
    },
    {
        "path": ["申购和赎回的方式、价格及程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["申购和赎回申请的确认"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["申购-投资冷静期及回访确认"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__^.{,5}投资冷静期及回访确认$"],
            },
        ],
    },
    {
        "path": ["申购和赎回的金额限制"],
        "models": [{"name": "syllabus_elt_v2", "inject_syllabus_features": [r"__regex__申购和赎回的限制"]}],
    },
    {
        "path": ["申购和赎回的费用"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["在如下情形下，基金管理人可以拒绝接受基金投资者的申购申请"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    rf"__regex__在如下情形下，基金管理人可以拒绝接受{FUND_INVESTORS}的申购申请"
                ],
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__拒绝或暂停申购、暂停赎回的情形及处理",
                ],
                "ignore_syllabus_children": True,
                "paragraph_model": "middle_paras",
                "extract_from": "same_type_elements",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": False,
                    "top_anchor_regs": [rf"在如下情形下，基金管理人可以拒绝接受{FUND_INVESTORS}的申购申请"],
                    "bottom_anchor_regs": [rf"在如下情形下，基金管理人可以暂停接受{FUND_INVESTORS}的申购申请"],
                },
            },
        ],
    },
    {
        "path": ["在如下情形下，基金管理人可以暂停基金投资者的申购"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [rf"__regex__在如下情形下，基金管理人可以暂停{FUND_INVESTORS}的申购"],
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__拒绝或暂停申购、暂停赎回的情形及处理",
                ],
                "ignore_syllabus_children": True,
                "paragraph_model": "middle_paras",
                "extract_from": "same_type_elements",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": False,
                    "top_anchor_regs": [rf"在如下情形下，基金管理人可以暂停接受{FUND_INVESTORS}的申购申请"],
                    "bottom_anchor_regs": [r"在如下情形下，基金管理人可以暂停接受基金份额持有人的赎回申请"],
                },
            },
        ],
    },
    {
        "path": ["在如下情形下，基金管理人可以暂停基金份额持有人的赎回"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": ["在如下情形下，基金管理人可以暂停基金份额持有人的赎回"],
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__拒绝或暂停申购、暂停赎回的情形及处理",
                ],
                "ignore_syllabus_children": True,
                "paragraph_model": "middle_paras",
                "extract_from": "same_type_elements",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": False,
                    "top_anchor_regs": [r"在如下情形下，基金管理人可以暂停接受基金份额持有人的赎回申请"],
                    "include_bottom_anchor": True,
                    "bottom_anchor_regs": [
                        r"在暂停赎回的情况消除时，基金管理人应及时恢复赎回业务的办理并以公告形式告知基金份额持有人。"
                    ],
                },
            },
        ],
    },
    {
        "path": ["巨额赎回的处理方式"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__正文目录__regex__私募基金的申购、赎回与转让__regex__巨额赎回的认定及处理方式__regex__巨额赎回的处理方式",
                    r"__regex__巨额赎回的认定及处理方式",
                ],
                "ignore_syllabus_children": True,
                "paragraph_model": "middle_paras",
                "extract_from": "same_type_elements",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": False,
                    "include_bottom_anchor": True,
                    "top_anchor_regs": [
                        r"巨额赎回的处理方式",
                        r"发生了巨额赎回.$",
                    ],
                    "bottom_default": True,
                },
            }
        ],
    },
    {
        "path": ["基金份额的转让"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金的非交易过户"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金份额的冻结与解冻"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金份额持有人大会的组成"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["召集人和召集方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["召开会议的通知时间、通知内容、通知方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["出席会议的方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["议事内容与程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["决议形成的条件、表决方式、程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金份额持有人大会决议的效力"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金份额持有人大会决议的披露"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"__regex__基金份额持有人大会决议的披露"],
                "only_inject_features": True,
                "top_default": True,
                "bottom_anchor_regs": [r"本基金存续期间"],
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["代为办理私募基金份额登记机构的职责"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金份额持有人名册的保管"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["越权交易的界定"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["越权交易的处理程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__越权交易的处理程序(如下)?[:：]?"],
            },
        ],
    },
    {
        "path": ["不属于越权交易的情形"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"__regex__越权交易的处理程序如下[:：]"],
                "only_inject_features": True,
                "include_top_anchor": False,
                "top_anchor_regs": [r"以下情况不属于越权交易"],
                "bottom_anchor_regs": [r"基金委托人确认"],
                "bottom_default": True,
            },
        ],
    },
    {
        "path": ["关联关系、关联交易及利益冲突的情形"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["关联交易及利益冲突情形的处理 "],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["非证券市场交易 "],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["关于穿透原则的特殊约定"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金财产的保管与处分"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["托管资金账户的开设和管理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金的证券账户和证券资金账户的开设和管理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["期货账户的开立管理"],
        "models": [{"name": "syllabus_elt_v2", "inject_syllabus_features": [r"__regex__股指期货账户的开立管理"]}],
    },
    {
        "path": ["其它账户的开设和管理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["与基金财产有关的重大合同的保管"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["选择证券、期货经纪机构的程序"],
        "models": [{"name": "syllabus_elt_v2", "inject_syllabus_features": [r"选择证券、期货经纪机构"]}],
    },
    {
        "path": ["资金清算交收安排"],
        "models": [
            {
                "name": "middle_paras",
                "include_top_anchor": True,
                "top_default": True,
                "bottom_default": True,
                "top_anchor_regs": [r"资金清算交收安排"],
                "bottom_anchor_regs": [r"证券账目及交易记录的核对"],
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资金、证券账目及交易记录的核对"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["申购、赎回的资金清算"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金管理人对预留印鉴授权及更换授权人的程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["投资指令的内容"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["投资指令的发送"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"投资指令的发送、确认和执行的时间和程序"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["投资指令的确认"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"投资指令的发送、确认和执行的时间和程序"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["投资指令的执行"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"投资指令的发送、确认和执行的时间和程序"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["基金托管人依照法律法规暂缓、拒绝执行指令的情形和处理程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金管理人发送错误指令的情形和处理方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["投资指令的保管"],
        "models": [{"name": "syllabus_elt_v2", "inject_syllabus_features": [r"指令的保管"]}],
    },
    {
        "path": ["交易及清算交收安排-相关责任"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["估值目的"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["估值程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["估值错误类型"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["估值错误处理原则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["估值错误处理程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金份额净值的确认"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["估值材料的交互要求"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金的会计政策"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金费用的种类"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["不列入基金管理业务费用的项目"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"不列入基金管理业务费用的项目"],
            }
        ],
    },
    {
        "path": ["基金管理业务的税收"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金收益分配原则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金收益分配方案的确定和通知"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金管理人的信息披露责任义务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"基金业务报告和财务报告提交制度"],
            }
        ],
    },
    {
        "path": ["基金管理人披露基金信息，不得有下列行为"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": False,
                "top_anchor_regs": [r"下列行为"],
                "include_bottom_anchor": True,
                "bottom_default": True,
            },
        ],
    },
    {
        "path": ["基金托管人的信息披露责任义务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["年度报告"],
        "models": [
            {"name": "syllabus_elt_v2", "neglect_patterns": [r"(季|月)度报告"]},
        ],
    },
    {
        "path": ["重大事项临时报告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"基金管理人重大事项临时报告"],
            }
        ],
    },
    {
        "path": ["基金管理人向投资者提供报告及信息查询的方式和渠道"],
        "models": [
            {"name": "syllabus_elt_v2", "inject_syllabus_features": [r"基金管理人向投资者提供报告及信息查询的方式"]}
        ],
    },
    {
        "path": ["向基金业协会提供的报告"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "top_default": True,
                "bottom_anchor_regs": [r"基金管理人可自行或通过第三方机构进行基金份额净值数据的信息披露事项"],
                "include_bottom_anchor": False,
            },
            {
                "name": "para_match",
                "anchor_regs": [r"向基金业协会提供的报告"],
                "paragraph_pattern": [r"基金管理人.+平台报送信息"],
            },
        ],
    },
    {
        "path": ["特殊风险揭示"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"特殊风险揭示"],
            }
        ],
    },
    {
        "path": ["一般风险揭示"],
        "models": [
            {
                "name": "middle_paras",
                "top_anchor_regs": [r"一般风险揭示"],
                "bottom_anchor_regs": [r"基金合同的效力"],
                "possible_element_counts": 600,
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"一般风险揭示"],
            },
        ],
    },
    {
        "path": ["投资标的风险"],
        "models": [
            {
                "name": "middle_paras",
                "use_top_crude_neighbor": False,
                "top_anchor_regs": [r"投资标的风险"],
                "bottom_anchor_regs": [r"本基金特定风险|税收风险"],
                "include_top_anchor": False,
            },
        ],
    },
    {
        "path": ["本基金特定风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"本基金特定风险"],
            }
        ],
    },
    {
        "path": ["合同成立"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"基金合同的效力、变更、解除与终止"],
                "only_inject_features": True,
                "ignore_syllabus_children": True,
                "extract_from": "same_type_elements",
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"基金合同.*?之日起成立"],
                },
            },
        ],
    },
    {
        "path": ["基金合同有效期"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (r"(?P<content>基金合同有效期.*)",),
            }
        ],
    },
    {
        "path": ["合同生效"],
        "models": [
            # {
            #     "name": "middle_paras",
            #     "include_top_anchor": False,
            #     "top_anchor_regs": [r'合同生效'],
            #     "bottom_anchor_regs": [r'至基金合同终止日'],
            # },
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金合同解除的情形"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["私募基金财产清算小组组成"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"私募基金的清算"],
                "only_inject_features": True,
                "include_top_anchor": False,
                "top_anchor_regs": [r"清算小组组成"],
                "bottom_anchor_regs": [r"清算小组职责"],
            },
            {
                "name": "para_match",
                "paragraph_pattern": (r"基金财产清算小组组成[:：].*",),
            },
        ],
    },
    {
        "path": ["私募基金财产清算小组职责"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"私募基金的清算"],
                "only_inject_features": True,
                "include_top_anchor": False,
                "top_anchor_regs": [r"清算小组职责"],
                "bottom_anchor_regs": [r"清算的程序"],
            },
            {
                "name": "para_match",
                "paragraph_pattern": (r"基金财产清算小组负责.*",),
            },
        ],
    },
    {
        "path": ["私募基金财产清算的程序"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "top_default": True,
                "top_anchor_regs": [r"私募基金(财产)?清算的程序"],
                "bottom_anchor_regs": [r"清算费用的来源与支付方式"],
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__私募基金(财产)?清算的程序"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["清算费用的来源与支付方式"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "top_anchor_regs": [r"清算费用的来源与支付方式"],
                "include_top_anchor": False,
                "bottom_anchor_regs": [r"基金剩余财产的分配"],
                "include_bottom_anchor": False,
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"清算费用的来源与支付方式"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["基金剩余财产的分配"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"基金剩余财产的分配"],
                "only_inject_features": True,
                "ignore_syllabus_children": True,
                "extract_from": "same_type_elements",
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "top_anchor_regs": [r"基金剩余财产的分配"],
                    "include_top_anchor": False,
                    "bottom_anchor_regs": [r"基金清算报告的告知安排"],
                },
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"基金剩余财产的分配"],
            },
        ],
    },
    {
        "path": ["基金清算报告的告知安排"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"私募基金财产清算"],
                "only_inject_features": True,
                "ignore_syllabus_children": True,
                "extract_from": "same_type_elements",
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "top_anchor_regs": [r"基金清算报告的告知安排"],
                    "include_top_anchor": False,
                    "bottom_anchor_regs": [r"私募基金清算账册及文件"],
                },
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "top_default": True,
                "bottom_anchor_regs": [r"私募基金清算账册及文件"],
                "include_bottom_anchor": False,
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"基金清算报告的告知安排"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["清算账册及文件"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (r"(?P<content>清算账册及文件.*)",),
            }
        ],
    },
    {
        "path": ["基金相关账户的注销"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["免责条款"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"违约责任"],
                "only_inject_features": True,
                "ignore_syllabus_children": True,
                "extract_from": "same_type_elements",
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": False,
                    "include_bottom_anchor": False,
                    "top_anchor_regs": [r"免责条款"],
                    "bottom_anchor_regs": [r"[(（]五"],
                },
            },
        ],
    },
    {
        "path": ["其他事项"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"其他事项"],
                "only_inject_features": True,
                "extract_from": "same_type_elements",
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "top_default": True,
                    "include_bottom_anchor": False,
                    "bottom_anchor_regs": [r"以下无正文"],
                },
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["销售协议"],
        "models": [
            {
                "name": "middle_paras",
                "elements_not_in_page_range": list(range(50)),
                "use_top_crude_neighbor": False,
                "top_anchor_regs": [r"金融产品代销协议"],
                "bottom_default": True,
                "include_top_anchor": False,
                "include_bottom_anchor": True,
            }
        ],
    },
    {
        "path": ["管理人自行对基金投资开展的风险控制和管理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__管理人自行对基金投资开展的风险控制和管理$"],
                "only_inject_features": True,
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"私募基金的投资"],
                "only_inject_features": True,
                "extract_from": "same_type_elements",
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": r"管理人自行对基金投资开展的风险控制和管理(?P<content>.*)",
                },
            },
        ],
    },
    {
        "path": ["认购期利息处理方式"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>基金募集期间认购.*。$)",
                ],
            },
        ],
    },
    {
        "path": ["净值精度"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>基金资产净值的?计算.*。$)",
                ],
            },
        ],
    },
    {
        "path": ["认购费用计算方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__基金份额的?计算$"],
            },
        ],
    },
    {
        "path": ["申购费用计算方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__申购和赎回的?费用$"],
            },
        ],
    },
    {
        "path": ["业绩报酬计提模式"],
        "models": [
            {
                "name": "table_kv_expand",
                "use_complete_table": True,
                "top_anchor_regs": [r"(\d.)?业绩报酬的?计算(方法|公式)", r"(不(计)?提(取)?|不收取)业绩报酬"],
                "top_anchor_content_regs": [
                    r"(?P<content>单个(.类)?基金份额持有人单笔投资基金份额)业绩",
                    r"(?P<content>^本?((产品)?基金管理人|基金)?(不(计)?提(取)?|不收取|无)业绩报酬。?$)",
                ],
                "bottom_anchor_regs": [
                    r"账户名称",
                    r"户名",
                ],
            },
            {
                "name": "table_kv",
                "regs": [
                    r"(?P<dst>单个(.类)?基金份额持有人单笔投资基金份额)业绩",
                    r"(?P<dst>^本?((产品)?基金管理人|基金)?(不(计)?提(取)?|不收取|无)业绩报酬。?$)",
                    r"(?P<dst>^无$)",
                ],
                "only_matched_value": True,
            },
        ],
    },
    {
        "path": ["预警、止损机制的风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__预警、止损机制的?风险"],
            },
        ],
    },
    {
        "path": ["调仓期"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"基金管理人应当在(?P<dst>.*)个工作日内调整完毕",
                ],
            },
        ],
    },
    {
        "path": ["调仓描述"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__投资((比例|限制)(、)?){2}$"],
                "multi_elements": True,
                "skip_child_syllabuses": False,
                "paragraph_model": "para_match",
                "multi": True,
                "para_config": {
                    "enum_from_multi_element": True,
                    "paragraph_pattern": (r"基金管理人应当.*比例规定"),
                },
            },
        ],
    },
    {
        "path": ["个人首次投资金额下限"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
]


def get_predictor_options():
    for option in predictor_options:
        models = option["models"]
        if [x for x in models if x["name"] in ["partial_text", "para_match"]]:
            models.append(
                {
                    "name": "score_filter",
                    "threshold": 0.2,
                    "aim_types": ["PARAGRAPH"],
                    "multi_elements": False,
                }
            )
        option["models"] = models
    return predictor_options


prophet_config = {
    "depends": {},
    "predictor_options": get_predictor_options(),
}
