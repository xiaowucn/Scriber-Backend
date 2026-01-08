"""
2: 深交所信息抽取-创业板-注册制-财务基础数据
"""

predictor_options = [
    {
        "path": [
            "合并资产负债表",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_ai",
                "post_process": {
                    "报告期": "find_date_from_header",
                },
            },
        ],
        # 'location_threshold': 0.08,
    },
    {
        "path": [
            "合并利润表",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_ai",
                "post_process": {
                    "报告期": "find_date_from_header",
                },
            },
        ],
        # 'location_threshold': 0.08,
    },
    {
        "path": [
            "合并现金流量表",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_ai",
                "post_process": {
                    "报告期": "find_date_from_header",
                },
            },
        ],
        # 'location_threshold': 0.04,
    },
    {
        "path": [
            "非经常性损益表",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_ai",
                "post_process": {
                    "报告期": "find_date_from_header",
                },
            },
        ],
        # 'location_threshold': 0.1,
    },
    {
        "path": [
            "八-主要财务指标表",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_ai",
                "post_process": {
                    "报告期": "find_date_from_header",
                },
            },
        ],
        # 'location_threshold': 0.3,
    },
    {
        "path": [
            "八-净资产收益率表",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_ai",
                "post_process": {
                    "报告期": "find_date_from_header",
                },
            },
        ],
        # 'location_threshold': 0.04,
    },
    {
        "path": [
            "二-主要财务指标表",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_ai",
                "post_process": {
                    "报告期": "find_date_from_header",
                },
            },
        ],
        # 'location_threshold': 0.3,
    },
    {
        "path": [
            "期间费用表",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_ai",
                "post_process": {
                    "报告期": "find_date_from_header",
                },
                "multi_elements": True,
            },
        ],
        # 'location_threshold': 0.3,
    },
    {
        "path": [
            "风险因素",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "complex_gross_margin",
                "multi": True,
            },
        ],
        "location_threshold": 0.3,
    },
    {
        "path": [
            "经营成果表",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_ai",
                "post_process": {
                    "报告期": "find_date_from_header",
                },
            },
        ],
        # 'location_threshold': 0.03,
    },
    {
        "path": [
            "盈利能力表",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_ai",
                "post_process": {
                    "报告期": "find_date_from_header",
                },
            },
        ],
    },
    {
        "path": [
            "毛利表",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_ai",
                "post_process": {
                    "报告期": "find_date_from_header",
                },
            },
        ],
        # 'location_threshold': 0.1,
    },
    {
        "path": [
            "综合毛利率（其他）",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_ai",
                "post_process": {
                    "报告期": "find_date_from_header",
                },
            },
            # {
            #     'name': 'complex_gross_margin',
            #     'dimensions': [
            #         {
            #             "column": "报告期",
            #             "pattern": [report_year_pattern],
            #         }
            #     ],
            # },
        ],
        # 'location_threshold': 0.1,
    },
    {
        "path": [
            "偿债能力表",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_ai",
                "post_process": {
                    "报告期": "find_date_from_header",
                },
            },
        ],
        # 'location_threshold': 0.08,
    },
    {
        "path": [
            "员工人数表",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_ai",
                "post_process": {
                    "报告期": "find_date_from_header",
                },
                "multi_elements": True,
            },
        ],
        # 'location_threshold': 0.051,
    },
    {
        "path": [
            "员工薪酬表",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_ai",
                "post_process": {
                    "报告期": "find_date_from_header",
                },
            },
        ],
        # 'location_threshold': 0.036,
    },
    {
        "path": [
            "其他指标（临时）",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_ai",
                "post_process": {
                    "报告期": "find_date_from_header",
                },
            },
        ],
        # 'location_threshold': 0.1,
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
                "name": "table_ai",
                # 'name': 'interpretation',
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
                "name": "table_ai",
                "multi": False,
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
                "name": "table_kv",
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
                "name": "syllabus_based",
                "multi_elements": True,
                "table_model": "table_kv",
                "para_config": {
                    "申报企业（全称）": {"use_answer_pattern": False},
                },
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
                ],
                "neglect_title_patterns": [r"前十名"],
            },
        ],
    },
    {
        "path": [
            "五-发行人股本情况-总股本",
        ],
        "models": [
            {
                "name": "table_ai",
                "multi": False,
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
        ],
        "models": [
            {
                "name": "table_ai",
                "multi": True,
                "multi_elements": True,
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
            "六-行业基本情况（证监会）",
        ],
        "models": [
            {
                "name": "partial_text",
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
                "name": "table_ai",
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
