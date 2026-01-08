# 广发基金年中报
from remarkable.common.pattern import PatternCollection

predictor_options = [
    {
        "path": ["报告期时间"],
        "sub_primary_key": ["份额名称"],
        "fake_leaf": True,
        "models": [
            {
                "name": "report_time",
            },
            {
                "name": "score_filter",
            },
        ],
    },
    {
        "path": ["兼任情况"],
        "sub_primary_key": ["姓名", "产品类型"],
        "models": [
            {
                "name": "table_row",
                "unit_column_pattern": (r"[-——：]单位$",),
                "neglect_title_patterns": [
                    r"基金经理.*?简介",
                    r"管理人报告",
                ],
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"期末兼任私募资产管理计划投资经理的基金经理同时管理的产品情况",
                ],
                "extract_from": "same_type_elements",
                "only_inject_features": True,
                "table_model": "table_row",
                "table_config": {
                    "unit_column_pattern": (r"[-——：]单位$",),
                    "neglect_title_patterns": [
                        r"基金经理.*?简介",
                        r"管理人报告",
                    ],
                },
            },
        ],
    },
    {
        "path": ["基金业绩表现"],
        "sub_primary_key": ["份额名称"],
        "models": [
            {
                "name": "fund_performance",
                "multi": True,
                "merge_char_result": False,
                "份额名称": {
                    "regs": [r"(?P<dst>([A-Z]类基金))份额"],
                },
                "净值增长率": {
                    "regs": [r"([A-Z]类基金)?份额净值增长率为(?P<dst>([-\d\.%]+))"],
                },
                "净值收益率": {
                    "regs": [r"([A-Z]类基金)?份额净值收益率为(?P<dst>([-\d\.%]+))"],
                },
                "同期业绩比较基准收益率": {
                    "regs": [r"同期业绩比较基准收益率为(?P<dst>([-\d\.%]+))"],
                },
            },
        ],
    },
    {
        "path": ["报告名称"],
        "models": [
            {
                "name": "fixed_position",
                "multi_elements": True,
                "positions": [1, 2, 3, 4, 5],
                "regs": ["(?P<dst>^广发.*)", "(?P<dst>.*报告)"],
                "ignore_element_class": ["PAGE_HEADER"],
            }
        ],
    },
    {
        "path": ["报告日期"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(1, 5)),
                "regs": [r"(?P<dst>\d+年\d+月\d+日)"],
            },
        ],
    },
    {
        "path": ["基金管理人"],
        "models": [
            {
                "name": "fixed_position",
                "positions": [3, 4, 5],
                "regs": ["基金管理人.?(?P<dst>.*?公司$)"],
            },
        ],
    },
    {
        "path": ["基金托管人"],
        "models": [
            {
                "name": "fixed_position",
                "positions": [3, 4, 5, 6],
                "regs": ["基金托管人.?(?P<dst>.*?公司$)"],
            },
        ],
    },
    {
        "path": ["报告送出日期"],
        "models": [
            {
                "name": "fixed_position",
                "pages": [0],
                "regs": ["送出日期.?(?P<dst>.{1,12}日$)"],
            },
        ],
    },
    {
        "path": ["报告起始日"],
        "models": [
            {
                "name": "partial_text",
                "regs": ["本报告期(?P<dst>自.*止)"],
            },
        ],
    },
    {
        "path": ["重要提示1"],
        "models": [
            {"name": "syllabus_filter", "important_split": True, "is_first_part": True},
        ],
    },
    {
        "path": ["重要提示2"],
        "models": [
            {"name": "syllabus_filter", "important_split": True, "is_first_part": False},
        ],
    },
    {
        "path": ["基金基本情况表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["基础设施项目-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["目标基金基本情况-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"目标基金基本情况"],
            },
        ],
    },
    {
        "path": ["基金产品说明-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["目标基金产品说明-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["基金管理人和基金托管人表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["基础设施资产支持证券管理人和外部管理机构-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["基金投资顾问表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["境外投资顾问和境外资产托管人表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["信息披露方式表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["其他相关资料表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "break_pattern": [
                    r"主要财务指标和基金净值表现$",
                ],
            },
        ],
    },
    {
        "path": ["主要会计数据和财务指标-注释"],
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1387#note_274394
        "models": [
            {
                "name": "table_annotate",
                "break_pattern": [r"基金净值表现$", r"3.1.2.*?证券投资基金$"],
            },
        ],
    },
    {
        "path": ["其他财务指标-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["基金净值表现-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"基金份额净值收益率及其与同期业绩比较基准收益率的比较"],
                "break_pattern": [r"3.2.2"],
            },
        ],
    },
    {
        "path": ["自基金合同生效（基金转型）一来基金份额累计净值增长率变动及其与同期业绩比较基准收益率变动的比较"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["自基金合同生效以来基金累计净值增长率变动及其与同期业绩比较基准收益率变动的比较-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [
                    r"__regex__[自从]基金\w{,6}以?(来|后)\w{,4}累计?\w{,5}变(动|更)(及其?|和)?与\w{,10}收益率?变(动|更)",
                ],
            }
        ],
    },
    {
        "path": ["过去五年或自基金合同生效或自基金转型以来基金每年净值增长率及其与同期业绩比较基准收益率的比较"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [
                    r"__regex__过去五年基金每年净值(收益|增长)率及其与同期业绩比较基准收益率的比较",
                    r"__regex__自基金(转型|合同生效)以来基金每年净值增长率及其与同期业绩比较基准收益率的比较",
                ],
                "ignore_pattern": [
                    r"广发景宁纯债C",
                ],
            },
        ],
    },
    {
        "path": ["其他指标-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["过去三年基金的利润分配情况-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"过去三年基金的利润分配情况"],
                "break_pattern": [r"管理人对报告期内本基金运作遵规守信情况的说明$"],
            }
        ],
    },
    {
        "path": ["本报告期及近三年的可供分配金额-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["本报告期及近三年的实际分配金额-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["本期可供分配金额计算过程-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["本期调整项与往期不一致的情况说明"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["本期可供分配金额与招募说明书中刊载的可供分配金额测算报告的差异情况说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["报告期内基金及资产支持证券费用收取情况的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["对报告期内基础设施项目公司运营情况的整体说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基础设施项目所属行业整体情况的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基础设施项目所属行业竞争情况的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["营业收入分析-基础设施项目公司名称"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"基础设施项目公司名称.(?P<dst>.*)"],
                "syllabus_regs": [r"营业收入分析"],
                "multi_elements": True,
            }
        ],
    },
    {
        "path": ["基础设施项目公司的营业收入分析-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["管理人对基础设施项目公司营业收入重大变化情况的分析"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["营业成本及费用分析-基础设施项目公司名称"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"基础设施项目公司名称.?(?P<dst>.*)"],
                "syllabus_regs": [r"营业成本及(?:主要)?费用分析"],
                "multi_elements": True,
            }
        ],
    },
    {
        "path": ["基础设施项目公司的营业成本及主要费用分析-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["管理人对基础设施项目公司营业成本及主要费用重大变化情况的分析"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["指标分析-基础设施项目公司名称"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"基础设施项目公司名称.?(?P<dst>.*)"],
                "syllabus_regs": [r"指标分析"],
                "multi_elements": True,
            }
        ],
    },
    {
        "path": ["基础设施项目公司的财务业绩衡量指标分析-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["管理人对基础设施项目公司财务业绩衡量指标重大变化情况的分析"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["基础设施项目运营相关通用指标信息"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["经营活动现金流归集、管理、使用情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["对报告期内单一客户经营性现金流占比较高情况的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["对报告期内发生的影响未来项目正常现金流的重大情况与拟采取的相应措施的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["报告期内对外借入款项基本情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["本期对外借入款项情况与上年同期的变化情况分析"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["对基础设施项目报告期内对外借入款项不符合借款要求情况的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["报告期内购入或出售基础设施项目情况-注释"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["购入或出售基础设施项目变化情况及对基金运作、收益等方面的影响分析"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["抵押、查封、扣押、冻结等他项权利限制的情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基础设施项目相关保险的情况"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["基础设施项目未来发展展望的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["其他需要说明的情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "ignore_pattern": [r"除基础设施资产支持证券之外的投资组合报告"],
            },
        ],
    },
    {
        "path": ["基金管理人及其管理基金的经验"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金管理人及其管理基础设施基金的经验"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金经理及基金经理助理简介-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"__regex__基金经理（或基金经理小组）及基金经理助理的简介"],
            },
        ],
    },
    {
        "path": ["期末兼任私募资产管理计划投资经理的基金经理同时管理的产品情况-注释"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金经理薪酬机制"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["境外投资顾问为本基金提供投资建议的主要成员简介-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["管理人对报告期内本基金运作遵规守信情况的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["管理人对报告期内公平交易制度及执行情况的专项说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["公平交易制度和控制方法"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["公平交易制度的执行情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_before_first_chapter": True,
            },
        ],
    },
    {
        "path": ["增加执行的基金经理公平交易制度执行情况及公平交易管理情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__增加执行的基金经理公平交易制度执行情况及公平交易管理情况"],
            },
        ],
    },
    {
        "path": ["异常交易行为的专项说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["报告期内基金的投资策略和运作分析"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r"报告期内基金的业绩表现$"],
            },
        ],
    },
    {
        "path": ["管理人对报告期内基金收益分配情况的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["管理人对宏观经济及行业走势的简要展望"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"管理人对宏观经济及行业走势的简要展望"],
            },
        ],
    },
    {
        "path": ["管理人对关联交易及相关利益冲突的防范措施"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["报告期内基金的业绩表现"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["管理人对宏观经济、证券市场及行业走势的简要展望"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["管理人内部有关本基金的监察稽核工作情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["管理人对报告期内基金估值程序等事项的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["报告期内基金资产重大减值计提情况的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["管理人对报告期内基金利润分配情况的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["管理人对会计师事务所出具非标准审计报告所涉相关事项的说明"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["报告期内基金持有人数或基金资产净值预警说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"报告期内管理人对本基金持有人数或基金资产净值预警情形的说明"],
                "only_before_first_chapter": True,
            },
        ],
    },
    {
        "path": ["报告期内本基金托管人遵规守信情况声明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["托管人对报告期内本基金投资运作遵规守信、净值计算、利润分配等情况的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["托管人对本年度报告或中期报告中财务信息等内容的真实、准确和完整发表意见"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r"审计报告$"],
                "inject_syllabus_features": [r"托管人对本中期报告中财务信息等内容的真实、准确和完整发表意见"],
            },
        ],
    },
    {
        "path": ["报告期内本基金资产支持证券管理人遵规守信及履职情况的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["报告期内本基金外部管理机构遵规守信及履职情况的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["报告期内本基金外部管理机构与本基金相关的主要人员变动情况的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["审计报告基本信息-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["审计报告的基本内容-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["审计意见"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["形成审计意见的基础"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["其他信息"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["管理层和治理层对财务报表的责任"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["注册会计师对财务报表审计的责任"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["对基金管理人和评估机构采用评估方法和参数的合理性的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资产负债表-会计主体"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"会计主体.?(?P<dst>.*)"],
            },
        ],
    },
    {
        "path": ["资产负债表-报告截止日"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"报告截止日.?(?P<dst>.*)"],
            },
        ],
    },
    {
        "path": ["资产负债表-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["个别资产负债表-会计主体"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"会计主体.?(?P<dst>.*)"],
                "syllabus_regs": [r"个别资产负债表"],
            },
        ],
    },
    {
        "path": ["个别资产负债表-报告截止日"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"报告截止日.?(?P<dst>.*)"],
                "syllabus_regs": [r"个别资产负债表"],
            },
        ],
    },
    {
        "path": ["个别资产负债表-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["利润表-会计主体"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"会计主体.?(?P<dst>.*)"],
            },
        ],
    },
    {
        "path": ["利润表-报告截止日"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"本报告期.?(?P<dst>.*)"],
            },
        ],
    },
    {
        "path": ["利润表-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["个别利润表-会计主体"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"会计主体.(?P<dst>.*)"],
                "syllabus_regs": [r"个别利润表"],
            },
        ],
    },
    {
        "path": ["个别利润表-报告截止日"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"本报告期.(?P<dst>.*)"],
                "syllabus_regs": [r"个别利润表"],
            },
        ],
    },
    {
        "path": ["个别利润表-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["现金流量表-会计主体"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"会计主体.(?P<dst>.*)"],
                "syllabus_regs": [r"现金流量表"],
            },
        ],
    },
    {
        "path": ["现金流量表-报告截止日"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"本报告期.(?P<dst>.*)"],
                "syllabus_regs": [r"现金流量表"],
            },
        ],
    },
    {
        "path": ["现金流量表-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["个别现金流量表-会计主体"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"会计主体.(?P<dst>.*)"],
                "syllabus_regs": [r"个别现金流量表"],
            },
        ],
    },
    {
        "path": ["个别现金流量表-报告截止日"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"本报告期.(?P<dst>.*)"],
                "syllabus_regs": [r"个别现金流量表"],
            },
        ],
    },
    {
        "path": ["个别现金流量表-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["净资产或所有者权益（基金净值）变动表-会计主体"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"会计主体.?(?P<dst>.*)"],
            },
        ],
    },
    {
        "path": ["净资产或所有者权益（基金净值）变动表-报告截止日"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"本报告期.?(?P<dst>.*)"],
            },
        ],
    },
    {
        "path": ["净资产或所有者权益（基金净值）变动表-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"__regex__净资产(（基金净值）)?变动表"],
                "break_pattern": [r"报表附注为财务报表的组成部分"],
                "annotate_pattern": [
                    r"^注",
                ],
            },
        ],
    },
    {
        "path": ["个别净资产或所有者权益（基金净值）变动表-会计主体"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"会计主体.(?P<dst>.*)"],
                "syllabus_regs": [r"个别所有者权益变动表"],
            },
        ],
    },
    {
        "path": ["个别净资产或所有者权益（基金净值）变动表-报告截止日"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"本报告期.(?P<dst>.*)"],
                "syllabus_regs": [r"个别所有者权益变动表"],
            },
        ],
    },
    {
        "path": ["个别净资产或所有者权益（基金净值）变动表-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["本报告章节"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"本报告(?P<dst>.*?)[,，]", r"本报告(?P<dst>[\d+\-\.–]+)"],
            },
        ],
    },
    {
        "path": ["基金管理人负责人"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"基金管理人负责人.?(?P<dst>.*?)([,，]|主管)"],
            },
            {
                "name": "previous_column_cell",
                "regs": [r"基金管理人负责人"],
            },
        ],
    },
    {
        "path": ["主管会计工作负责人"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"主管会计工作负责人.?(?P<dst>.*?)([，,]|会计)"],
            },
            {
                "name": "previous_column_cell",
                "regs": [r"主管会计工作负责人"],
            },
        ],
    },
    {
        "path": ["会计机构负责人"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"会计机构负责人.?(?P<dst>.*)"],
            },
            {
                "name": "previous_column_cell",
                "regs": [r"会计机构负责人"],
            },
        ],
    },
    {
        "path": ["基金基本情况"],
        "models": [
            {"name": "syllabus_elt_v2", "inject_syllabus_features": [r"__regex__报表附注__regex__基金基本情况"]},
        ],
    },
    {
        "path": ["会计报表的编制基础"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["遵循企业会计准则及其他有关规定的声明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["会计年度"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["记账本位币"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["企业合并"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["合并财务报表的编制方法"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["现金及现金等价物"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["外币业务和外币报表折算"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["金融工具"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["应收票据"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["应收账款"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["存货"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["长期股权投资"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["投资性房地产"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["固定资产"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["在建工程"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["借款费用"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["无形资产"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["长期待摊费用"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["长期资产减值"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["职工薪酬"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["应付债券"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["预计负债"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["优先股、永续债等其他金融工具"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["递延所得税资产与递延所得税负债"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["持有待售"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["公允价值计量"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["实收基金"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__重要会计政策和会计估计__regex__实收基金"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["收入"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["费用"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["租赁"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["政府补助"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["金融资产和金融负债的分类"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["金融资产和金融负债的初始确认、后续计量和终止确认"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["金融资产和金融负债的估值原则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": ["金融资产和金融负债的抵销$"],
            },
        ],
    },
    {
        "path": ["金融资产和金融负债的抵销"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["损益平准金"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["收入或（损失）的确认和计量"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"收入/\(损失\)的确认和计量"],
            },
        ],
    },
    {
        "path": ["费用的确认和计量"],
        "models": [
            {
                "name": "syllabus_elt",
            },
        ],
    },
    {
        "path": ["基金的收益分配政策"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["外币交易"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["分部报告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["其他重要的会计政策和会计估计"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["会计政策变更的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["会计估计变更的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["差错更正的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["税项"],
        "models": [
            {"name": "syllabus_elt_v2", "inject_syllabus_features": [r"税项"], "skip_table": True},
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                #  https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2229
                "inject_syllabus_features": [
                    r"印花税",
                    r"增值税、城建税、教育费附加及地方教育费附加",
                    r"企业所得税",
                    r"个人所得税",
                    r"境外投资",
                ],
                "skip_table": True,
                "multi": True,
                "include_title": True,
            },
        ],
    },
    {
        "path": ["货币资金情况表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"货币资金"],
            },
        ],
    },
    {
        "path": ["银行存款表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"__regex__重要财务报表项目的说明__regex__银行存款"],
            },
        ],
    },
    {
        "path": ["因抵押、质押或冻结等对使用有限制、有潜在回收风险的款项说明"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["交易性金融资产-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
            {
                "name": "para_match",
                "paragraph_pattern": [r"^本基金本报告期内无交易性金融资产"],
            },
        ],
    },
    {
        "path": ["交易性金融资产1表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["交易性金融资产2表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["衍生金融资产（负债）期末余额表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"__regex__衍生金融资产[/]负债期末余额"],
            },
        ],
    },
    {
        "path": ["期末基金持有的期货合约情况表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["期末基金持有的黄金衍生品情况表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["各项买入返售金融资产表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2438
                "inject_syllabus_features": [r"各项买入返售金融资产期末余额"],
            },
        ],
    },
    {
        "path": ["期末买断式逆回购交易中取得的债券表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"期末买断式逆回购交易中取得的债券"],
            },
        ],
    },
    {
        "path": ["按预期信用损失一般模型计提减值准备的说明"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["债权投资情况表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"__regex__债权投资$"],
            },
        ],
    },
    {
        "path": ["债权投资减值准备计提情况表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["其他债权投资情况表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["其他债权投资减值准备计提情况表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["其他权益工具投资情况表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["报告期末其他权益工具投资情况表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["按账龄披露应收账款-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["按坏账准备计提方法分类披露-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["单项计提坏账准备的应收账款-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["按组合计提坏账准备的应收账款-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["本期坏账准备的变动情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["本期实际核销的应收账款情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["按债务人归集的报告期末余额前五名的应收账款-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["存货分类-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["存货跌价准备及合同履约成本减值准备-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["报告期末存货余额含借款费用资本化金额的说明"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["报告期内合同履约成本摊销金额的说明"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["合同资产情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["报告期内合同资产账面价值发生重大变动的金额和原因-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["报告期内合同资产计提减值准备情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["按预期信用损失一般模型计提减值准备的注释或说明"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["持有待售资产-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["采用成本计量模式的投资性房地产-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["采用公允价值计量模式的投资性房地产-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["投资性房地产主要项目情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["固定资产-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["固定资产情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["固定资产的其他说明"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["固定资产清理-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["在建工程-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["在建工程情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["报告期内重要在建工程项目变动情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["报告期内在建工程计提减值准备情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["工程物资情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["使用权资产-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["无形资产情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["无形资产的其他说明"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["开发支出-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["商誉账面原值-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["商誉减值准备-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["商誉减值测试过程、关键参数及商誉减值损失的确认方法"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["长期待摊费用-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["未经抵销的递延所得税资产-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["未经抵销的递延所得税负债-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["以抵销后净额列示的递延所得税资产或负债-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["未确认递延所得税资产的可抵扣暂时性差异明细-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["未确认递延所得税资产的可抵扣亏损将于以下年度到期-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["其他资产表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["按账龄列示表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["按预付对象归集的报告期末余额前五名的预付款情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["其他应收款-按账龄列示-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["其他应收款-按款项性质分类-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["其他应收款坏账准备计提情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["本期发生坏账准备显著变动的其他应收款情况说明"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["本期计算坏账准备计提金额与评估金融工具信用风险是否显著增加的依据"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["报告期内实际核销的其他应收款情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["按债务人归集的报告期末余额前五名的其他应收款-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["短期借款-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["应付账款情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["账龄超过一年的重要应付账款-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["应付职工薪酬情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["短期薪酬-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["设定提存计划-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["应交税费-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["应付利息-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["合同负债情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["报告期内合同负债账面价值发生重大变动的金额和原因-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["长期借款-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["预计负债-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["租赁负债-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["其他负债表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["预收款项情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["账龄超过一年的重要预收款项-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["按款项性质列示的其他应付款-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["账龄超过一年的重要其他应付款-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["实收基金表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"__regex__重要财务报表项目的说明__regex__实收基金"],
                "one_result_per_feature": False,
                "break_pattern": [r"未分配利润$"],
                "ignore_pattern": [
                    r"^实收基金为对外发行基金份额所对应的金额",
                ],
            },
        ],
    },
    {
        "path": ["资本公积-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["其他综合收益表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["盈余公积-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["未分配利润表格-注释"],
        "models": [
            {"name": "table_annotate", "annotate_pattern": [r"未分配利润.*元"]},
        ],
    },
    {
        "path": ["营业收入和营业成本-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["投资收益-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["资产处置收益-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["其他收益-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["其他业务收入-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["利息支出-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["税金及附加-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["销售费用-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["管理费用-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["财务费用-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["资产减值损失-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["营业外收入情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["计入当期损益的政府补助-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["营业外支出-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["所得税费用情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["会计利润与所得税费用调整过程-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["收到其他与经营活动有关的现金-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["支付其他与经营活动有关的现金-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["收到其他与投资活动有关的现金-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["支付其他与投资活动有关的现金-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["收到其他与筹资活动有关的现金-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["支付其他与筹资活动有关的现金-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["现金流量表补充资料-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["报告期内支付的取得子公司的现金净额-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["现金和现金等价物的构成-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["所有者权益变动表项目-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["报告期内发生的非同一控制下企业合并-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["合并成本及商誉情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["合并成本公允价值的确定方法、或有对价及其变动的说明"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["大额商誉形成的主要原因"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["被购买方于购买日可辨认资产、负债的情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["可辨认资产、负债公允价值的确定方法"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["企业合并中承担的被购买方的或有负债"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["报告期内发生的同一控制下企业合并-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["合并成本-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["或有对价及其变动的说明"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["合并日被合并方资产、负债的账面价值-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["企业合并中承担的被合并方的或有负债的说明"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["反向购买"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["其他"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["集团的构成-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["存款利息收入表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"存款利息收入"],
            },
        ],
    },
    {
        "path": ["股票投资收益项目构成表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"股票投资收益"],
            },
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"股票投资收益项目构成"],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [r"^本基金本报告期内无股票投资收益"],
            },
        ],
    },
    {
        "path": ["股票投资收益——买卖股票差价收入表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
            {
                "name": "para_match",
                "paragraph_pattern": [r"^本基金本报告期内无买卖股票差价收入。"],
            },
        ],
    },
    {
        "path": ["股票投资收益——赎回差价收入表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["股票投资收益——申购差价收入表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["股票投资收益——证券出借差价收入表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["基金投资收益表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["债券投资收益项目构成表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2439
                "inject_syllabus_features": [r"债券投资收益项目构成"],
            }
        ],
    },
    {
        "path": ["债券投资收益——买卖债券差价收入表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"债券投资收益——买卖债券差价收入"],
            },
        ],
    },
    {
        "path": ["债券投资收益——赎回差价收入表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["债券投资收益——申购差价收入表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["资产支持证券投资收益项目构成表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["资产支持证券投资收益——买卖资产支持证券差价收入表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["资产支持证券投资收益——赎回差价收入表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["资产支持证券投资收益——申购差价收入表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["贵金属投资收益项目构成表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"贵金属投资收益"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["贵金属投资收益——买卖贵金属差价收入表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["贵金属投资收益——赎回差价收入表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["贵金属投资收益——申购差价收入表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["衍生工具收益——买卖权证差价收入表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["衍生工具收益——其他投资收益表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["股利收益表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"股利收益"],
            }
        ],
    },
    {
        "path": ["公允价值变动收益表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
            {
                "name": "para_match",
                "paragraph_pattern": [r"^本基金本报告期内无公允价值变动收益"],
            },
        ],
    },
    {
        "path": ["其他收入表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"其他收入"],
            },
        ],
    },
    {
        "path": ["持有基金产生的费用表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["信用减值损失表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["其他费用表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["分部报告-附注"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["承诺事项-附注"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["或有事项-附注"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资产负债表日后事项-附注"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["关联方关系-注释"],
        "models": [
            {
                "name": "table_annotate",
                "break_pattern": [r"基金托管费$"],
            }
        ],
    },
    {
        "path": ["本报告期存在控制关系或其他重大利害关系的关联方发生变化的情况-附注"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["本报告期与基金发生关联交易的各关联方表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["本报告期及上年度可比期间的关联方交易"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["采购商品、接受劳务情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["出售商品、提供劳务情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["作为出租方-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["作为承租方-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["债券交易-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["股票交易表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"股票交易"],
            }
        ],
    },
    {
        "path": ["权证交易表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["应支付关联方的佣金表格-注释"],
        "models": [
            {
                "name": "middle_paras",
                "top_anchor_regs": [r"注[：:].{,3}(上述佣金|本基金)"],
                "bottom_anchor_regs": [r"关联方报酬$"],
            },
            {
                "name": "table_annotate",
                "break_pattern": [r"关联方报酬$"],
            },
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r"关联方报酬$"],
            },
        ],
    },
    {
        "path": ["基金管理费表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["基金投资顾问费表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["基金托管费表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["销售服务费表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["与关联方进行银行间同业市场的债券（含回购）交易表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"与关联方进行银行间同业市场的债券\(含回购\)交易"],
            },
        ],
    },
    {
        "path": ["与关联方通过约定申报方式进行的适用固定期限费率的证券出借业务的情况表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["与关联方通过约定申报方式进行的适用市场化期限费率的证券出借业务的情况表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["报告期内基金管理人运用固有资金投资本基金的情况表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["报告期末除基金管理人之外的其他关联方投资本基金的情况表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
            {
                "name": "syllabus_elt_v2",
                "skip_table": True,
                "ignore_pattern": [r"份额单位"],
            },
        ],
    },
    {
        "path": ["由关联方保管的银行存款余额及当期产生的利息收入表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["本基金在承销期内参与关联方承销证券的情况表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["其他关联交易事项的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__其他关联交易事项的说明__regex__其他关联交易事项的说明"],
                "break_para_pattern": [r"当期交易及持有基金管理人以及管理人关联方所管理基金产生的费用"],
            },
            {
                "name": "para_match",
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2442
                "paragraph_pattern": [r"^本基金本报告期末持有基金管理人广发基金管理有限公司"],
            },
        ],
    },
    {
        "path": ["关联方应收项目-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["关联方应付项目-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["当期交易及持有基金管理人以及管理人关联方所管理基金产生的费用表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["收益分配基本情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["因认购新发或增发证券而于期末持有的流通受限证券表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["期末持有的暂时停牌等流通受限股票表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"期末持有的暂时停牌等流通受限股票"],
            }
        ],
    },
    {
        "path": ["银行间市场债券正回购-文字说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"银行间市场债券正回购"],
                "only_first": True,
            },
        ],
    },
    {
        "path": ["银行间市场债券正回购表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["交易所市场债券正回购"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["期末参与转融通证券出借业务的证券表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["金融工具风险及管理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r"风险管理政策和组织架构$"],
            }
        ],
    },
    {
        "path": ["风险管理政策和组织架构"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["信用风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r"按短期信用评级列示的债券投资$"],
            }
        ],
    },
    {
        "path": ["按短期信用评级列示的债券投资表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["按短期信用评级列示的资产支持证券投资表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["按短期信用评级列示的同业存单投资表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["按长期信用评级列示的债券投资表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "break_pattern": [r"流动性风险$", r"按长期信用评级列示的同业存单投资$"],
            }
        ],
    },
    {
        "path": ["按长期信用评级列示的资产支持证券投资表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["按长期信用评级列示的同业存单投资表格-注释"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r"流动性风险$"],
            }
        ],
    },
    {
        "path": ["流动性风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_before_first_chapter": True,
            },
        ],
    },
    {
        "path": ["金融资产和金融负债的到期期限分析表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["报告期内本基金组合资产的流动性风险分析"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r"市场风险$"],
            }
        ],
    },
    {
        "path": ["市场风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r"利率风险$"],
            }
        ],
    },
    {
        "path": ["利率风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r"利率风险敞口$"],
            }
        ],
    },
    {
        "path": ["利率风险敞口-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["利率风险的敏感性分析表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["外汇风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r"外汇风险敞口$", r"外汇风险的敏感性分析$"],
            }
        ],
    },
    {
        "path": ["外汇风险敞口表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["外汇风险的敏感性分析表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["其他价格风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r"其他价格风险敞口$", r"其他价格风险的敏感性分析$"],
            }
        ],
    },
    {
        "path": ["其他价格风险敞口表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"其他价格风险敞口"],
            }
        ],
    },
    {
        "path": ["其他价格风险的敏感性分析-假设"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["其他价格风险的敏感性分析表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["采用风险价值法管理风险表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["金融工具公允价值计量的方法"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"金融工具公允价值计量的方法"],
            },
        ],
    },
    {
        "path": ["各层次金融工具的公允价值表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["公允价值所属层次间的重大变动"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["第三层次公允价值余额及变动情况表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [
                    r"__regex__第三层次公允价值余额及变动情况__regex__第三层次公允价值余额及变动情况",
                ],
            },
        ],
    },
    {
        "path": ["使用重要不可观察输入值的第三层次公允价值计量的情况表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["非持续的以公允价值计量的金融工具的说明"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r".*非持续的以公允价值计量的金融工具.*"],
            },
        ],
    },
    {
        "path": ["不以公允价值计量的金融工具的相关说明"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"本基金持有的不以公允价值计量.*"],
            },
        ],
    },
    {
        "path": ["有助于理解和分析会计报表需要说明的其他事项"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"有助于理解和分析会计报表需要说明的其他事项"],
            }
        ],
    },
    {
        "path": ["个别财务报表-货币资金情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["个别财务报表-银行存款-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["个别财务报表-长期股权投资情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["对子公司投资-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["期末基金资产组合情况-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"期末基金资产组合情况"],
            }
        ],
    },
    {
        "path": ["报告期末按行业分类的境内股票投资组合-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"报告期末按行业分类的境内股票投资组合"],
            }
        ],
    },
    {
        "path": ["按行业分类的港股通投资股票投资组合-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票投资明细-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"期末按公允价值占基金资产净值比例大小排序的所有股票投资明细"],
            },
        ],
    },
    {
        "path": ["期末积极投资按公允价值占基金资产净值比例大小排序的前五名股票投资明细-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["累计买入金额超出期初基金资产净值2%或前20名的股票明细表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "note_pattern": [r"本基金本报告期内未买入股票", r"本项.*不考虑相关交易费用"],
                "inject_syllabus_features": [
                    r"__regex__累计买入金额超出期(初|末)基金资产净值2[%％]或前20名的股票明细",
                ],
            }
        ],
    },
    {
        "path": ["累计卖出金额超出期初基金资产净值2%或前20名的股票明细表格-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [
                    r"__regex__累计卖出金额超出期(初|末)基金资产净值2[%％]或前20名的股票明细",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [r"^本基金本报告期内未(持有|卖出)股票。"],
            },
        ],
    },
    {
        "path": ["买入股票的成本总额及卖出股票的收入总额表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
            {
                "name": "para_match",
                "paragraph_pattern": [r"^本基金本报告期内未持有股票。"],
            },
        ],
    },
    {
        "path": ["期末按债券品种分类的债券投资组合-注释"],
        "models": [
            {
                "name": "table_annotate",
                "syllabus_black_list": [r"期末按债券信用等级分类的债券投资组合"],
                "inject_syllabus_features": [r"期末按债券品种分类的债券投资组合"],
            }
        ],
    },
    {
        "path": ["期末按公允价值占基金资产净值比例大小排序的前五名债券投资明细-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"期末按公允价值占基金资产净值比例大小排序的前五名债券投资明细"],
            }
        ],
    },
    {
        "path": ["期末按公允价值占基金资产净值比例大小排序的前十名资产支持证券投资明细-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [
                    r"期末按公允价值占基金资产净值比例大小排名的所有资产支持证券投资明细",
                    r"期末按公允价值占基金资产净值比例大小排名的前十名资产支持证券投资明细",
                ],
            }
        ],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名贵金属投资明细-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["期末按公允价值占基金资产净值比例大小排序的前五名权证投资明细-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["本基金投资股指期货的投资政策"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__本基金投资股指期货的投资政策"],
            },
        ],
    },
    {
        "path": ["本期国债期货投资政策"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"本期国债期货投资政策"],
            },
        ],
    },
    {
        "path": ["本期国债期货投资评价"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"本期国债期货投资评价"],
            },
        ],
    },
    {
        "path": ["基金持有股票资产"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["股票资产占基金资产净值的比例"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["空头合约市值"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["空头合约市值市值占基金资产净值的比例"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["空头合约市值占股票资产的比例"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["本基金执行市场中性策略的投资收益"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["公允价值变动损益"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["投资政策及风险说明"],
        "models": [
            {"name": "syllabus_elt_v2", "inject_syllabus_features": [r"投资政策及风险说明"]},
        ],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名基金投资明-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["基金计价方法说明"],
        "models": [
            {"name": "syllabus_elt_v2", "inject_syllabus_features": ["基金计价方法说明"], "only_first": True},
        ],
    },
    {
        "path": ["投资组合报告附注-是否处罚"],
        "models": [
            {
                "name": "syllabus_filter",
                "first_num_para": True,
                "inject_syllabus_features": [r"投资组合报告附注"],
            },
        ],
    },
    {
        "path": ["投资组合报告附注-备选股票库"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "include_title": True,
                "remove_para_begin_number": True,
                "inject_syllabus_features": [r"__regex__本报告期.*?投资.*?前十名股票.*?备选股票库"],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [r"(?P<content>(本基金)?本报告期.*?投资.*?前十名股票.*?备选股票库.*)"],
            },
        ],
    },
    {
        "path": ["其他各项资产构成-注释"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "skip_table": True,
                "ignore_pattern": [
                    r"份额单位",
                    r"金额单位",
                    r"^单位",
                    r"^[\d.]+",
                ],
                "inject_syllabus_features": [r"期末其他各项资产构成"],
            },
        ],
    },
    {
        "path": ["期末持有的处于转股期的可转换债券明细-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"期末持有的处于转股期的可转换债券明细"],
            }
        ],
    },
    {
        "path": ["期末前十名股票中存在流通受限情况的说明-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
            {
                "name": "syllabus_elt_v2",
                "skip_table": True,
                "ignore_pattern": [
                    r"份额单位",
                    r"金额单位",
                    r"^单位",
                ],
                "inject_syllabus_features": [r"期末前十名股票中存在流通受限情况的说明"],
            },
        ],
    },
    {
        "path": ["期末积极投资前五名股票中存在流通受限情况的说明-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
            {
                "name": "para_match",
                "paragraph_pattern": [r"^本基金本报告期末积极投资前五名股票中不存在流通受限情况。"],
            },
        ],
    },
    {
        "path": ["投资组合报告附注的其他文字描述部分"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["期末在各个国家（地区）证券市场的权益投资分布-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["期末按行业分类的权益投资组合-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["期末按公允价值占基金资产净值比例大小排序的所有权益投资明细-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["期末按公允价值占基金资产净值比例大小排序的前十名权益投资明细-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["积极投资期末按公允价值占基金资产净值比例大小排序的前五名权益投资明细-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["累计买入金额超出期初基金资产净值2%或前20名的权益投资明细表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
            {
                "name": "syllabus_elt_v2",
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"累计买入金额超出期末基金资产净值2%或前20名的权益投资明细"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["累计卖出金额超出期初基金资产净值2%或前20名的权益投资明细表格-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"累计卖出金额超出期末基金资产净值2%或前20名的权益投资明细"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["权益投资的买入成本总额及卖出收入总额-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"权益投资的买入成本总额及卖出收入总额"],
            }
        ],
    },
    {
        "path": ["期末按债券信用等级分类的债券投资组合-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"期末按债券信用等级分类的债券投资组合"],
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["期末按公允价值占基金资产净值比例大小排名的前五名金融衍生品投资明细-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["期末按公允价值占基金资产净值比例大小排序的前十名基金投资明细-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"期末按公允价值占基金资产净值比例大小排序的前十名基金投资明细"],
            }
        ],
    },
    {
        "path": ["债券回购融资情况-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"债券回购融资情况"],
                "break_pattern": [r"债券正回购的资金余额超过基金资产净值的20%的说明"],
            }
        ],
    },
    {
        "path": ["债券正回购的资金余额超过基金资产净值的20%的说明-注释"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"债券回购融资情况"],
                "skip_table": True,
                "ignore_pattern": [r"注[：:]", r"金额单位", r"债券正回购的资金余额超过基金资产净值的20%的说明"],
            },
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["投资组合平均剩余期限基本情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["报告期内投资组合平均剩余期限超过120天情况说明-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"报告期内投资组合平均剩余期限超过120天情况说明"],
            },
            {
                "name": "syllabus_filter",
                "last_paragraph": True,
                "inject_syllabus_features": [r"投资组合平均剩余期限基本情况"],
            },
        ],
    },
    {
        "path": ["期末投资组合平均剩余期限分布比例-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["报告期内投资组合平均剩余存续期超过240天情况说明-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"报告期内投资组合平均剩余存续期超过240天情况说明"],
            }
        ],
    },
    {
        "path": ["期末按实际利率计算账面价值占基金资产净值比例大小排名的前十名债券投资明细-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["“影子定价”与按实际利率计算账面价值确定的基金资产净值的偏离-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["报告期内负偏离度的绝对值达到0.25%情况说明-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"报告期内负偏离度的绝对值达到0.25%情况说明"],
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"__regex__投资组合报告"],
                "only_inject_features": True,
                "top_anchor_regs": [r"报告期内负偏离度的绝对值达到0.25%情况说明"],
                "include_top_anchor": False,
                "bottom_anchor_regs": [r"报告期内正偏离度的绝对值达到0.5%情况说明"],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [r"^本基金本报告期内未发生负偏离度的绝对值达到0.25%的情况"],
            },
        ],
    },
    {
        "path": ["报告期内正偏离度的绝对值达到0.5%情况说明-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"报告期内正偏离度的绝对值达到0.5%情况说明"],
            }
        ],
    },
    {
        "path": ["管理人聘任评估机构及评估报告内容的合规性说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["评估报告摘要"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["评估机构使用评估方法的特殊情况说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["期末基金份额持有人户数及持有人结构-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["期末上市基金前十名持有人-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["期末货币市场基金前十名份额持有人情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["基金前十名流通份额持有人-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["基金前十名非流通份额持有人-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["期末基金管理人的从业人员持有本开放式基金份额总量区间情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["期末兼任私募资产管理计划投资经理的基金经理本人及其直系亲属持有本人管理的产品情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["发起式基金发起资金持有份额情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["（开放式）基金份额变动-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["基金份额持有人大会决议"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金管理人、基金托管人的专门基金托管部门的重大人事变动"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["涉及基金管理人、基金财产、基金托管业务的诉讼"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["报告期内原始权益人或其同一控制下的关联方卖出战略配售取得的基金份额"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金投资策略的改变"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["本报告期持有的基金发生的重大影响事件"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"本报告期持有的基金发生的重大影响事件"],
            },
        ],
    },
    {
        "path": ["为基金进行审计的会计师事务所情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["为基金出具评估报告的评估机构情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["管理人、托管人及其高级管理人员受稽查或处罚等情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金租用证券公司交易单元进行股票投资及佣金支付情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["基金租用证券公司交易单元进行其他证券投资的情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["偏离度绝对值超过0.5%的情况-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"偏离度绝对值超过0.5%的情况"],
            }
        ],
    },
    {
        "path": ["其他重大事件-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["报告期内单一投资者持有基金份额比例达到或超过20%的情况-注释"],
        "models": [
            {
                "name": "table_annotate",
            },
        ],
    },
    {
        "path": ["影响投资者决策的其他重要信息"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__影响投资者决策的其他重要信息__regex__影响投资者决策的其他重要信息"
                ],
                "break_para_pattern": [r"报告期内单一投资者持有基金份额比例达到或超过20%的情况$"],
            }
        ],
    },
    {
        "path": ["备查文件目录"],
        "models": [
            {
                "name": "middle_paras",
                "top_anchor_regs": [r"备查文件目录"],
                "include_top_anchor": False,
                "ignore_pattern": [r"备查文件目录$"],
                "bottom_anchor_regs": [r"存放地点"],
                "possible_element_counts": 20,
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__备查文件目录__regex__备查文件目录"],
                "ignore_pattern": [r"有限公司$", r".{1,4}年.{1,2}月.{1,3}日$"],
                "syllabus_black_list": ["中国证监会批准广发对冲套利定期开放混合型发起式证券投资基金募集的文件"],
            },
        ],
    },
    {
        "path": ["存放地点"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"存放地点"],
            },
        ],
    },
    {
        "path": ["查阅方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"查阅方式"],
                "ignore_pattern": [r"有限公司$", r".{1,4}年.{1,2}月.{1,3}日$"],
            },
            {
                "name": "middle_paras",
                "top_anchor_regs": [r"查阅方式"],
                "bottom_anchor_regs": [r"网站查阅"],
                "include_top_anchor": False,
                "include_bottom_anchor": True,
                "top_greed": False,
            },
        ],
    },
    {
        "path": ["衍生工具收益-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"衍生工具收益"],
            }
        ],
    },
    {
        "path": ["利润分配情况-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"利润分配情况"],
            }
        ],
    },
    {
        "path": ["报告期末本基金投资的股指期货交易情况说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_before_first_chapter": True,
                "skip_table": True,
                "include_sub_title": False,
            },
        ],
    },
    {
        "path": ["应付交易费用-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"应付交易费用"],
            }
        ],
    },
    {
        "path": ["报告期末本基金投资的国债期货交易情况说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r"本期国债期货投资政策$"],
            }
        ],
    },
    {
        "path": ["基金名称"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["基金代码"],
        "models": [
            {"name": "table_kv", "neglect_title_patterns": [r"目标基金基本情况"]},
        ],
    },
    {
        "path": ["本报告期所采用的会计政策、会计估计与最近一期年度报告相一致的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [r"本报告期所采用的会计政策、会计估计与最近一期年度报告相一致的说明"],
            },
        ],
    },
]


def get_predictor_options():
    p_syllabus_name = PatternCollection(["表格-注释$", "-注释$"])
    for option in predictor_options:
        models = option["models"]
        for model in models:
            if model["name"] == "table_annotate":
                if model.get("only_inject_features"):
                    continue
                inject_syllabus_features = model.get("inject_syllabus_features", [])
                path = option["path"][0]
                syllabus_name = p_syllabus_name.sub("", path)
                if syllabus_name not in inject_syllabus_features:
                    inject_syllabus_features.append(syllabus_name)
                model["inject_syllabus_features"] = inject_syllabus_features

        option["models"] = models
    return predictor_options


prophet_config = {
    "depends": {},
    "predictor_options": get_predictor_options(),
}
