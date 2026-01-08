"""“广发基金季报"""

predictor_options = [
    {
        "path": ["报告期时间"],
        "sub_primary_key": ["份额名称"],
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
                "unit_column_pattern": (r"[-——：]单位$",),
                "neglect_title_patterns": [
                    r"基金经理.*?简介",
                    r"管理人报告",
                ],
            },
        ],
    },
    {
        "path": ["投资策略和运作分析"],
        "models": [
            {
                "name": "syllabus_elt_v2",
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
            },
        ],
    },
    {
        "path": ["基金主代码"],
        "models": [
            {"name": "table_kv"},
        ],
    },
    {
        "path": ["报告名称"],
        "models": [
            {
                "name": "fixed_position",
                "multi_elements": True,
                "positions": list(range(1, 4)),
                "regs": [
                    r"(?P<dst>^广发.*)",
                    r"(?P<dst>.*报告)",
                ],
            },
        ],
    },
    {
        "path": ["报告日期"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(1, 4)),
                "regs": [
                    r"(?P<dst>.{1,11}日)",
                ],
            }
        ],
    },
    {
        "path": ["基金管理人"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(3, 6)),
                "regs": [r"基金管理人.?(?P<dst>.{1,10}公司$)"],
            },
        ],
    },
    {
        "path": ["基金托管人"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(3, 6)),
                "regs": [r"基金托管人.?(?P<dst>.{1,10}公司$)"],
            },
        ],
    },
    {
        "path": ["报告送出日期"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(5, 7)),
                "regs": [r"报告送出日期.?(?P<dst>.{1,10}日$)"],
            },
        ],
    },
    {
        "path": ["报告起始日"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"本报告期自(?P<dst>.{1,25})止"],
            },
        ],
    },
    {"path": ["重要提示1"], "models": [{"name": "syllabus_filter", "important_split": True, "is_first_part": True}]},
    {
        "path": ["重要提示2"],
        "models": [{"name": "syllabus_filter", "important_split": True, "is_first_part": False}],
    },
    {
        "path": ["基金名称"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(1, 4)),
                "regs": [
                    r"(?P<dst>^广发.*基金(（FOF）)?)",
                ],
            },
        ],
    },
    {
        "path": ["基金简称"],
        "models": [
            {
                "name": "table_kv",
            }
        ],
    },
    {"path": ["场内简称"], "models": [{"name": "table_kv"}]},
    {
        "path": ["基金代码"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["交易代码"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["基金运作方式"],
        "models": [
            {"name": "table_kv"},
        ],
    },
    {
        "path": ["报告期末基金份额总额"],
        "models": [
            {"name": "table_kv"},
        ],
    },
    {
        "path": ["基金合同生效日"],
        "models": [
            {"name": "table_kv"},
        ],
    },
    {"path": ["基金合同存续期"], "models": [{"name": "partial_text"}]},
    {"path": ["基金份额上市的证券交易所"], "models": [{"name": "partial_text"}]},
    {"path": ["上市日期"], "models": [{"name": "partial_text"}]},
    {"path": ["投资目标"], "models": [{"name": "table_kv"}]},
    {
        "path": ["投资策略"],
        "models": [
            {
                "name": "table_kv",
            },
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"基金资产组合进行积极管理"],
                "content_pattern": [
                    r"(?P<dst>.*基金资产组合进行积极管理)",
                ],
            },
        ],
        "pick_answer_strategy": "all",
    },
    {"path": ["业绩比较基准（若有）"], "models": [{"name": "table_kv"}]},
    {"path": ["风险收益特征（若有）"], "models": [{"name": "table_kv"}]},
    {"path": ["基金管理人-基金基本情况"], "models": [{"name": "table_kv"}]},
    {"path": ["基金托管人-基金基本情况"], "models": [{"name": "table_kv"}]},
    {"path": ["基金收益分配政策"], "models": [{"name": "partial_text"}]},
    {"path": ["资产支持证券管理人"], "models": [{"name": "partial_text"}]},
    {"path": ["外部管理机构"], "models": [{"name": "partial_text"}]},
    {"path": ["基金投资顾问"], "models": [{"name": "partial_text"}]},
    {"path": ["基金保证人"], "models": [{"name": "partial_text"}]},
    {
        "path": ["下属分级基金的基金简称"],
        "models": [
            {
                "name": "row_match",
                "merge_row": False,
                "multi": True,
                "row_pattern": [r"下属.级基金的基金简称"],
                "content_pattern": [
                    r"(?P<dst>广发.*)",
                ],
            },
        ],
    },
    {
        "path": ["下属分级基金场内简称"],
        "models": [
            {
                "name": "row_match",
                "merge_row": False,
                "multi": True,
                "row_pattern": [r"下属.级基金的场内简称"],
                "content_pattern": [
                    r"(?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["下属分级基金的交易代码"],
        "models": [
            {
                "name": "row_match",
                "merge_row": False,
                "multi": True,
                "row_pattern": [r"下属.级基金的交易代码"],
                "content_pattern": [
                    r"(?P<dst>\d+)",
                ],
            },
        ],
    },
    {
        "path": ["报告期末下属分级基金的份额总额"],
        "models": [
            {
                "name": "row_match",
                "merge_row": False,
                "multi": True,
                "row_pattern": [r"报告期末下属.级基金的份额总额"],
                "content_pattern": [
                    r"(?P<dst>.*份$)",
                ],
            },
        ],
    },
    {"path": ["下属分级基金的风险收益特征"], "models": [{"name": "partial_text"}]},
    {"path": ["境外投资顾问英文名称"], "models": [{"name": "partial_text"}]},
    {"path": ["境外投资顾问中文名称"], "models": [{"name": "partial_text"}]},
    {"path": ["境外资产托管人英文名称"], "models": [{"name": "table_kv"}]},
    {"path": ["境外资产托管人中文名称"], "models": [{"name": "table_kv"}]},
    {
        "path": ["基金基本情况表格注释"],
        "models": [
            {
                "name": "para_match",
                "multi_elements": True,
                "combine_paragraphs": True,
                "paragraph_pattern": [r"注.{1,3}\d.{1,3}自\d+年\d+月\d+日起", r"\d.{1,3}广发添利交易"],
            },
        ],
    },
    {"path": ["基础设施项目名称"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司名称"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目类型"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目主要经营模式"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目地理位置"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["目标基金名称"], "models": [{"name": "table_kv"}]},
    {"path": ["目标基金主代码"], "models": [{"name": "table_kv"}]},
    {"path": ["目标基金运作方式"], "models": [{"name": "table_kv"}]},
    {"path": ["目标基金合同生效日"], "models": [{"name": "table_kv"}]},
    {"path": ["目标基金份额上市的证券交易所"], "models": [{"name": "table_kv"}]},
    {"path": ["目标基金上市日期"], "models": [{"name": "table_kv"}]},
    {"path": ["目标基金管理人名称"], "models": [{"name": "table_kv"}]},
    {"path": ["目标基金托管人名称"], "models": [{"name": "table_kv"}]},
    {"path": ["目标基金基本情况注释"], "models": [{"name": "partial_text"}]},
    {"path": ["目标基金投资目标"], "models": [{"name": "table_kv"}]},
    {"path": ["目标基金投资策略"], "models": [{"name": "table_kv"}]},
    {"path": ["目标基金业绩比较基准"], "models": [{"name": "table_kv"}]},
    {"path": ["目标基金风险收益特征"], "models": [{"name": "table_kv"}]},
    {"path": ["目标基金产品说明注释"], "models": [{"name": "partial_text"}]},
    {"path": ["主要财务指标", "基金名称"], "models": [{"name": "partial_text"}]},
    {"path": ["主要财务指标", "财务指标", "本期已实现收益"], "models": [{"name": "partial_text"}]},
    {"path": ["主要财务指标", "财务指标", "本期利润"], "models": [{"name": "partial_text"}]},
    {"path": ["主要财务指标", "财务指标", "加权平均基金份额本期利润"], "models": [{"name": "partial_text"}]},
    {"path": ["主要财务指标", "财务指标", "期末基金资产净值"], "models": [{"name": "partial_text"}]},
    {"path": ["主要财务指标", "财务指标", "期末基金份额净值"], "models": [{"name": "partial_text"}]},
    {"path": ["主要财务指标", "财务指标", "本期收入"], "models": [{"name": "partial_text"}]},
    {"path": ["主要财务指标", "财务指标", "本期净利润"], "models": [{"name": "partial_text"}]},
    {"path": ["主要财务指标", "财务指标", "本期经营活动产生的现金流量净额"], "models": [{"name": "partial_text"}]},
    {"path": ["主要财务指标", "指标单位"], "models": [{"name": "partial_text"}]},
    {
        "path": ["主要财务指标表格注释"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [r"注：本期已实现收益指基金本期利息收入"],
            },
        ],
    },
    # {"path": ["基金净值表现", "基金名称"], "models": [{"name": "partial_text"}]},
    {
        "path": [
            "基金净值表现",
            "基金份额净值增长率及其与同期业绩比较基准收益率的比较",
        ],
        "multi_elements": True,
        "sub_primary_key": ["阶段"],
        "models": [
            {
                "name": "abc",
                "净值增长率标准差②": {
                    "feature_black_list": [
                        r"业绩比较基准收益率③",
                    ],
                },
                "净值收益率标准差②": {
                    "feature_black_list": [
                        r"业绩比较基准收益率③",
                    ],
                },
            }
        ],
    },
    {
        "path": ["基金净值表现注释"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [r"注.{1,3}本基金\w类基金", r"注.{1,3}本基金收益分配按日结转份额"],
            }
        ],
    },
    {
        "path": [
            "自基金合同生效以来基金累计净值增长率变动及其与同期业绩比较基准收益率变动的比较",
            "基金始末时间",
            "基金名称",
        ],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": [
            "自基金合同生效以来基金累计净值增长率变动及其与同期业绩比较基准收益率变动的比较",
            "基金始末时间",
            "期初时间",
        ],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": [
            "自基金合同生效以来基金累计净值增长率变动及其与同期业绩比较基准收益率变动的比较",
            "基金始末时间",
            "期末时间",
        ],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["自基金合同生效以来基金累计净值增长率变动及其与同期业绩比较基准收益率变动的比较-注释"],
        "models": [
            {
                "name": "para_match",
                "combine_paragraphs": True,
                "multi_elements": True,
                "paragraph_pattern": [
                    r"注.{1,3}自\d+年\d+月\d+日起.本基金的业绩比较基准",
                    r"注.{1,4}本基金合同生效",
                    r".{1,3}本基金建仓期为",
                ],
            },
        ],
    },
    {"path": ["其他指标"], "models": [{"name": "partial_text"}]},
    {"path": ["其他指标数据", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["其他指标数据", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["其他指标-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["其他财务指标"], "models": [{"name": "partial_text"}]},
    {"path": ["本报告期及近三年的可供分配金额", "期间"], "models": [{"name": "partial_text"}]},
    {"path": ["本报告期及近三年的可供分配金额", "可供分配金额", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["本报告期及近三年的可供分配金额", "可供分配金额", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["本报告期及近三年的可供分配金额", "单位可供分配金额", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["本报告期及近三年的可供分配金额", "单位可供分配金额", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["本报告期及近三年的可供分配金额", "备注"], "models": [{"name": "partial_text"}]},
    {"path": ["本报告期及近三年的可供分配金额-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["本报告期及近三年的实际分配金额", "期间"], "models": [{"name": "partial_text"}]},
    {"path": ["本报告期及近三年的实际分配金额", "实际分配金额", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["本报告期及近三年的实际分配金额", "实际分配金额", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["本报告期及近三年的实际分配金额", "单位实际分配金额", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["本报告期及近三年的实际分配金额", "单位实际分配金额", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["本报告期及近三年的实际分配金额", "备注"], "models": [{"name": "partial_text"}]},
    {"path": ["本报告期及近三年的实际分配金额-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["本期可供分配金额计算过程", "项目"], "models": [{"name": "partial_text"}]},
    {"path": ["本期可供分配金额计算过程", "金额", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["本期可供分配金额计算过程", "金额", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["本期可供分配金额计算过程", "备注"], "models": [{"name": "partial_text"}]},
    {"path": ["本期可供分配金额计算过程-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["本期调整项与往期不一致的情况说明"], "models": [{"name": "partial_text"}]},
    {"path": ["对报告期内基础设施项目公司运营情况的整体说明"], "models": [{"name": "partial_text"}]},
    {"path": ["营业收入分析-基础设施项目公司名称"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的营业收入分析-本期"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的营业收入分析-上年同期"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的营业收入分析", "序号"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的营业收入分析", "构成"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的营业收入分析", "本期-金额（元）", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的营业收入分析", "本期-金额（元）", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的营业收入分析", "本期-占该项目总收入比例（%）"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的营业收入分析", "上期-金额（元）", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的营业收入分析", "上期-金额（元）", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的营业收入分析", "上期-占该项目总收入比例（%）"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的营业收入分析-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["营业成本及费用分析-基础设施项目公司名称"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的营业成本及费用分析-本期"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的营业成本及费用分析-上年同期"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的营业成本及主要费用分析", "序号"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的营业成本及主要费用分析", "构成"], "models": [{"name": "partial_text"}]},
    {
        "path": ["基础设施项目公司的营业成本及主要费用分析", "本期金额（元）", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["基础设施项目公司的营业成本及主要费用分析", "本期金额（元）", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["基础设施项目公司的营业成本及主要费用分析", "本期占该项目总成本比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["基础设施项目公司的营业成本及主要费用分析", "上年同期金额（元）", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["基础设施项目公司的营业成本及主要费用分析", "上年同期金额（元）", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["基础设施项目公司的营业成本及主要费用分析", "上年同期占该项目总成本比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["基础设施项目公司的营业成本及主要费用分析-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["指标分析-基础设施项目公司名称"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的财务业绩衡量指标分析", "序号"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的财务业绩衡量指标分析", "指标名称"], "models": [{"name": "partial_text"}]},
    {
        "path": ["基础设施项目公司的财务业绩衡量指标分析", "只标含义说明及计算公式"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["基础设施项目公司的财务业绩衡量指标分析", "指标单位"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的财务业绩衡量指标分析", "本期指标数值"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的财务业绩衡量指标分析", "上年同期指标数值"], "models": [{"name": "partial_text"}]},
    {"path": ["基础设施项目公司的财务业绩衡量指标分析-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["经营活动现金流归集、管理、使用情况"], "models": [{"name": "partial_text"}]},
    {
        "path": ["对报告期内发生的影响未来项目正常现金流的重大情况与拟采取的相应措施的说明"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["报告期内对外借入款项基本情况"], "models": [{"name": "partial_text"}]},
    {"path": ["本期对外借入款项情况与上年同期的变化情况分析"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内购入或出售基础设施项目情况", "序号"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内购入或出售基础设施项目情况", "项目名称"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内购入或出售基础设施项目情况", "交易成交方向"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内购入或出售基础设施项目情况", "交易对手"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内购入或出售基础设施项目情况", "交易价格", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内购入或出售基础设施项目情况", "交易价格", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内购入或出售基础设施项目情况", "项目账面价值", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内购入或出售基础设施项目情况", "项目账面价值", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内购入或出售基础设施项目情况", "项目评估价格", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内购入或出售基础设施项目情况", "项目评估价格", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内购入或出售基础设施项目情况", "评估方法"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内购入或出售基础设施项目情况", "备注"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内购入或出售基础设施项目情况-注释"], "models": [{"name": "partial_text"}]},
    {
        "path": ["购入或出售基础设施项目变化情况及对基金运作、收益等方面的影响分析"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["基金经理简介", "姓名"], "models": [{"name": "partial_text"}]},
    {"path": ["基金经理简介", "职务"], "models": [{"name": "partial_text"}]},
    {"path": ["基金经理简介", "任职日期"], "models": [{"name": "partial_text"}]},
    {"path": ["基金经理简介", "离任日期"], "models": [{"name": "partial_text"}]},
    {"path": ["基金经理简介", "证券从业年限"], "models": [{"name": "partial_text"}]},
    {"path": ["基金经理简介", "基础设施项目运营或投资管理年限"], "models": [{"name": "partial_text"}]},
    {"path": ["基金经理简介", "基础设施项目运营或投资管理经验"], "models": [{"name": "partial_text"}]},
    {"path": ["基金经理简介", "说明"], "models": [{"name": "partial_text"}]},
    {
        "path": ["基金经理简介-注释"],
        "models": [
            {
                "name": "para_match",
                "multi_elements": True,
                "combine_paragraphs": True,
                "paragraph_pattern": [r"注.{1,3}\d.{1,3}任职日期", r"\d.{1,3}证券从业"],
            }
        ],
    },
    {
        "path": ["期末兼任私募资产管理计划投资经理的基金经理同时管理的产品情况", "姓名"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["期末兼任私募资产管理计划投资经理的基金经理同时管理的产品情况", "产品类型"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["期末兼任私募资产管理计划投资经理的基金经理同时管理的产品情况", "产品数量"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["期末兼任私募资产管理计划投资经理的基金经理同时管理的产品情况", "资产净值", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["期末兼任私募资产管理计划投资经理的基金经理同时管理的产品情况", "资产净值", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["期末兼任私募资产管理计划投资经理的基金经理同时管理的产品情况", "任职时间"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["期末兼任私募资产管理计划投资经理的基金经理同时管理的产品情况-注释"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["境外投资顾问为本基金提供投资建议的主要成员简介", "姓名"], "models": [{"name": "partial_text"}]},
    {
        "path": ["境外投资顾问为本基金提供投资建议的主要成员简介", "在境外投资顾问所任职务"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["境外投资顾问为本基金提供投资建议的主要成员简介", "证券从业年限"], "models": [{"name": "partial_text"}]},
    {"path": ["境外投资顾问为本基金提供投资建议的主要成员简介", "说明"], "models": [{"name": "partial_text"}]},
    {"path": ["境外投资顾问为本基金提供投资建议的主要成员简介-注释"], "models": [{"name": "partial_text"}]},
    {
        "path": ["管理人对报告期内本基金运作遵规守信情况的说明"],
        "models": [{"name": "syllabus_elt_v2"}],
    },
    {
        "path": ["公平交易制度的执行情况"],
        "models": [{"name": "syllabus_elt_v2"}],
    },
    {
        "path": ["异常交易行为的专项说明"],
        "models": [{"name": "syllabus_elt_v2"}],
    },
    {"path": ["报告期内基金的投资策略和运作分析"], "models": [{"name": "syllabus_elt_v2"}]},
    {
        "path": ["报告期内基金的业绩表现"],
        "models": [{"name": "syllabus_elt_v2"}],
    },
    {"path": ["报告期内基金的投资策略和业绩表现说明"], "models": [{"name": "syllabus_elt_v2"}]},
    {"path": ["报告期内基金持有人数或基金资产净值预警说明"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内基金费用收取情况的说明"], "models": [{"name": "partial_text"}]},
    {"path": ["公平交易制度及执行情况的专项说明"], "models": [{"name": "partial_text"}]},
    {"path": ["管理人对报告期内基金投资和运营分析"], "models": [{"name": "partial_text"}]},
    {"path": ["管理人对宏观经济及基础设施项目所在行业的简要展望"], "models": [{"name": "partial_text"}]},
    {"path": ["管理人及其管理基础设施基金的经验"], "models": [{"name": "partial_text"}]},
    {"path": ["基金资产组合情况", "序号"], "models": [{"name": "partial_text"}]},
    {"path": ["基金资产组合情况", "项目"], "models": [{"name": "partial_text"}]},
    {"path": ["基金资产组合情况", "金额", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["基金资产组合情况", "金额", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["基金资产组合情况", "币种"], "models": [{"name": "partial_text"}]},
    {"path": ["基金资产组合情况", "占基金总资产的比例（%）"], "models": [{"name": "partial_text"}]},
    {"path": ["基金资产组合情况-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末按行业分类的境内股票投资组合", "行业类别"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末按行业分类的境内股票投资组合", "公允价值", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末按行业分类的境内股票投资组合", "公允价值", "单位"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期末按行业分类的境内股票投资组合", "占基金资产净值比例（％）"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["报告期末按行业分类的境内股票投资组合-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["按行业分类的港股通投资股票投资组合", "行业类别"], "models": [{"name": "partial_text"}]},
    {"path": ["按行业分类的港股通投资股票投资组合", "公允价值"], "models": [{"name": "partial_text"}]},
    {"path": ["按行业分类的港股通投资股票投资组合", "公允价值币种"], "models": [{"name": "partial_text"}]},
    {"path": ["按行业分类的港股通投资股票投资组合", "占基金资产净值比例（%）"], "models": [{"name": "partial_text"}]},
    {"path": ["按行业分类的港股通投资股票投资组合-注释"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票投资明细", "序号"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票投资明细", "股票代码"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票投资明细", "股票名称"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票投资明细", "数量（股）", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票投资明细", "数量（股）", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票投资明细", "公允价值", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票投资明细", "公允价值", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票投资明细", "占基金资产净值比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票投资明细-注释"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["积极投资按公允价值占基金资产净值比例大小排序的前五名股票投资明细", "序号"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["积极投资按公允价值占基金资产净值比例大小排序的前五名股票投资明细", "股票代码"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["积极投资按公允价值占基金资产净值比例大小排序的前五名股票投资明细", "股票名称"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["积极投资按公允价值占基金资产净值比例大小排序的前五名股票投资明细", "数量（股）", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["积极投资按公允价值占基金资产净值比例大小排序的前五名股票投资明细", "数量（股）", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["积极投资按公允价值占基金资产净值比例大小排序的前五名股票投资明细", "公允价值", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["积极投资按公允价值占基金资产净值比例大小排序的前五名股票投资明细", "公允价值", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["积极投资按公允价值占基金资产净值比例大小排序的前五名股票投资明细", "占基金资产净值比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["积极投资按公允价值占基金资产净值比例大小排序的前五名股票投资明细-注释"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["期末按公允价值占基金资产净值比例大小排序的全国中小企业股份转让系统挂牌股票投资明细", "序号"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["期末按公允价值占基金资产净值比例大小排序的全国中小企业股份转让系统挂牌股票投资明细", "股票代码"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["期末按公允价值占基金资产净值比例大小排序的全国中小企业股份转让系统挂牌股票投资明细", "股票名称"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": [
            "期末按公允价值占基金资产净值比例大小排序的全国中小企业股份转让系统挂牌股票投资明细",
            "数量（股）",
            "数值",
        ],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": [
            "期末按公允价值占基金资产净值比例大小排序的全国中小企业股份转让系统挂牌股票投资明细",
            "数量（股）",
            "单位",
        ],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": [
            "期末按公允价值占基金资产净值比例大小排序的全国中小企业股份转让系统挂牌股票投资明细",
            "公允价值",
            "数值",
        ],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": [
            "期末按公允价值占基金资产净值比例大小排序的全国中小企业股份转让系统挂牌股票投资明细",
            "公允价值",
            "单位",
        ],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": [
            "期末按公允价值占基金资产净值比例大小排序的全国中小企业股份转让系统挂牌股票投资明细",
            "占基金资产净值比例（%）",
        ],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["期末按公允价值占基金资产净值比例大小排序的全国中小企业股份转让系统挂牌股票投资明细-注释"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["报告期末按债券品种分类的债券投资组合", "序号"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末按债券品种分类的债券投资组合", "债券品种"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末按债券品种分类的债券投资组合", "摊余成本", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末按债券品种分类的债券投资组合", "摊余成本", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末按债券品种分类的债券投资组合", "公允价值", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末按债券品种分类的债券投资组合", "公允价值", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末按债券品种分类的债券投资组合", "占基金资产净值比例（%）"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末按债券品种分类的债券投资组合注释"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名债券投资明细", "序号"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名债券投资明细", "债券代码"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名债券投资明细", "债券名称"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名债券投资明细", "数量（张）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名债券投资明细", "公允价值", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名债券投资明细", "公允价值", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名债券投资明细", "占基金资产净值比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名债券投资明细注释"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名资产支持证券投资明细", "序号"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名资产支持证券投资明细", "证券代码"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名资产支持证券投资明细", "证券名称"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名资产支持证券投资明细", "数量（份）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名资产支持证券投资明细", "公允价值", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名资产支持证券投资明细", "公允价值", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名资产支持证券投资明细", "占基金资产净值比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名资产支持证券投资明细-注释"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名贵金属投资明细", "序号"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名贵金属投资明细", "贵金属代码"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名贵金属投资明细", "贵金属名称"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名贵金属投资明细", "数量（份）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名贵金属投资明细", "公允价值", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名贵金属投资明细", "公允价值", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名贵金属投资明细", "占基金资产净值比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名贵金属投资明细-注释"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名权证投资明细", "序号"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名权证投资明细", "权证代码"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名权证投资明细", "权证名称"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名权证投资明细", "数量（份）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名权证投资明细", "公允价值", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名权证投资明细", "公允价值", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名权证投资明细", "占基金资产净值比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前五名权证投资明细-注释"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["报告期末本基金投资的股指期货持仓和损益明细", "代码"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末本基金投资的股指期货持仓和损益明细", "名称"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末本基金投资的股指期货持仓和损益明细", "持仓量（买或卖）"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末本基金投资的股指期货持仓和损益明细", "合约市值", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末本基金投资的股指期货持仓和损益明细", "合约市值", "单位"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期末本基金投资的股指期货持仓和损益明细", "公允价值变动", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末本基金投资的股指期货持仓和损益明细", "公允价值变动", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["报告期末本基金投资的股指期货持仓和损益明细", "风险说明"], "models": [{"name": "partial_text"}]},
    {"path": ["公允价值变动总额合计-股指期货", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["公允价值变动总额合计-股指期货", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["股指期货投资本期收益-股指期货", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["股指期货投资本期收益-股指期货", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["股指期货收资本期公允价值变动-股指期货", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["股指期货收资本期公允价值变动-股指期货", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末本基金投资的股指期货持仓和损益明细注释"], "models": [{"name": "partial_text"}]},
    {"path": ["本基金投资股指期货的投资政策"], "models": [{"name": "partial_text"}]},
    {"path": ["本期国债期货投资政策"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末本基金投资的国债期货持仓和损益明细", "代码"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末本基金投资的国债期货持仓和损益明细", "名称"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末本基金投资的国债期货持仓和损益明细", "持仓量（买或卖）"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末本基金投资的国债期货持仓和损益明细", "合约市值", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末本基金投资的国债期货持仓和损益明细", "合约市值", "单位"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期末本基金投资的国债期货持仓和损益明细", "公允价值变动", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末本基金投资的国债期货持仓和损益明细", "公允价值变动", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["报告期末本基金投资的国债期货持仓和损益明细", "风险指标说明"], "models": [{"name": "partial_text"}]},
    {"path": ["公允价值变动总额合计-国债期货", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["公允价值变动总额合计-国债期货", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["国债期货投资本期收益", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["国债期货投资本期收益", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["国债期货投资本期公允价值变动", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["国债期货投资本期公允价值变动", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末本基金投资的国债期货持仓和损益明细注释"], "models": [{"name": "partial_text"}]},
    {"path": ["本期国债期货投资评价"], "models": [{"name": "partial_text"}]},
    {"path": ["基金持有股票资产", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["基金持有股票资产", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["股票资产占基金资产净值的比例"], "models": [{"name": "partial_text"}]},
    {"path": ["空头合约市值", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["空头合约市值", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["市值占基金资产净值的比例"], "models": [{"name": "partial_text"}]},
    {"path": ["空头合约市值占股票资产的比例"], "models": [{"name": "partial_text"}]},
    {"path": ["本基金执行市场中性策略的投资收益", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["本基金执行市场中性策略的投资收益", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["公允价值变动损益", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["公允价值变动损益", "单位"], "models": [{"name": "partial_text"}]},
    {
        "path": ["投资组合报告附注-是否处罚"],
        "models": [{"name": "syllabus_elt_v2", "include_title": True}],
    },
    {"path": ["投资组合报告附注-备选股票库"], "models": [{"name": "syllabus_elt_v2", "include_title": True}]},
    {"path": ["其他资产构成", "序号"], "models": [{"name": "partial_text"}]},
    {"path": ["其他资产构成", "名称"], "models": [{"name": "partial_text"}]},
    {"path": ["其他资产构成", "金额", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["其他资产构成", "金额", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["其他资产构成-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["处于转股期的可转换债券明细", "序号"], "models": [{"name": "partial_text"}]},
    {"path": ["处于转股期的可转换债券明细", "债券代码"], "models": [{"name": "partial_text"}]},
    {"path": ["处于转股期的可转换债券明细", "债券名称"], "models": [{"name": "partial_text"}]},
    {"path": ["处于转股期的可转换债券明细", "公允价值", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["处于转股期的可转换债券明细", "公允价值", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["处于转股期的可转换债券明细", "占基金资产净值比例（%）"], "models": [{"name": "partial_text"}]},
    {"path": ["处于转股期的可转换债券明细-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末前十名股票中存在流通受限情况的说明", "序号"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末前十名股票中存在流通受限情况的说明", "股票代码"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末前十名股票中存在流通受限情况的说明", "股票名称"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末前十名股票中存在流通受限情况的说明", "公司名称"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期末前十名股票中存在流通受限情况的说明", "流通受限部分的公允价值", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末前十名股票中存在流通受限情况的说明", "流通受限部分的公允价值", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末前十名股票中存在流通受限情况的说明", "占基金资产净值比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["报告期末前十名股票中存在流通受限情况的说明", "流通受限情况说明"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末前十名股票中存在流通受限情况的说明-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["期末积极投资前五名股票中存在流通受限情况的说明", "序号"], "models": [{"name": "partial_text"}]},
    {"path": ["期末积极投资前五名股票中存在流通受限情况的说明", "股票代码"], "models": [{"name": "partial_text"}]},
    {"path": ["期末积极投资前五名股票中存在流通受限情况的说明", "股票名称"], "models": [{"name": "partial_text"}]},
    {
        "path": ["期末积极投资前五名股票中存在流通受限情况的说明", "流通受限部分的公允价值", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["期末积极投资前五名股票中存在流通受限情况的说明", "流通受限部分的公允价值", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["期末积极投资前五名股票中存在流通受限情况的说明", "占基金资产净值比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["期末积极投资前五名股票中存在流通受限情况的说明", "流通受限情况说明"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["流通受限部分的公允价值-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["投资组合报告附注的其他文字描述部分"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期债券回购融资情况", "项目"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期债券回购融资情况", "金额", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期债券回购融资情况", "金额", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期债券回购融资情况", "占基金资产净值比例（%）"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期债券回购融资情况-注释"],
        "models": [
            {"name": "para_match", "paragraph_pattern": [r"注：报告期内债券回购融资余额"]},
        ],
    },
    {"path": ["债券正回购的资金余额超过基金资产净值的20%的说明", "序号"], "models": [{"name": "partial_text"}]},
    {"path": ["债券正回购的资金余额超过基金资产净值的20%的说明", "发生日期"], "models": [{"name": "partial_text"}]},
    {
        "path": ["债券正回购的资金余额超过基金资产净值的20%的说明", "融资余额占基金资产净值比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["债券正回购的资金余额超过基金资产净值的20%的说明", "原因"], "models": [{"name": "partial_text"}]},
    {"path": ["债券正回购的资金余额超过基金资产净值的20%的说明", "调整期"], "models": [{"name": "partial_text"}]},
    {"path": ["债券正回购的资金余额超过基金资产净值的20%的说明-备注"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期末投资组合平均剩余期限"],
        "models": [
            {"name": "table_kv"},
        ],
    },
    {
        "path": ["报告期内投资组合平均剩余期限最高值"],
        "models": [
            {"name": "table_kv"},
        ],
    },
    {
        "path": ["报告期内投资组合平均剩余期限最低值"],
        "models": [
            {"name": "table_kv"},
        ],
    },
    {"path": ["投资组合平均剩余期限基本情况-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内投资组合平均剩余期限超过120天情况说明", "序号"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内投资组合平均剩余期限超过120天情况说明", "发生日期"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内投资组合平均剩余期限超过120天情况说明", "平均剩余期限"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内投资组合平均剩余期限超过120天情况说明", "原因"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内投资组合平均剩余期限超过120天情况说明", "调整期"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内投资组合平均剩余期限超过120天情况说明-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末投资组合平均剩余期限分布比例", "平均剩余期限"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期末投资组合平均剩余期限分布比例", "各期限资产占基金资产净值的比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末投资组合平均剩余期限分布比例", "各期限负债占基金资产净值的比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["报告期末投资组合平均剩余期限分布比例-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内投资组合平均剩余存续期超过240天情况说明", "序号"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内投资组合平均剩余存续期超过240天情况说明", "发生日期"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期内投资组合平均剩余存续期超过240天情况说明", "平均剩余存续期"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["报告期内投资组合平均剩余存续期超过240天情况说明", "原因"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内投资组合平均剩余存续期超过240天情况说明", "调整期"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内投资组合平均剩余存续期超过240天情况说明-注释"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期末按摊余成本占基金资产净值比例大小排名的前十名债券投资明细", "序号"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按摊余成本占基金资产净值比例大小排名的前十名债券投资明细", "债券代码"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按摊余成本占基金资产净值比例大小排名的前十名债券投资明细", "债券名称"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按摊余成本占基金资产净值比例大小排名的前十名债券投资明细", "债券数量（张）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按摊余成本占基金资产净值比例大小排名的前十名债券投资明细", "摊余成本", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按摊余成本占基金资产净值比例大小排名的前十名债券投资明细", "摊余成本", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按摊余成本占基金资产净值比例大小排名的前十名债券投资明细", "占基金资产净值比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按摊余成本占基金资产净值比例大小排名的前十名债券投资明细-注释"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期内偏离度的绝对值在0.25（含）-0.5%间的次数"],
        "models": [
            {"name": "table_kv"},
        ],
    },
    {
        "path": ["报告期内偏离度的最高值"],
        "models": [
            {"name": "table_kv"},
        ],
    },
    {
        "path": ["报告期内偏离度的最低值"],
        "models": [
            {"name": "table_kv"},
        ],
    },
    {
        "path": ["报告期内每个工作日偏离度的绝对值的简单平均值"],
        "models": [
            {"name": "table_kv"},
        ],
    },
    {"path": ["“影子定价”与“摊余成本法”确定的基金资产净值的偏离-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内负偏离度的绝对值达到0.25%情况说明", "序号"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内负偏离度的绝对值达到0.25%情况说明", "发生日期"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内负偏离度的绝对值达到0.25%情况说明", "偏离度"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内负偏离度的绝对值达到0.25%情况说明", "原因"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内负偏离度的绝对值达到0.25%情况说明", "调整期"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内负偏离度的绝对值达到0.25%情况说明-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内正偏离度的绝对值达到0.5%情况说明", "序号"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内正偏离度的绝对值达到0.5%情况说明", "发生日期"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内正偏离度的绝对值达到0.5%情况说明", "偏离度"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内正偏离度的绝对值达到0.5%情况说明", "原因"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内正偏离度的绝对值达到0.5%情况说明", "调整期"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期内正偏离度的绝对值达到0.5%情况说明-注释"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期末在各个国家（地区）证券市场的股票及存托凭证投资分布", "国家（地区）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末在各个国家（地区）证券市场的股票及存托凭证投资分布", "公允价值", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末在各个国家（地区）证券市场的股票及存托凭证投资分布", "公允价值", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末在各个国家（地区）证券市场的股票及存托凭证投资分布", "币种"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末在各个国家（地区）证券市场的股票及存托凭证投资分布", "占基金资产净值比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末在各个国家（地区）证券市场的股票及存托凭证投资分布-注释"],
        "models": [
            {
                "name": "para_match",
                "combine_paragraphs": True,
                "multi_elements": True,
                "paragraph_pattern": [r"注.{1,4}国家（地区）类别", r"[(（）)\d]+ADR"],
            }
        ],
    },
    {"path": ["报告期末按行业分类的股票及存托凭证投资组合", "行业类别"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末按行业分类的股票及存托凭证投资组合", "公允价值", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末按行业分类的股票及存托凭证投资组合", "公允价值", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末按行业分类的股票及存托凭证投资组合", "币种"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期末按行业分类的股票及存托凭证投资组合", "占基金资产净值比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按行业分类的股票及存托凭证投资组合-注释"],
        "models": [
            {"name": "para_match", "paragraph_pattern": [r"注.{1,3}以上分类采用彭博提供的国际通用行业分类标准"]}
        ],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票及存托凭证投资明细", "序号"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票及存托凭证投资明细", "公司名称英文"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票及存托凭证投资明细", "公司名称中文"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票及存托凭证投资明细", "证券代码"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票及存托凭证投资明细", "所在证券市场"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票及存托凭证投资明细", "所属国家（地区）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票及存托凭证投资明细", "数量（股）", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票及存托凭证投资明细", "数量（股）", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票及存托凭证投资明细", "公允价值", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票及存托凭证投资明细", "公允价值", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票及存托凭证投资明细", "公允价值币种"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": [
            "报告期末按公允价值占基金资产净值比例大小排序的前十名股票及存托凭证投资明细",
            "占基金资产净值比例（%）",
        ],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名股票及存托凭证投资明细-注释"],
        "models": [{"name": "para_match", "paragraph_pattern": [r"注.{1,3}此处所用证券代码的类别是当地市场代码"]}],
    },
    {"path": ["报告期末按债券信用等级分类的债券投资组合", "债券信用等级"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末按债券信用等级分类的债券投资组合", "公允价值", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末按债券信用等级分类的债券投资组合", "公允价值", "单位"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期末按债券信用等级分类的债券投资组合", "占基金资产净值比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["报告期末按债券信用等级分类的债券投资组合-注释"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排名的前五名金融衍生品投资明细", "序号"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排名的前五名金融衍生品投资明细", "衍生品类别"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排名的前五名金融衍生品投资明细", "衍生品名称"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排名的前五名金融衍生品投资明细", "公允价值", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排名的前五名金融衍生品投资明细", "公允价值", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排名的前五名金融衍生品投资明细", "币种"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排名的前五名金融衍生品投资明细", "占基金资产净值比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排名的前五名金融衍生品投资明细-注释"],
        "models": [{"name": "para_match", "paragraph_pattern": [r"注.{1,3}期货投资采用当日无负债结算制度"]}],
    },
    {
        "path": ["基金计价方法说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名基金投资明细", "序号"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名基金投资明细", "基金代码"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名基金投资明细", "基金名称"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名基金投资明细", "基金类型"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名基金投资明细", "运作方式"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名基金投资明细", "管理人"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名基金投资明细", "持有份额（份）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名基金投资明细", "公允价值", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名基金投资明细", "公允价值", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名基金投资明细", "占基金资产净值比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": [
            "报告期末按公允价值占基金资产净值比例大小排序的前十名基金投资明细",
            "是否属于基金管理人及管理人关联方所管理的基金",
        ],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末按公允价值占基金资产净值比例大小排序的前十名基金投资明细-注释"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["当期交易及持有基金产生的费用", "项目"], "models": [{"name": "partial_text"}]},
    {"path": ["当期交易及持有基金产生的费用", "本期费用", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["当期交易及持有基金产生的费用", "本期费用", "单位"], "models": [{"name": "partial_text"}]},
    {
        "path": ["当期交易及持有基金产生的费用", "其中：交易及持有基金管理人以及管理人关联方所管理基金产生的费用"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["当期交易及持有基金产生的费用-注释"],
        "models": [
            {
                "name": "para_match",
                "multi_elements": True,
                "combine_paragraphs": True,
                "paragraph_pattern": [
                    r"注{1,3}当期持有基金产生的应支付销售服务费",
                    r"根据相关法律法规及本基金合同的约定",
                ],
            }
        ],
    },
    {"path": ["本报告期持有的基金发生的重大影响事件"], "models": [{"name": "partial_text"}]},
    {"path": ["本报告期持有的基金发生的重大影响事件-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["开放式基金份额变动", "基金名称"], "models": [{"name": "partial_text"}]},
    {"path": ["开放式基金份额变动", "份额变动情况", "报告期期初基金份额总额"], "models": [{"name": "partial_text"}]},
    {"path": ["开放式基金份额变动", "份额变动情况", "报告期期间总申购份额"], "models": [{"name": "partial_text"}]},
    {"path": ["开放式基金份额变动", "份额变动情况", "报告期期间基金总赎回份额"], "models": [{"name": "partial_text"}]},
    {
        "path": ["开放式基金份额变动", "份额变动情况", "报告期期间基金拆分变动份额（份额减少以“-”填列）"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["开放式基金份额变动", "份额变动情况", "报告期期末基金份额总额"], "models": [{"name": "partial_text"}]},
    {
        "path": ["开放式基金份额变动-注释"],
        "models": [{"name": "para_match", "paragraph_pattern": [r"注.{1,3}本基金于本报告期间成立"]}],
    },
    {"path": ["报告期期间其他份额变动情况"], "models": [{"name": "partial_text"}]},
    {"path": ["基金份额变动情况-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末各资产单元的资产净值及占基金资产净值的比例", "资产单元"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期末各资产单元的资产净值及占基金资产净值的比例", "投资顾问名称"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末各资产单元的资产净值及占基金资产净值的比例", "报告期末资产单元资产净值", "数值"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末各资产单元的资产净值及占基金资产净值的比例", "报告期末资产单元资产净值", "单位"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期末各资产单元的资产净值及占基金资产净值的比例", "占期末基金资产净值比例（%）"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["报告期末各资产单元的资产净值及占基金资产净值的比例-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["基金投资顾问1", "序号"], "models": [{"name": "partial_text"}]},
    {"path": ["基金投资顾问1", "投资顾问名称"], "models": [{"name": "partial_text"}]},
    {"path": ["基金投资顾问1", "是否与基金管理人存在关联关系"], "models": [{"name": "partial_text"}]},
    {"path": ["基金投资顾问1", "是否与其他投资顾问存在关联关系"], "models": [{"name": "partial_text"}]},
    {"path": ["基金投资顾问1-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["基金管理人运用固有资金投资本基金交易明细", "序号"], "models": [{"name": "partial_text"}]},
    {"path": ["基金管理人运用固有资金投资本基金交易明细", "交易方式"], "models": [{"name": "partial_text"}]},
    {"path": ["基金管理人运用固有资金投资本基金交易明细", "交易日期"], "models": [{"name": "partial_text"}]},
    {"path": ["基金管理人运用固有资金投资本基金交易明细", "交易份额（份）"], "models": [{"name": "partial_text"}]},
    {"path": ["基金管理人运用固有资金投资本基金交易明细", "交易金额", "数值"], "models": [{"name": "partial_text"}]},
    {"path": ["基金管理人运用固有资金投资本基金交易明细", "交易金额", "单位"], "models": [{"name": "partial_text"}]},
    {"path": ["基金管理人运用固有资金投资本基金交易明细", "适用费率"], "models": [{"name": "partial_text"}]},
    {"path": ["基金管理人运用固有资金投资本基金交易明细-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末发起式基金发起资金持有份额情况", "项目"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末发起式基金发起资金持有份额情况", "持有份额总数"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期末发起式基金发起资金持有份额情况", "持有份额占基金总份额比例"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["报告期末发起式基金发起资金持有份额情况", "发起份额总数"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期末发起式基金发起资金持有份额情况", "发起份额占基金总份额比例"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["报告期末发起式基金发起资金持有份额情况", "发起份额承诺持有期限"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期末发起式基金发起资金持有份额情况-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期期初管理人持有的本基金份额"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期期间买入或申购总份额"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期期间卖出总份额"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期期末管理人持有的本基金份额"], "models": [{"name": "partial_text"}]},
    {"path": ["报告期期末持有的本基金份额占基金总份额比例（%）"], "models": [{"name": "partial_text"}]},
    {"path": ["基金管理人持有本基金份额变动情况-注释"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期内单一投资者持有基金份额比例达到或超过20%的情况", "投资者类别"],
        "models": [{"name": "partial_text"}],
    },
    {"path": ["报告期内单一投资者持有基金份额比例达到或超过20%的情况", "序号"], "models": [{"name": "partial_text"}]},
    {
        "path": ["报告期内单一投资者持有基金份额比例达到或超过20%的情况", "持有基金份额比例达到或者超过20%的时间区间"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期内单一投资者持有基金份额比例达到或超过20%的情况", "期初份额"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期内单一投资者持有基金份额比例达到或超过20%的情况", "申购份额"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期内单一投资者持有基金份额比例达到或超过20%的情况", "赎回份额"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期内单一投资者持有基金份额比例达到或超过20%的情况", "持有份额"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["报告期内单一投资者持有基金份额比例达到或超过20%的情况", "份额占比"],
        "models": [{"name": "partial_text"}],
    },
    {
        "path": ["产品特有风险"],
        "models": [
            {
                "name": "row_match",
                "row_pattern": [r"报告期内，本基金存在单"],
                "content_pattern": [
                    r"(?P<dst>报告期内，本基金存在单一投资者持有份额比例达到.*利益.?)",
                ],
            },
        ],
    },
    {"path": ["报告期内单一投资者持有基金份额比例达到或超过20%的情况-注释"], "models": [{"name": "partial_text"}]},
    {"path": ["影响投资者决策的其他重要信息"], "models": [{"name": "syllabus_elt_v2"}]},
    {
        "path": ["备查文件目录"],
        "models": [{"name": "syllabus_elt_v2"}],
    },
    {
        "path": ["存放地点"],
        "models": [{"name": "syllabus_elt_v2"}],
    },
    {
        "path": ["查阅方式"],
        "models": [{"name": "syllabus_elt_v2", "include_title": True}],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
