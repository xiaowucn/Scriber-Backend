"""
交易商协会募集说明书
"""

from remarkable.predictor.common_pattern import R_CN, R_CONJUNCTION
from remarkable.predictor.eltype import ElementClass, ElementType
from remarkable.predictor.glazer_predictor.schemas.citic_sse_bond_prospectus_schema import (
    ASSET_PATTERNS,
    DEBT_PATTERNS,
    R_CONTROLLER,
    R_ISSUER,
    R_LESS_THAN,
    R_MORE_THAN,
    R_SCOPE_OF_CONSOLIDATION,
    SUB_TOTAL_ASSET_PATTERNS,
    SUB_TOTAL_DEBT_PATTERNS,
)

predictor_options = [
    {
        "path": ["发行人设立情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "skip_types": [ElementClass.FOOTNOTE.value],
            },
        ],
    },
    {
        "path": ["发行人历史沿革"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__公司历史沿革__regex__变更情况",
                ],
            },
        ],
    },
    {
        "path": ["发行人设立情况及历史沿革"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["已或拟发生重大资产重组"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["发行人控股股东"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": [
                    r"控股股东(基本)?(情况)?$",
                ],
            },
            {
                "name": "partial_text",
                "syllabus_regs": [r"控股股东[及和]实际控制人(基本)?(情况)?$", r"股权结构"],
                "regs": [
                    rf"控股股东[{R_CONJUNCTION}]实际控制人(均|仍)?为(?P<dst>.*?{R_CONTROLLER})",
                    rf"(?P<dst>[{R_CN}]+?{R_CONTROLLER})系发行人的?控股股东",
                    r"(发行人|公司)的?(全资)?控股股东为(?P<dst>光大环境)",
                ],
                "model_alternative": True,
            },
            {
                "name": "table_kv",
                "syllabus_regs": [
                    r"控股股东(基本)?(情况)?$",
                ],
                "feature_white_list": [r"公司名称"],
            },
        ],
    },
    {
        "path": ["实际控制人"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": [
                    r"实际控制人(基本)?(情况)?$",
                ],
                "model_alternative": True,
                "regs": [
                    rf"实际控制人(均|仍)?为(?P<dst>.*?{R_CONTROLLER})",
                ],
            },
            {
                "name": "partial_text",
                "syllabus_regs": [
                    r"控股股东及实际控制人情况$",
                    r"股权结构",
                ],
                "regs": [
                    rf"{R_ISSUER}的?(全资)?控股股东[{R_CONJUNCTION}]实际控制人均?为(?P<dst>.*?{R_CONTROLLER})",
                    rf"(?P<dst>[{R_CN}]+?{R_CONTROLLER})持有.*的股权.是{R_ISSUER}的实际控制人",
                ],
            },
        ],
    },
    {
        "path": ["发行人股权结构图"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "valid_types": [ElementClass.IMAGE.value, ElementClass.SHAPE.value],
                "inject_syllabus_features": [rf"__regex__({R_ISSUER})?的?股权结构"],
            },
            {
                "name": "syllabus_elt_v2",
                "valid_types": [ElementClass.IMAGE.value, ElementClass.SHAPE.value],
                "inject_syllabus_features": [r"__regex__发行人控股股东及实际控制人"],
            },
        ],
    },
    {
        "path": ["发行人控股股东情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [rf"__regex__{R_ISSUER}控股股东情况"],
                "syllabus_black_list": [
                    r"股权结构",
                    r"[及和]",
                    r"质押情况",
                ],
            },
        ],
    },
    {
        "path": ["发行人实际控制人情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    rf"__regex__{R_ISSUER}实际控制人的?情况",
                ],
                "syllabus_black_list": [
                    r"股权结构",
                    r"[及和]",
                    r"质押情况",
                ],
            },
        ],
    },
    {
        "path": ["控股股东及实际控制人情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__(控股|发行人)股东[及和]实际控制人",
                ],
            },
        ],
    },
    {
        "path": ["发行人的重要权益投资情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__公司控股子公司、参股公司情况",
                ],
            },
        ],
    },
    {
        "path": ["发行人持股比例大于50%但未纳入合并范围的持股公司"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    rf"__regex__报告期内发行人持股比例{R_MORE_THAN}50[%％]但[不未]纳入{R_SCOPE_OF_CONSOLIDATION}",
                    rf"__regex__发行人持股比例{R_MORE_THAN}50[%％]但[不未]纳入{R_SCOPE_OF_CONSOLIDATION}的",
                    rf"__regex__持股比例{R_MORE_THAN}50[%％]但[不未]纳入{R_SCOPE_OF_CONSOLIDATION}",
                ],
                "only_inject_features": True,
            },
            {
                "name": "syllabus_based",
                "extract_from": "same_type_elements",
                "include_title": False,
                "inject_syllabus_features": [
                    r"__regex__(主要|发行人)(控股)?子公司的?情况",
                ],
                "only_inject_features": True,
                "para_config": {
                    "regs": [r"^$"],
                },
                "table_model": "table_titles",
                "table_config": {
                    "feature_white_list": [
                        rf"报告期内发行人持股比例{R_MORE_THAN}50[%％]但[不未]纳入{R_SCOPE_OF_CONSOLIDATION}",
                        rf"发行人持股比例{R_MORE_THAN}50[%％]但[不未]纳入{R_SCOPE_OF_CONSOLIDATION}的",
                        rf"发行人存在.*家持股比例{R_MORE_THAN}50[%％]但[不未]纳入{R_SCOPE_OF_CONSOLIDATION}的",
                    ],
                },
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"__regex__主要子公司情况"],
                "include_bottom_anchor": True,
                "bottom_continue_greed": True,
                "bottom_greed": True,
                "top_anchor_regs": [
                    rf"存在.*发行人持股比例{R_MORE_THAN}50[%％]但[不未]纳入{R_SCOPE_OF_CONSOLIDATION}的.*公司",
                ],
                "bottom_anchor_regs": [
                    rf"(因此|故).?未将.*纳入{R_SCOPE_OF_CONSOLIDATION}",
                    r"\d.*公司$",
                ],
            },
            {
                "name": "para_match",
                "multi_elements": True,
                "paragraph_pattern": [
                    rf"存在.*发行人持股比例{R_MORE_THAN}50[%％]但[不未]纳入{R_SCOPE_OF_CONSOLIDATION}的.*公司",
                    rf"发行人持股比例{R_MORE_THAN}50[%％]但[不未]纳入{R_SCOPE_OF_CONSOLIDATION}的.*公司",
                    rf"发行人存在.*家持股比例{R_MORE_THAN}50[%％]但[不未]纳入{R_SCOPE_OF_CONSOLIDATION}的持股公司",
                    rf"发行人持有.*公司[56789][\d.]+[%％]股权，但[不未]将.*公司纳入{R_SCOPE_OF_CONSOLIDATION}",
                    rf"发行人对.*公司.*持股[56789][\d.]+[%％]，但[不未]纳入{R_SCOPE_OF_CONSOLIDATION}",
                    rf"公司.发行人持股比例[56789][\d.]+[%％].*[不未]纳入{R_SCOPE_OF_CONSOLIDATION}",
                ],
            },
        ],
    },
    {
        "path": ["发行人持股比例小于50%但纳入合并范围的持股公司"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    rf"__regex__报告期内发行人持股比例{R_LESS_THAN}(等于)?50[%％]但纳入{R_SCOPE_OF_CONSOLIDATION}的情况",
                    rf"__regex__发行人持股比例{R_LESS_THAN}(等于)?50[%％]但纳入{R_SCOPE_OF_CONSOLIDATION}的子公司",
                    rf"__regex__持股比例{R_LESS_THAN}(等于)?50[%％]但纳入{R_SCOPE_OF_CONSOLIDATION}",
                ],
                "only_inject_features": True,
            },
            {
                "name": "syllabus_based",
                "extract_from": "same_type_elements",
                "include_title": False,
                "inject_syllabus_features": [
                    r"主要子公司情况",
                ],
                "only_inject_features": True,
                "para_config": {
                    "regs": [r"^$"],
                },
                "table_model": "table_titles",
                "table_config": {
                    "feature_white_list": [
                        rf"报告期内发行人持股比例{R_LESS_THAN}50[%％]但纳入{R_SCOPE_OF_CONSOLIDATION}",
                        rf"发行人持股比例{R_LESS_THAN}50[%％]但纳入{R_SCOPE_OF_CONSOLIDATION}的",
                        rf"发行人存在.*家持股比例{R_LESS_THAN}50[%％]但纳入{R_SCOPE_OF_CONSOLIDATION}的",
                    ],
                },
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [
                    r"__regex__发行人主要子公司情况",
                    r"__regex__发行人主要子公司以及其他有重要影响的参股公司情况",
                ],
                "include_bottom_anchor": True,
                "bottom_continue_greed": True,
                "bottom_greed": True,
                "top_anchor_regs": [
                    rf"发行人存在.*家持股比例{R_LESS_THAN}或等于50%但纳入{R_SCOPE_OF_CONSOLIDATION}的子公司",
                    rf"存在.*发行人持股比例{R_LESS_THAN}50[%％]但纳入{R_SCOPE_OF_CONSOLIDATION}的子公司",
                    rf"发行人.*持(股比例|有|股)为?[1-4][\d.]+[%％].*纳入{R_SCOPE_OF_CONSOLIDATION}",
                    rf"发行人.*(享有.*控股权|能够.*形成实际控制).*纳入{R_SCOPE_OF_CONSOLIDATION}",
                    r"发行人.*控制权对其控制，故按照会计准则相关条款进行并表",
                ],
                "bottom_anchor_regs": [
                    rf"发行人持有.*公司([(（].*[)）])?[1234][\d.]+[%％]的?股权.*纳入{R_SCOPE_OF_CONSOLIDATION}",
                    rf"发行人.*持(股比例|有|股)为?[1-4][\d.]+[%％].*纳入{R_SCOPE_OF_CONSOLIDATION}",
                    rf"发行人.*(享有.*控股权|能够.*形成实际控制).*纳入{R_SCOPE_OF_CONSOLIDATION}",
                    rf"发行人.*控制权对其控制.*纳入{R_SCOPE_OF_CONSOLIDATION}",
                ],
            },
            {
                "name": "syllabus_based",
                "extract_from": "same_type_elements",
                "include_title": False,
                "inject_syllabus_features": [
                    r"__regex__(主要|发行人)(控股)?子公司的?情况",
                    r"__regex__发行人重要权益投资情况",
                ],
                "only_inject_features": True,
                "para_config": {
                    "regs": [r"^$"],
                },
                "table_model": "table_titles",
                "table_config": {
                    "feature_white_list": [
                        rf"报告期内发行人持股比例{R_LESS_THAN}50[%％]但纳入{R_SCOPE_OF_CONSOLIDATION}",
                        rf"发行人持股比例{R_LESS_THAN}50[%％]但纳入{R_SCOPE_OF_CONSOLIDATION}的",
                        rf"发行人存在.*家持股比例{R_LESS_THAN}50[%％]但纳入{R_SCOPE_OF_CONSOLIDATION}的",
                    ],
                },
            },
            {
                "name": "para_match",
                "paragraph_pattern": [
                    rf"发行人.*持股比例{R_LESS_THAN}50[%％]但纳入{R_SCOPE_OF_CONSOLIDATION}",
                    rf"发行人.*持股比例为?[1-4][\d.]+[%％].*纳入{R_SCOPE_OF_CONSOLIDATION}",
                    rf"发行人.*均具有决定权.*纳入{R_SCOPE_OF_CONSOLIDATION}",
                    rf"发行人.*持有.*股权.*发行人对.*实际控制.*纳入{R_SCOPE_OF_CONSOLIDATION}",
                    rf"为享有该公司最大表决权的股东.*纳入{R_SCOPE_OF_CONSOLIDATION}",
                    rf"从而对.*进行控制.*纳入{R_SCOPE_OF_CONSOLIDATION}",
                ],
            },
        ],
    },
    {
        "path": ["投资控股型发行人相关情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["发行人的治理结构等情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__公司治理情况",
                ],
            },
        ],
    },
    {
        "path": ["发行人董事、监事、高级管理人员基本情况表"],
        "models": [
            {
                "name": "syllabus_based",
                "extract_from": "same_type_elements",
                "include_title": False,
                "inject_syllabus_features": [
                    r"__regex__(发行人|企业)人力资源情况",
                    r"__regex__(发行人|企业)(人员|员工)基本情况",
                    r"__regex__(发行人|企业)董事、监事及(高级管理|高管)人员"
                    r"__regex__(发行人|企业)董事会、监事会及(高级管理|高管)人员组成情况",
                    r"__regex__高级管理人员简历及公司整体人员情况",
                ],
                "only_inject_features": True,
                "para_config": {
                    "regs": [r"^$"],
                },
                "table_model": "table_titles",
                "table_config": {
                    "feature_white_list": [
                        r"(发行人|公司)董事会成员(情况|名单)?",
                        r"(发行人|公司)(高级管理|高管)(人员|员工)(情况|名单)?",
                        r"(发行人|公司)总经理办公会成员(情况|名单)?",
                        rf"(发行人|公司)董事、监事[{R_CONJUNCTION}](高级管理|高管)人员((基本|主要)情况|名单)",
                    ],
                },
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    rf"__regex__董事(、监事)?[{R_CONJUNCTION}](其他)?(高级管理|高管)人员((基本|主要|组成)情况|名单)",
                ],
                "valid_types": [ElementClass.TABLE.value],
            },
        ],
    },
    {
        "path": ["董事、监事、高级管理人员简介"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__董事、高级管理人员主要从业经历",
                    r"__regex__发行人董事及高级管理人员",
                ],
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"__regex__发行人员工基本情况"],
                "include_top_anchor": False,
                "top_anchor_regs": [
                    r"发行人董事、监事及高级?管理?人员简历",
                ],
                "bottom_anchor_regs": [r"兼职情况"],
            },
        ],
    },
    {
        "path": ["董事、监事、高级管理人员设置符合《公司法》等相关法律法规及公司章程的说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__关于公司高管人员设置是否符合《公司法》等相关法律法规及《公司章程》要求的说明",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"(发行人|公司|人员的设置).*符合.*《?公司(章程|法)》?.*(相关)?(规定|要求|法规)",
                    r"根据《公司章程》.*发行人目前在任监事不存在《公司法》等相关法律法规规定的不得担任监事的情形",
                    r"发行人.*管理人员的设置.*的规定.不存在重大违纪违法情况",
                    r"发行人.*不存在.*法律法规所规定的不得担任.*的情形.*不存在重大违法违纪行为",
                    r"发行人.*有关规定选举和任命产生.*不存在.*超越公司董事会职权做出人事任免决定的情况",
                    r"公司董事、监事、高级管理人员的任职符合《公司法》的规定",
                    r"发行人.*高级管理人员的设置《公司法》等相关法律法规的规定，不存在重大违纪违法情况",
                    r"发行人.*高级管理人员报告期内不存在违法违规情况，任职资格符合《公司法》及《公司章程》的规定。",
                ],
                "neglect_regs": [
                    r"公司具有健全的组织机构及议事规则",
                ],
            },
        ],
    },
    {
        "path": ["所在行业状况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__公司所处行业现状及发展前景",
                    r"__regex__钢铁行业状况",
                ],
            },
        ],
    },
    {
        "path": ["公司所处行业地位"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__公司在行业中的地位",
                ],
            },
        ],
    },
    {
        "path": ["公司面临的主要竞争状况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__公司行业地位和竞争优势__regex__竞争优势",
                    r"__regex__行业竞争格局",
                ],
            },
        ],
    },
    {
        "path": ["公司经营方针和战略"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__公司的发展战略",
                ],
            },
        ],
    },
    {
        "path": ["发行人所在行业状况、行业地位、竞争状况、经营方针及战略"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["发行人主营业务情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__公司主营业务情况",
                    r"__regex__主要业务经营情况",
                ],
            },
        ],
    },
    {
        "path": ["其他经营重要事项", "标题"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["其他经营重要事项", "正文"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["会计报表编制基础、审计情况"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [
                    r"__regex__财务报表信息",
                ],
                "ignore_pattern": [
                    r"近三年财务报告审计情况",
                ],
                "include_top_anchor": False,
                "top_anchor_regs": [
                    r"会计报表编制基础$",
                ],
                "include_bottom_anchor": True,
                "bottom_anchor_regs": [
                    r"审计并出具了标准无保留意见的审计报告",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__财务报表编制及审计情况",
                ],
            },
        ],
    },
    {
        "path": ["会计政策、会计估计变更"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__会计政策变更、会计估计变更、会计差错更正",
                ],
                "break_para_pattern": [
                    r"合并报表范围变化",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__会计政策变更事项的说明",
                    r"__regex__报告期内主要会计政策变更情况",
                ],
            },
        ],
    },
    {
        "path": ["合并范围变化情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__合并报表变化范围",
                ],
            },
        ],
    },
    {
        "path": ["会计师事务所变更"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["审计报告为带强调事项段无保留意见或保留意见的"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["公司报告期内合并及母公司财务报表"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "multi": True,
                "inject_syllabus_features": [
                    r"__regex__发行人合并财务报表",
                    r"__regex__发行人母公司财务报表",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r"(资产|复制)结构分析"],
                "inject_syllabus_features": [
                    r"__regex__发行人合并财务报表",
                    r"__regex__发行人近三年及一期财务报表",
                ],
            },
        ],
    },
    {
        "path": ["报告期内主要财务指标"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__主要财务指标分析",
                ],
            },
        ],
    },
    {
        "path": ["资产结构分析"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__资产结构及主要资产科目分析",
                    rf"__regex__(?<![{R_CN}])资产(结构|情况|构成)([{R_CONJUNCTION}]变动|情况)?(分析)?$",
                ],
            },
        ],
    },
    {
        "path": ["资产结构分析-子科目分析"],
        "sub_primary_key": ["科目名称", "分析内容"],
        "strict_group": True,
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "only_use_syllabus_elements": True,
                    "table_regarded_as_paragraph": True,
                    "inject_syllabus_features": [
                        rf"__regex__(?<![{R_CN}])资产分析$",
                        rf"__regex__(?<![{R_CN}])资产(结构|情况|构成)([{R_CONJUNCTION}]变动|情况)?(分析)?$",
                        rf"__regex__(发行人)资产(结构|情况|构成)([{R_CONJUNCTION}]变动|情况)?(分析)?$",
                        r"资产结构及主要资产科目分析",
                    ],
                    "only_inject_features": True,
                    "ignore_syllabus_children": True,
                    "ignore_syllabus_range": True,
                    "include_bottom_anchor": True,
                    "top_default": True,
                    "bottom_default": True,
                },
                "general_model": "sub_account",
                "general_config": {
                    "sub_patterns": ASSET_PATTERNS,
                    "sub_total_patterns": SUB_TOTAL_ASSET_PATTERNS,
                },
            },
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "only_use_syllabus_elements": True,
                    "table_regarded_as_paragraph": True,
                    "inject_syllabus_features": [
                        rf"__regex__(?<![{R_CN}])资产负债(结构|情况|构成)(与变动|情况)?分析$",
                    ],
                    "only_inject_features": True,
                    "ignore_syllabus_children": True,
                    "ignore_syllabus_range": True,
                    "include_bottom_anchor": True,
                    "top_default": True,
                    "bottom_anchor_regs": [r"流动负债(科目|结构|情况|构成)分析"],
                },
                "general_model": "sub_account",
                "general_config": {
                    "sub_patterns": ASSET_PATTERNS,
                    "sub_total_patterns": SUB_TOTAL_ASSET_PATTERNS,
                },
            },
        ],
    },
    {
        "path": ["负债结构分析"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__负债结构及主要负债科目分析",
                    rf"__regex__(?<![{R_CN}])负债(结构|情况|构成)([{R_CONJUNCTION}]变动)?(分析)?$",
                ],
            },
        ],
    },
    {
        "path": ["负债结构分析-子科目分析"],
        "sub_primary_key": ["科目名称", "分析内容"],
        "strict_group": True,
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "only_use_syllabus_elements": True,
                    "table_regarded_as_paragraph": True,
                    "inject_syllabus_features": [
                        rf"__regex__(?<![{R_CN}])负债分析$",
                        rf"__regex__(?<![{R_CN}])负债(结构|情况|构成)([{R_CONJUNCTION}]变动)?(分析)?$",
                        rf"__regex__(发行人)负债(结构|情况|构成)([{R_CONJUNCTION}]变动)?(分析)?$",
                        r"负债结构及主要负债科目分析",
                    ],
                    "syllabus_black_list": [
                        r"优化",
                    ],
                    "only_inject_features": True,
                    "ignore_syllabus_children": True,
                    "ignore_syllabus_range": True,
                    "include_bottom_anchor": True,
                    "top_default": True,
                    "bottom_default": True,
                },
                "general_model": "sub_account",
                "general_config": {
                    "sub_patterns": DEBT_PATTERNS,
                    "sub_total_patterns": SUB_TOTAL_DEBT_PATTERNS,
                },
            },
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "only_use_syllabus_elements": True,
                    "table_regarded_as_paragraph": True,
                    "inject_syllabus_features": [
                        rf"__regex__(?<![{R_CN}])资产负债(结构|情况|构成)(与变动)?分析$",
                    ],
                    "only_inject_features": True,
                    "ignore_syllabus_children": True,
                    "ignore_syllabus_range": True,
                    "include_bottom_anchor": True,
                    "top_anchor_regs": [r"流动负债(科目|结构|情况|构成)分析"],
                    "bottom_default": True,
                },
                "general_model": "sub_account",
                "general_config": {
                    "sub_patterns": ASSET_PATTERNS,
                    "sub_total_patterns": SUB_TOTAL_ASSET_PATTERNS,
                },
            },
        ],
    },
    {
        "path": ["盈利能力分析"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__盈利情况分析",
                ],
            },
        ],
    },
    {
        "path": ["现金流量分析"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["偿债能力分析"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["运营能力分析"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["关联方及关联交易"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__交易关联方及关联交易",
                ],
            },
        ],
    },
    {
        "path": ["对外担保情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "invalid_parent_features": [
                    r"__regex__发行人\d{4}年\d{1,2}-\d{1,2}月经营及财务情况__regex__其他财务重要事项",
                ],
                "inject_syllabus_features": [
                    r"__regex__对外担保(情况)?$",
                ],
            },
        ],
    },
    {
        "path": ["未决诉讼、仲裁情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__未决诉讼(.仲裁.)?情况",
                    r"__regex__未决诉讼（仲裁）",
                    r"__regex__未决诉讼(、仲裁)?",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"无重[大要](未决)?诉讼",
                ],
            },
        ],
    },
    {
        "path": ["受限资产情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "invalid_parent_features": [
                    r"__regex__发行人\d{4}年\d{1,2}-\d{1,2}月经营及财务情况__regex__其他财务重要事项",
                ],
                "inject_syllabus_features": [
                    r"__regex__资产抵押、质押及其他所有权或使用权受到限制的资产",
                ],
            },
        ],
    },
    {
        "path": ["释义"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["发行人主体提示"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
            {
                "name": "elements_collector_based",
                "elements_collect_model": "fixed_position",
                "elements_collect_config": {
                    "target_element": ElementType.PARAGRAPH.value,
                    "pages": [5, 6],
                },
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": False,
                    "top_anchor_regs": [
                        r"发行人主体提示",
                    ],
                    "bottom_anchor_regs": [
                        r"投资人保护机制相关提示",
                    ],
                },
            },
        ],
    },
    {
        "path": ["利率风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["流动性风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["偿付风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["财务风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["经营风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["管理风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["政策风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["特有风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__特有的?风险$",
                ],
            },
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
