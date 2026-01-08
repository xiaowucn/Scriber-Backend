# 广发基金季报1
from remarkable.predictor.eltype import ElementType

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
        "models": [
            {
                "name": "table_row",
                "use_complete_table": True,
                "multi_elements": True,
                "unit_column_pattern": (r"[-——：]单位$",),
                "neglect_title_patterns": [
                    r"基金经理.*?简介",
                    r"管理人报告",
                ],
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
                "positions": list(range(0, 5)),
                "regs": [
                    r"(?P<dst>^东吴.*)",
                    r"(?P<dst>^广发.*)",
                    r"(?P<dst>.*报告)",
                    r"^20\d{2}年第.季度报告$",
                ],
                "filter_headers": True,
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
            }
        ],
    },
    {
        "path": ["基金管理人"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(2, 6)),
                "regs": ["基金管理人.?(?P<dst>.*?公司$)"],
            }
        ],
    },
    {
        "path": ["基金托管人"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(3, 7)),
                "regs": [r"基金托管人[:：]\s*(?P<dst>.*?公司$)"],
            }
        ],
    },
    {
        "path": ["报告送出日期"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(3, 8)),
                "regs": ["报告送出日期.?(?P<dst>.{1,10}日$)"],
            }
        ],
    },
    {
        "path": ["报告起始日"],
        "models": [
            {
                "name": "partial_text",
                "regs": ["报告期(?P<dst>自.{1,25}止.$)"],
            }
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
        "path": ["基金基本情况表格注释"],
        "models": [
            {
                "name": "table_annotate",
                "break_pattern": [r"目标基金基本情况$"],
            }
        ],
    },
    {
        "path": ["基础设施项目-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["目标基金基本情况注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["目标基金产品说明注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["主要财务指标表格注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["基金净值表现注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [
                    r"__regex__基金份额净值收益率及其与同期业绩比较基准收益率的比较",
                    r"__regex__广发货币E",
                    r"__regex__^基金净值表现$",
                ],
                "break_pattern": [r"收益率变动的比较"],
            }
        ],
    },
    {
        "path": ["自基金合同生效以来基金累计净值增长率变动及其与同期业绩比较基准收益率变动的比较-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [
                    r"__regex__[自从]基金\w{,6}以?(来|后)\w{,4}累计?\w{,5}变(动|更)(及其?|和)?与\w{,10}收益率?变?(动|更)?",
                    r"自基金合同生效以来基金累计净值增长率变动及其与同期业绩比较基准",
                ],
                "ignore_pattern": [r"管理人报告$"],
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1153
                "break_pattern": [r"^广发再融资主题灵活配置混合型证券投资基金"],
            }
        ],
    },
    {
        "path": ["其他指标-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["其他财务指标"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["本报告期及近三年的可供分配金额-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["本报告期及近三年的实际分配金额-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["本期可供分配金额计算过程-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["本期调整项与往期不一致的情况说明"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["对报告期内基础设施项目公司运营情况的整体说明"],
        "models": [
            {"name": "syllabus_elt_v2"},
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
            {"name": "table_annotate"},
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
            {"name": "table_annotate"},
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
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["经营活动现金流归集、管理、使用情况"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["对报告期内发生的影响未来项目正常现金流的重大情况与拟采取的相应措施的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "ignore_pattern": [r"^说明（如有）$"],
            }
        ],
    },
    {
        "path": ["报告期内对外借入款项基本情况"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["本期对外借入款项情况与上年同期的变化情况分析"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["报告期内购入或出售基础设施项目情况-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["购入或出售基础设施项目变化情况及对基金运作、收益等方面的影响分析"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金经理简介-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"基金经理\(或基金经理小组\)简介"],
                "break_pattern": [r"期末兼任私募资产管理计划投资经理的基金经理同时管理的产品情况$"],
            }
        ],
    },
    {
        "path": ["期末兼任私募资产管理计划投资经理的基金经理同时管理的产品情况-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["境外投资顾问为本基金提供投资建议的主要成员简介-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["管理人对报告期内本基金运作遵规守信情况的说明"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["公平交易制度的执行情况"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["异常交易行为的专项说明"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["报告期内基金的投资策略和业绩表现说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"投资策略以?[与和及]业绩表现说明"],
                "ignore_pattern": [r"^报告期内基金的业绩表现$"],
            }
        ],
    },
    {
        "path": ["报告期内基金的投资策略和运作分析"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["报告期内基金的业绩表现"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["报告期内基金持有人数或基金资产净值预警说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r"投资组合报告$"],
            }
        ],
    },
    {
        "path": ["报告期内基金费用收取情况的说明"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["公平交易制度及执行情况的专项说明"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["管理人对报告期内基金投资和运营分析"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["管理人对宏观经济及基础设施项目所在行业的简要展望"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"管理人对宏观经济及基础设施项目所在行业的简要展望"],
            }
        ],
    },
    {
        "path": ["管理人及其管理基础设施基金的经验"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金资产组合情况-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["报告期末按行业分类的境内股票投资组合-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["按行业分类的港股通投资股票投资组合-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票投资明细-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["积极投资按公允价值占基金资产净值比例大小排序的前五名股票投资明细-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["期末按公允价值占基金资产净值比例大小排序的全国中小企业股份转让系统挂牌股票投资明细-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["报告期末按债券品种分类的债券投资组合注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名债券投资明细注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名资产支持证券投资明细-注释"],
        "models": [
            {"name": "table_annotate"},
            {
                "name": "middle_paras",
                "top_anchor_regs": [r"报告期末按公允价值占基金资产净值比例大小排序的前十名资产支持证券投资"],
                "include_top_anchor": False,
                "bottom_anchor_regs": [r"报告期末按公允价值占基金资产净值比例大小排序的前五名贵金属投资明细"],
                "ignore_pattern": [r"^明细$"],
            },
        ],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名贵金属投资明细-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [
                    r"__regex__报告期末按公允价值占基金资产净值比例大小排序的前五名贵金属投资"
                ],
            },
            {
                "name": "middle_paras",
                "top_anchor_regs": [r"报告期末按公允价值占基金资产净值比例大小排序的前五名贵金属投资明"],
                "include_top_anchor": False,
                "bottom_anchor_regs": [r"报告期末按公允价值占基金资产净值比例大小排序的前五名权证投资明细"],
                "ignore_pattern": [r"^[明细]+$"],
            },
        ],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名权证投资明细-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["报告期末本基金投资的股指期货持仓和损益明细注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [r"报告期末本基金投资的股指期货持仓和损益明细"],
            },
        ],
    },
    {
        "path": ["本基金投资股指期货的投资政策"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["本期国债期货投资政策"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["报告期末本基金投资的国债期货持仓和损益明细注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["本期国债期货投资评价"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金持有股票资产"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"基金持有股票资产(?P<dst>.*?元)"],
            }
        ],
    },
    {
        "path": ["股票资产占基金资产净值的比例"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"占基金资产净值的比例为(?P<dst>.*?%)"],
            }
        ],
    },
    {
        "path": ["空头合约市值"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"空头合约市值(?P<dst>.*?元)"],
            }
        ],
    },
    {
        "path": ["空头合约市值占基金资产净值的比例"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"运用.*?占基金资产净值的比例为(?P<dst>.*?%)"],
            }
        ],
    },
    {
        "path": ["空头合约市值占股票资产的比例"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"空头合约市值占股票资产的比例为(?P<dst>.*?%)"],
            }
        ],
    },
    {
        "path": ["本基金执行市场中性策略的投资收益"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"本基金执行市场中性策略的投资收益为(?P<dst>.*?元)"],
            }
        ],
    },
    {
        "path": ["公允价值变动损益"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"公允价值变动损益为(?P<dst>.*?元)"],
            }
        ],
    },
    {
        "path": ["公允价值变动损益"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"公允价值变动损益为(?P<dst>.*?元)"],
            }
        ],
    },
    {
        "path": ["基金计价方法说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r"本基金投资的前十名证券的发行主体中"],
            }
        ],
    },
    {
        "path": ["投资组合报告附注-是否处罚"],
        "models": [
            {
                "name": "syllabus_filter",
                "first_num_para": True,
                "inject_syllabus_features": [r"投资组合报告附注"],
            }
        ],
    },
    {
        "path": ["投资组合报告附注-备选股票库"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "include_title": True,
                "remove_para_begin_number": True,
                "inject_syllabus_features": [
                    r"本报告期内，基金投资的前十名股票未出现超出基金合同规定的备选股",
                    r"__regex__本基金本报告期末?未投资股票，因此不存在投资的前十名股票超出基金合",
                    r"__regex__本基金不存在投资的前十名股票超出基金合同规定的备选股票库",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"(?P<content>本基金本报告期末?未投资股票，因此不存在投资的前十名股票超出基金合.*)"
                ],
            },
        ],
    },
    {
        "path": ["其他资产构成-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["处于转股期的可转换债券明细-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["报告期末前十名股票中存在流通受限情况的说明-注释"],
        "models": [
            {
                "name": "table_annotate",
                "break_pattern": [r"开放式基金份额变动$"],
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__报告期末前十名股票中存在流通受限情况的说明",
                ],
            },
        ],
    },
    {
        "path": ["流通受限部分的公允价值-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["投资组合报告附注的其他文字描述部分"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["报告期债券回购融资情况-注释"],
        "models": [
            {
                "name": "table_annotate",
                "break_pattern": [r"的说明$"],
            }
        ],
    },
    {
        "path": ["债券正回购的资金余额超过基金资产净值的20%的说明-备注"],
        "models": [
            {"name": "syllabus_elt_v2"},
            {
                "name": "partial_text",
                "regs": ["本报告期内本货币市场基金债券正回购的资金余额未超过资产净值的20%。"],
            },
        ],
    },
    {
        "path": ["投资组合平均剩余期限基本情况-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["报告期内投资组合平均剩余期限超过120天情况说明-注释"],
        "models": [
            {"name": "table_annotate"},
            {
                "name": "middle_paras",
                "top_anchor_regs": [r"剩余期限超过120天的?情况说明$"],
                "bottom_anchor_regs": [r"(未|没有)(发生)?超过120天的?情况"],
                "top_default": True,
                "include_top_anchor": False,
                "include_bottom_anchor": True,
                "top_greed": True,
            },
        ],
    },
    {
        "path": ["报告期末投资组合平均剩余期限分布比例-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["报告期内投资组合平均剩余存续期超过240天情况说明-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["报告期末按摊余成本占基金资产净值比例大小排名的前十名债券投资明细-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["“影子定价”与“摊余成本法”确定的基金资产净值的偏离-注释"],
        "models": [
            {"name": "table_annotate"},
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
                "name": "para_match",
                "paragraph_pattern": [r"^本基金本报告期内.*?负偏离度的绝对值达到.*?"],
            },
        ],
    },
    {
        "path": ["报告期内正偏离度的绝对值达到0.5%情况说明-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["报告期末在各个国家（地区）证券市场的股票及存托凭证投资分布-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["报告期末按行业分类的股票及存托凭证投资组合-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票及存托凭证投资明细-注释"],
        "models": [
            {
                "name": "table_annotate",
                "inject_syllabus_features": [
                    "__regex__报告期末按公允价值占基金资产净值比例大小排序的前十名股票及存[托凭证投资明细]+"
                ],
            },
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["报告期末按债券信用等级分类的债券投资组合-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排名的前五名金融衍生品投资明细-注释"],
        "models": [
            {"name": "table_annotate"},
            {"name": "syllabus_elt_v2"},
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"注.{1,3}期货投资采用当日无负债结算制度",
                    r"本基金本报告期末未持有金融衍生品",
                ],
            },
            {
                "name": "middle_paras",
                "top_anchor_regs": [r"报告期末按公允价值占基金资产净值比例大小排名的前五名金融衍生品投资明细$"],
                "bottom_anchor_regs": [r"注.{1,3}期货投资采用当日无负债结算制度"],
                "top_default": True,
                "include_top_anchor": False,
                "include_bottom_anchor": True,
                "top_greed": True,
            },
        ],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名基金投资明细-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["当期交易及持有基金产生的费用-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["本报告期持有的基金发生的重大影响事件"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r"开放式基金份额变动$"],
            }
        ],
    },
    {
        "path": ["本报告期持有的基金发生的重大影响事件-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["开放式基金份额变动-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["基金份额变动情况-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["报告期末各资产单元的资产净值及占基金资产净值的比例-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["基金投资顾问具体情况-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["基金管理人运用固有资金投资本基金交易明细-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["报告期末发起式基金发起资金持有份额情况-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["基金管理人持有本基金份额变动情况-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["报告期内单一投资者持有基金份额比例达到或超过20%的情况-注释"],
        "models": [
            {"name": "table_annotate"},
        ],
    },
    {
        "path": ["影响投资者决策的其他重要信息"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    "__regex__影响投资者决策的其他重要信息__regex__影响投资者决策的其他重要信息"
                ],
            }
        ],
    },
    {
        "path": ["备查文件目录"],
        "models": [
            {
                "name": "middle_paras",
                "top_anchor_regs": [r"备查文件目录"],
                "bottom_anchor_regs": [r"存放地点"],
                "include_top_anchor": False,
                "top_greed": False,
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["存放地点"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["查阅方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"查阅方式"],
                "ignore_pattern": [r"有限公司$", r".{1,4}年.{1,2}月.{1,3}日$"],
            }
        ],
    },
    {
        "path": ["报告期末本基金投资的股指期货交易情况说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r"^\d[\d.]+报告期末本基金投资的股指期货持仓和损益明细$"],
            }
        ],
    },
    {
        "path": ["报告期末本基金投资的国债期货交易情况说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1095#note_256706
                "break_para_pattern": [
                    r"报告期末本基金投资的国债期货持仓和损益明细$",
                    r"^\d[\d.]+本期国债期货投资政策$",
                ],
                "ignore_pattern": [r"本期国债期货投资政策$"],
            }
        ],
    },
    {
        "path": ["基金名称"],
        "models": [
            {"name": "table_kv"},
        ],
    },
    {
        "path": ["基金代码"],
        "models": [
            {"name": "table_kv"},
        ],
    },
    {
        "path": ["报告期末按摊余成本占基金资产净值比例大小排名的前十名资产支持证券投资明细"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "target_element": ElementType.PARAGRAPH.value,
                "only_inject_features": True,
                # 仅一个标注样本
                "inject_syllabus_features": [
                    "__regex__报告期末按摊余成本占基金资产净值比例大小排名的前十名资产支持证券投资明细?"
                ],
            }
        ],
    },
    {
        "path": ["业绩图标题时间-期初时间"],
        "models": [
            {
                "name": "syllabus_based",
                "include_title": False,
                "extract_from": "same_type_elements",
                "inject_syllabus_features": [r"__regex__基金净值表现"],
                "only_inject_features": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"(?P<content>[\d年月日]+)至[\d年月日]"],
                },
            },
        ],
    },
    {
        "path": ["业绩图标题时间-期末时间"],
        "models": [
            {
                "name": "syllabus_based",
                "include_title": False,
                "extract_from": "same_type_elements",
                "inject_syllabus_features": [r"__regex__基金净值表现"],
                "only_inject_features": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"[\d年月日]+至(?P<content>[\d年月日]+)"],
                },
            },
        ],
    },
    {
        "path": ["市场中性策略执行情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"市场中性策略执行情况"],
                "only_inject_features": True,
            }
        ],
    },
    {
        "path": ["报告底部日期"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(-2, 0))[::-1],
                "regs": [
                    r"(?P<dst>[\d〇一二三四五六七八九十]+年.*)",
                ],
            }
        ],
    },
]
prophet_config = {"depends": {}, "predictor_options": predictor_options}
