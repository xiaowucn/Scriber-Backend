from remarkable.plugins.predict.models.model_base import SPECIAL_ATTR_PATTERNS
from remarkable.plugins.predict.predictor import AIAnswerPredictor

predictors = [
    {
        "path": ["扉页-发行概况"],
        "model": "table_kv",
        "just_table": True,
    },
    {
        "path": ["扉页-重大事项提示"],
        "model": "title_content_group",
        "multi_elements": True,
        "top_title": "重大事项提示",
    },
    {
        "path": ["概览-简要基本情况"],
        "model": "table_kv",
        "just_table": True,
    },
    {
        "path": ["概览-中介机构列表"],
        "model": "table_kv",
        "just_table": True,
    },
    {
        "path": ["概览-发行概况（二）"],
        "model": "table_kv",
        "just_table": True,
    },
    {
        "path": ["概览-主要会计数据及财务指标"],
        "model": "table_tuple",
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
        "just_table": True,
    },
    {
        "path": ["概览-发行人选择的上市标准"],
    },
    {
        "path": ["概览-募集资金用途"],
        "model": "table_row",
    },
    {
        "path": ["本次发行概况-发行概况（三）"],
        "model": "table_kv",
        "just_table": True,
    },
    {
        "path": ["本次发行概况-相关机构-保荐人"],
        "model": "table_kv",
        "multi_elements": True,
    },
    {
        "path": ["本次发行概况-相关机构-主承销商"],
        "model": "table_kv",
        "multi_elements": True,
    },
    {
        "path": ["本次发行概况-相关机构-发行人律师事务所"],
        "model": "table_kv",
        "multi_elements": True,
    },
    {
        "path": ["本次发行概况-相关机构-保荐人律师事务所"],
        "model": "table_kv",
        "multi_elements": True,
    },
    {
        "path": ["本次发行概况-相关机构-审计机构"],
        "model": "table_kv",
        "multi_elements": True,
    },
    {
        "path": ["本次发行概况-相关机构-资产评估机构"],
        "model": "table_kv",
        "multi_elements": True,
    },
    {
        "path": ["本次发行概况-相关机构-资产评估复核机构"],
        "model": "table_kv",
        "multi_elements": True,
    },
    {
        "path": ["本次发行概况-相关机构-验资机构"],
        "model": "table_kv",
        "multi_elements": True,
    },
    {
        "path": ["本次发行概况-其他相关机构"],
        "model": "other_related_agencies",
        "need_syl": True,
        "multi_elements": True,
        "valid": {
            "fullfill": 0.1,
        },
    },
    {
        "path": ["风险因素"],
        "model": "similar_section",
        "multi_elements": True,
        "need_syl": True,
    },
    {
        "path": ["发行人基本情况-基本情况", "（表格）"],
        "model": "table_kv",
        "just_table": True,
    },
    {"path": ["发行人基本情况-基本情况", "注册中文名称"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "注册英文名称"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "注册资本"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "注册资本币种"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "实收资本"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "实收资本币种"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "法定代表人"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "成立日期/有限公司成立日期"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "股份公司成立日期"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "住所"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "邮政编码"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "电话号码"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "传真号码"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "互联网网址"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "电子信箱"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "负责信息披露和投资者关系的部门"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "负责信息披露和投资者关系的负责人"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "负责信息披露和投资者关系的负责人电话号码"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "主要生产经营地址"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "控股股东"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "实际控制人"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "行业分类"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "营业范围"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "在其他交易所（申请）挂牌或上市的情况"], "model": "partial_text"},
    {"path": ["发行人基本情况-基本情况", "统一社会信用代码"], "model": "partial_text"},
    {
        "path": ["发行人基本情况-股本情况"],
        "model": "table_row",
        "just_table": True,
        "necessary": ["股东名称"],
        "pos": (-1, -4),
        "multi_elements": True,
    },
    {
        "path": ["发行人基本情况-重大资产重组情况"],
        "model": "syllabus_elt_v2",
        "order_by": "level",
        "reverse": True,
        "equal_mode": True,
        "need_syl": True,
        "enum": {"default": "是", "regs": [("否", [r"[不没未][^。]*重组"])]},
    },
    # {"path": ["发行人基本情况-发行人股权结构图"],},
    {
        "path": ["发行人基本情况-发行人股权结构图", "发行人股权结构图"],
        "need_syl": True,
        "model": "chart_in_syl",
        "multi_elements": False,
    },
    {
        "path": ["子公司基本情况"],
        "model": "sse_subcompany",
        "need_syl": True,
        "multi_elements": True,
    },
    {
        "path": ["子公司基本情况", "股东构成及控股情况"],
        "model": "score_filter",
    },
    {
        "path": ["子公司基本情况", "子公司最近一年及一期末的资产及利润情况"],
        "model": ["table_tuple", "partial_text", "score_filter"],
        "element_candidate_priors": ["总资产"],
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
        "multi_model": False,
    },
    {
        "path": ["子公司基本情况", "子公司最近一年及一期末的资产及利润情况", "单位"],
        "model": "nearby_elt",
        "pos": (-1, -4),
    },
    {
        "path": ["发行人基本情况-分支机构基本情况"],
        "model": "table_kv",
        "multi_elements": True,
    },
    # {"path": ["发行人基本情况-参股公司基本情况"], "model": "table_kv", "multi_elements": True,},
    {
        "path": ["发行人基本情况-参股公司基本情况"],
        "model": "part_stock_companies",
        "multi_elements": True,
    },
    {
        "path": ["发行人基本情况-控股股东"],
        "model": "table_kv",
        "multi_elements": True,
    },
    {
        "path": ["发行人基本情况-间接控股股东"],
        "model": "table_kv",
        "multi_elements": True,
    },
    {
        "path": ["发行人基本情况-实际控制人"],
        "model": "actual_controller",
        "multi_elements": True,
        "supplement": {
            "实际控制人名称": [
                r"[，。：；](?P<dst>\w{2,4})(先生|小姐|女士)?(直接|间接)持有",
                r"实际控制人为(?P<dst>[^，。；]*)",
            ],
        },
    },
    {
        "path": ["发行人基本情况-实际控制人的一致行动人"],
        "model": "consistent_actioner",
        "multi_elements": True,
        "regs": {
            "一致行动人名称": [
                r"^(?P<dst>\w{2,4)(?=(、|为|签署))",
                r"[、，](?P<dst>\w{2,4})(?=(、|为|签署))",
                r"一致行动人(?P<dst>\w{2,4})(?=(持有))",
                r"(，|。)(?P<dst>\w{2,4})(?=(担任))",
            ],
        },
    },
    {
        "path": ["发行人基本情况-持有5%以上股份的股东"],
        "model": "share_holders",
        "multi_elements": True,
    },
    {
        "path": ["发行人基本情况-员工持股平台", "是否存在员工持股平台"],
        "model": "score_filter",
        "threshold": 0.1,
        "enum": {
            "default": "是",
            "regs": [
                ("否", [r"[不没未]"]),
            ],
        },
    },
    {
        "path": ["发行人基本情况-员工持股平台", "持股平台名称"],
        "model": "partial_text",
    },
    {
        "path": ["发行人基本情况-控股股东、实际控制人股权质押情况"],
        "model": "equity_pledge",
        "multi_elements": True,
        "need_syl": True,
    },
    {
        "path": ["发行人基本情况-前十股东"],
        "model": "table_row",
        "just_table": True,
        "necessary": ["股东名称"],
        "pos": (-1, -4),
    },
    {
        "path": ["发行人基本情况-前十自然人股东及其担任职务"],
        "model": "table_row",
        "just_table": True,
        "necessary": ["股东名称"],
        "pos": (-1, -4),
    },
    {
        "path": ["发行人基本情况-前十自然人股东及其担任职务", "是否存在自然人股东及在发行人处担任职位的情况"],
        "model": "score_filter",
    },
    {
        "path": ["发行人基本情况-股东关系"],
        "model": "shareholder_relation",
        "need_syl": True,
        "necessary": ["股东名称", "关联关系"],
    },
    {
        "path": ["发行人基本情况-董事会成员"],
        "candi_types": ["TABLE"],
        "necessary": ["董事姓名"],
        "model": "table_row",
    },
    {"path": ["发行人基本情况-董事会成员", "简历"], "model": "resume", "_key": "董事姓名"},
    {
        "path": ["发行人基本情况-监事会成员"],
        "candi_types": ["TABLE"],
        "necessary": ["监事姓名"],
        "model": "table_row",
    },
    {"path": ["发行人基本情况-监事会成员", "简历"], "model": "resume", "_key": "监事姓名"},
    {
        "path": ["发行人基本情况-高级管理人员"],
        "candi_types": ["TABLE"],
        "necessary": ["高管姓名"],
        "model": "table_row",
    },
    {"path": ["发行人基本情况-高级管理人员", "简历"], "model": "resume", "_key": "高管姓名"},
    {
        "path": ["发行人基本情况-核心技术人员"],
        "candi_types": ["TABLE"],
        "necessary": ["核心技术人员姓名"],
        "model": "table_row",
    },
    {"path": ["发行人基本情况-核心技术人员", "简历"], "model": "resume", "_key": "核心技术人员姓名"},
    {
        "path": ["发行人基本情况-董监高核薪酬总额"],
        "model": "table_tuple",
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
    },
    {
        "path": ["发行人基本情况-薪酬情况"],  # todo：row_3d
        "model": "table_row",
        "just_table": True,
        "necessary": ["姓名", "薪酬金额"],
        "pos": (-1, -4),
        "multi_elements": True,
    },
    {
        "path": ["发行人基本情况-员工情况-专业构成"],
        "necessary": ["人数", "项目（专业）"],
        "model": "table_row_filter",
        "group_by": {"项目（专业）": [r"专业"]},
        "unit_priority": {
            "<数量单位>": [r"(人数|数量)"],
            "<百分比单位>": [r"(占比|比[例率])"],
        },
    },
    {
        "path": ["发行人基本情况-员工情况-专业构成", "年度"],
        "model": "nearby_elt",
        "type": "date",
        "pos": (-1, -4),
        "same_elt_with_parent": True,
    },
    {
        "path": ["发行人基本情况-员工情况-学历构成"],
        "necessary": ["人数", "项目（学历）"],
        "model": "table_row_filter",
        "group_by": {"项目（学历）": [r"(学历|教育)"]},
        "unit_priority": {
            "<数量单位>": [r"(人数|数量)"],
            "<百分比单位>": [r"(占比|比[例率])"],
        },
    },
    {
        "path": ["发行人基本情况-员工情况-学历构成", "年度"],
        "model": "nearby_elt",
        "type": "date",
        "pos": (-1, -4),
        "same_elt_with_parent": True,
    },
    {
        "path": ["发行人基本情况-员工情况-年龄构成"],
        "necessary": ["期末人数", "年龄类别/年龄"],
        "model": "table_row_filter",
        "group_by": {"年龄类别/年龄": [r"年[龄纪岁]"]},
        "unit_priority": {
            "<数量单位>": [r"(人数|数量)"],
            "<百分比单位>": [r"(占比|比[例率])"],
        },
    },
    {
        "path": ["发行人基本情况-员工情况-年龄构成", "年度"],
        "model": "nearby_elt",
        "type": "date",
        "pos": (-1, -4),
        "same_elt_with_parent": True,
    },
    {
        "path": ["业务与技术-主要产品及业务的收入情况"],
        "model": "table_row_3d",
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
    },
    {
        "path": ["业务与技术-前五客户"],
        "model": "table_row",
        "just_table": True,
        "necessary": ["客户名称"],
        "pos": (-1, -4),
        "multi_elements": True,
        "element_candidate_priors": [">表格<"],
        "exclude_attr": ["销售产品/类型"],
    },
    {
        "path": ["业务与技术-前五客户", "销售产品/类型"],
        "model": "nearby_elt",
        "blocks": [{"pos": (-1, -6), "neg_patterns": [r"^单位"]}, {"pos": (0, 2)}],
        "same_elt_with_parent": True,
        "include_self": False,
    },
    {
        "path": ["业务与技术-前五供应商"],
        "model": "table_row",
        "just_table": True,
        "necessary": ["供应商名称"],
        "pos": (-1, -4),
        "multi_elements": True,
        "element_candidate_priors": [">表格<"],
        "exclude_attr": ["采购产品/类型"],
    },
    {
        "path": ["业务与技术-前五供应商", "采购产品/类型"],
        "model": "nearby_elt",
        "blocks": [{"pos": (-1, -6), "neg_patterns": [r"^单位"]}, {"pos": (0, 2)}],
        "same_elt_with_parent": True,
        "include_self": False,
    },
    {
        "path": ["业务与技术-专利"],
        "model": "table_row",
        "just_table": True,
        "necessary": ["专利名称"],
        "multi_elements": True,
    },
    {
        "path": ["业务与技术-专利", "专利授权国家"],
        "model": "nearby_elt",
        "pos": (-1, -4),
    },
    {
        "path": ["业务与技术-软件著作权"],
        "model": "table_row",
        "just_table": True,
        "necessary": ["软件名称"],
        "multi_elements": True,
    },
    {
        # 注：多在段落中描述，或许用四元组/关系模型能找出来
        "path": ["业务与技术-核心技术产品占营业收入比例"],
        "model": "table_tuple",
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
    },
    {
        # 注: 多在段落中描述
        "path": ["业务与技术-专业资质情况"],
        "model": "professional_qualifications",
        "just_table": True,
        "multi_elements": True,
        "necessary": ["资质名称"],
    },
    {
        # 注: 多在段落中描述
        "path": ["业务与技术-主要核心技术"],
        "model": "table_row",
        "just_table": True,
        "necessary": ["技术名称"],
        "multi_elements": True,
        "neglect_patterns": {
            "技术类型": [
                r"序号|产品|名称|环节",
                r"(核心)?技术(名称|来源)",
            ]
        },
    },
    {
        "path": ["业务与技术-获奖情况"],
        "model": "table_row",
        "just_table": True,
        "necessary": ["奖项名称"],
        "multi_elements": True,
    },
    {
        "path": ["业务与技术-获奖情况", "获奖人"],
        "model": "nearby_elt",
        "regs": [r"(?P<dst>本?公司|发行人)"],
        "pos": (-1, -4),
    },  # 倒数三个elt
    {
        "path": ["业务与技术-科研成果"],
        "model": "table_row",
        "just_table": True,
        "necessary": ["项目名称"],
    },
    {
        "path": ["业务与技术-在研项目"],
        "model": "table_row",
        "just_table": True,
        "multi_elements": True,
        "necessary": ["项目名称/编码"],
    },
    {
        "path": ["业务与技术-研发费用与营业收入比例"],
        "model": "table_tuple",
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
        "column_header_index": 0,
    },
    {
        "path": ["业务与技术-研发人员数量"],
        "model": "partial_text",
        "regs": {
            "年度": SPECIAL_ATTR_PATTERNS["date"],
            "研发人员数量": [r"\d+[人|名|个]"],
        },
        "valid": {
            "fullfill": 0.1,
        },
    },
    {
        "path": ["公司治理与独立性-发行人特别表决权股份情况"],
        "model": "syllabus_elt_v2",
        "order_by": "level",
        "reverse": True,
        "equal_mode": True,
        "need_syl": True,
        "enum": {
            "default": "是",
            "regs": [
                ("否", [r"[不没未][^。]*特别表决"]),
            ],
        },
    },
    {
        "path": ["公司治理与独立性-发行人协议控制架构情况"],
        "model": "syllabus_elt_v2",
        "order_by": "level",
        "reverse": True,
        "equal_mode": True,
        "need_syl": True,
        "enum": {
            "default": "是",
            "regs": [
                ("否", [r"[不没未][^。]*控制架构"]),
            ],
        },
    },
    {
        "path": ["公司治理与独立性-同业竞争"],
        "model": "title_content_group",
        "top_title": "同业竞争",
        "need_syl": True,
    },
    {
        "path": ["公司治理与独立性-关联方及关联关系"],
        "model": "correlation",
        "need_syl": True,
        "necessary": ["关联方名称", "关联关系", "关联类型"],
    },
    {
        "path": ["公司治理与独立性-关联交易"],
        "model": "title_content_group",
        "multi_elements": True,
        "top_title": "关联交易",
        "need_syl": True,
    },
    {
        "path": ["公司治理与独立性-发行人违法违规情况"],
        "model": "syllabus_elt_v2",
        "order_by": "level",
        "reverse": True,
        "equal_mode": True,
        "need_syl": True,
        "enum": {
            "default": "否",
            "regs": [
                ("是", [r"[不没未][^。]*构成", r"上述(处罚|违[法规]|行为)"]),
            ],
        },
    },
    {
        "path": ["财务会计信息-审计意见"],
        "model": "para_match",
        "paragraph_pattern": [r"会计.*意见"],
        "enum": {
            "default": None,
            "regs": [
                ("标准的无保留意见", [r"标准的?无保留意见"]),
                ("带强调事项段的无保留意见", [r"带强调事项段的?无保留意见"]),
                ("保留意见", [r"保留意见"]),
                ("否定意见", [r"否定意见"]),
                ("无法表示意见", [r"无法表示意见"]),
            ],
        },
    },
    {
        "path": ["IPO资产负债表（合并）"],
        "model": "table_kv",
        "just_table": True,
    },  # TODO: 三大报表_（表格） 待改成缺省模型
    {
        "path": ["IPO利润表（合并）"],
        "model": "table_kv",
        "just_table": True,
    },
    {
        "path": ["IPO现金流量表（合并）"],
        "model": "table_kv",
        "just_table": True,
    },
    {
        "path": ["IPO资产负债表（母公司）"],
        "model": "table_kv",
        "just_table": True,
    },
    {
        "path": ["IPO利润表（母公司）"],
        "model": "table_kv",
        "just_table": True,
    },
    {
        "path": ["IPO现金流量表（母公司）"],
        "model": "table_kv",
        "just_table": True,
    },
    {
        "path": ["财务会计信息-重要会计政策和会计评估"],
        "model": "title_content_group",
        "multi_elements": True,
        "need_syl": True,
        "top_title": "重要会计政策和会计评估",
    },
    {
        "path": ["财务会计信息-非经常性损益"],
        "model": "table_tuple",
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
    },
    {
        "path": ["财务会计信息-非经常性损益", "非经常性损益净额占归属于母公司所有者净利润的比例"],
        "model": "nearby_elt",
        "pos": (1, 4),
    },
    {
        "path": ["财务会计信息-主要财务指标"],
        "model": "table_row_3d",
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
        "just_table": True,
        "unit_priority": {
            "<金额单位>": [
                "息税折旧摊销前利润",
                "归属于发行人股东的净利润",
                "归属于发行人股东扣除非经常性损益后的净利润",
            ],
        },
    },
    {
        "path": ["财务会计信息-净资产收益率和每股收益"],
        "model": "table_row",
    },
    {
        "path": ["财务会计信息-营业收入的构成情况（区分主营与非主营）"],
        "model": "table_row_3d",
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
    },
    {
        "path": ["财务会计信息-营业收入分产品分析"],
        "model": "table_row_3d",
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
        "element_candidate_priors": ["收入金额"],
        "location_threshold": {"table": 0.5},
        "multi_elements": True,
    },
    {
        "path": ["财务会计信息-营业收入分销售模式分析"],
        "model": "table_row_3d",
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
        "element_candidate_priors": ["收入金额"],
        "location_threshold": {"table": 0.5},
        "multi_elements": True,
    },
    {
        "path": ["财务会计信息-营业收入分区域分析"],
        "model": "table_row_3d",
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
        "element_candidate_priors": ["收入金额"],
        "location_threshold": {"table": 0.5},
        "multi_elements": True,
    },
    {
        "path": ["财务会计信息-营业收入季节性分析"],
        "model": "table_row_3d",
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
        "element_candidate_priors": ["收入金额"],
    },
    {
        "path": ["财务会计信息-营业成本构成情况"],
        "model": "table_row_3d",
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
        "element_candidate_priors": ["成本金额"],
    },
    {
        "path": ["财务会计信息-营业成本分产品分析"],
        "model": "table_row_3d",
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
        "element_candidate_priors": ["成本金额"],
        "location_threshold": {"table": 0.5},
        "multi_elements": True,
    },
    {
        "path": ["财务会计信息-毛利率及收入占比"],
        "model": ["table_row_3d", "partial_text"],
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
        "element_candidate_priors": ["项目名称(产品/类型)"],
        "header_regs": {
            "收入占比": [r"占.*?比"],
            "项目毛利率（%）": [r"毛利率"],
        },
        # "multi_elements": True,
    },
    {
        "path": ["财务会计信息-研发费用细分情况"],
        "model": "table_row_3d",
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
        "just_table": True,
    },
    {
        "path": ["财务会计信息-研发费用率与同行业公司对比"],
        "model": "table_row_3d",
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
    },
    {
        "path": ["财务会计信息-股份支付概况"],
        "model": "table_row_3d",
        "header_regs": {
            "股份支付金额原文": [r"股份支付"],
        },
        "3rd_dimension": {
            "type": "date",
            "column": "年度",
        },
        "multi_elements": True,
    },
    {
        "path": ["财务会计信息-股份支付概况", "股份支付金额原文单位"],
        "model": "nearby_elt",
        "regs": [r"(?P<dst>万?元)"],
        "multi_elements": True,
        "pos": (0, -2),
    },
    {
        "path": ["募集资金运用与未来发展规划-募集资金用途"],
        "model": "table_row",
    },
    {
        "path": ["募集资金运用与未来发展规划-募集资金用途", "建设期"],
        "model": "nearby_elt",
        "regs": [r"建设期?(?P<dst>[\d一二三四五六七八九零个十百]+[日天周月年])"],
        "pos": (-1, -4),
    },
    {
        "path": ["其他重要事项-对外担保情况", "发行人是否存在对外担保"],
        "model": "syllabus_elt_v2",
        "order_by": "level",
        "reverse": True,
        "equal_mode": True,
        "need_syl": True,
        "enum": {"default": "是", "regs": [("否", [r"[不没未][^。]*担保"])]},
    },
    {
        "path": ["其他重要事项-重大诉讼", "是否存在重大诉讼"],
        "model": "syllabus_elt_v2",
        "order_by": "level",
        "reverse": True,
        "equal_mode": True,
        "need_syl": True,
        "enum": {"default": "是", "regs": [("否", [r"[不没未][^。]*诉讼"])]},
    },
    {
        "path": ["其他重要事项-涉及违法情况", "是否存在涉及违法"],
        "model": "syllabus_elt_v2",
        "order_by": "level",
        "reverse": True,
        "equal_mode": True,
        "need_syl": True,
        "enum": {"default": "是", "regs": [("否", [r"[不没未][^。]*违法"])]},
    },
    {
        "path": ["其他重要事项-董监高核涉及立案情况"],
        "model": "para_match",
        "paragraph_pattern": ["董.*监.*高.*核.*(立案|诉讼)"],
        "enum": {"default": "是", "regs": [("否", [r"[不没未][^。] *(立案|诉讼)"])]},
    },
    {"path": ["概览-发行人选择的上市标准", "发行人选择的上市标准(原文)"]},
    {
        "path": ["概览-发行人选择的上市标准", "发行人选择的上市标准-条款编号"],
        "model": "partial_text",
    },
    {
        "path": ["概览-发行人选择的上市标准", "发行人选择的上市标准-内容"],
        "model": "partial_text",
    },
    {
        "path": ["业务与技术-发行人参与制定的标准"],
        "model": "table_row",
        "just_table": True,
        "multi_elements": True,
    },
    {
        "path": ["业务与技术-科研项目"],
        "model": "table_row",
        "just_table": True,
        "multi_elements": True,
        "necessary": ["项目名称"],
    },
]


class SSEAnnoPredictor(AIAnswerPredictor):
    """上交所 科创板招股说明书信息抽取"""

    def __init__(self, *args, **kwargs):
        kwargs["predictors"] = predictors
        super(SSEAnnoPredictor, self).__init__(*args, **kwargs)
