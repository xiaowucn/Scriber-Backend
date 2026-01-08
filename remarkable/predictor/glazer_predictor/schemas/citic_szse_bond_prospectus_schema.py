"""
深交所公司债募集说明书
"""

from remarkable.predictor.common_pattern import R_CN, R_CONJUNCTION
from remarkable.predictor.eltype import ElementClass
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
                "invalid_parent_features": [
                    "__regex__发行人历史沿革__regex__历史沿革",
                ],
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
                "invalid_child_features": [
                    "__regex__历史沿革__regex__公司[成设]立",
                    "__regex__公司[成设]立",
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
                    rf"{R_ISSUER}的?(控股)?股东([{R_CONJUNCTION}]实际控制人均?)?为(?P<dst>.*?{R_CONTROLLER})",
                    rf"(?P<dst>[{R_CN}]+?{R_CONTROLLER})(持有{R_ISSUER}.*的股权.)?[系为]{R_ISSUER}的?控股股东",
                    rf"唯一出资人(?P<dst>[{R_CN}]+)持有{R_ISSUER}100.00[%％]的股权",
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
                    rf"{R_ISSUER}的?实际控制人为(?P<dst>.*?政府.*?委员会)",
                    rf"实际控制人为(?P<dst>.*?{R_CONTROLLER})",
                ],
            },
            {
                "name": "partial_text",
                "syllabus_regs": [
                    r"控股股东及实际控制人情况$",
                    r"股权结构",
                ],
                "regs": [
                    rf"{R_ISSUER}的?控股股东及实际控制人均?为(?P<dst>.*?{R_CONTROLLER})",
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
                "inject_syllabus_features": [r"__regex__发行人的?股权结构"],
            },
        ],
    },
    {
        "path": ["发行人控股股东情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
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
                "syllabus_black_list": [
                    r"股权结构",
                    r"[及和]",
                    r"质押情况",
                ],
                "inject_syllabus_features": [
                    rf"__regex__{R_ISSUER}实际控制人的?情况",
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
                    r"__regex__发行人权益投资情况",
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
                    r"__regex__(主要|发行人)子公司的?情况",
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
                    r"__regex__(主要|发行人)子公司的?情况",
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
                    r"__regex__发行人的治理结构",
                ],
            },
        ],
    },
    {
        "path": ["发行人董事、监事、高级管理人员基本情况表"],
        "models": [
            {
                "name": "syllabus_elt_v2",
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
                    r"__regex__董事、高级管理人员主要(从业|工作)经历",
                ],
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [
                    r"__regex__现任董事、监事和高级管理人员的基本情况__regex__基本情况",
                ],
                "top_anchor_regs": [
                    r"董事简历",
                ],
                "bottom_anchor_regs": [r"现任董事"],
            },
        ],
    },
    {
        "path": ["董事、监事、高级管理人员设置符合《公司法》等相关法律法规及公司章程的说明"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"(发行人|公司).*符合.*《?公司章程》?.*(相关)?(规定|要求)",
                    r"根据《公司章程》.*发行人目前在任监事不存在《公司法》等相关法律法规规定的不得担任监事的情形",
                    r"发行人.*管理人员的设置.*的规定.不存在重大违纪违法情况",
                    r"发行人.*不存在.*法律法规所规定的不得担任.*的情形.*不存在重大违法违纪行为",
                    r"发行人.*有关规定选举和任命产生.*不存在.*超越公司董事会职权做出人事任免决定的情况",
                    r"公司董事、监事、高级管理人员的任职符合《公司法》的规定",
                    r"发行人.*高级管理人员的设置《公司法》等相关法律法规的规定，不存在重大违纪违法情况",
                    r"发行人.*高级管理人员报告期内不存在违法违规情况，任职资格符合《公司法》及《公司章程》的规定。",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__董事、监事(（如有）)?、高级管理人员违法违规和严重失信情况",
                ],
            },
        ],
    },
    {
        "path": ["所在行业状况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["公司所处行业地位"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__公司所处行业地位及竞争优势",
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
                    rf"__regex__{R_ISSUER}面临的主要竞争情况",
                    rf"__regex__{R_ISSUER}未来发展面临的竞争格局及挑战",
                ],
            },
        ],
    },
    {
        "path": ["公司经营方针和战略"],
        "models": [
            {
                "name": "syllabus_elt_v2",
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
        "path": ["公司主营业务情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__公司主营业务情况",
                ],
            },
        ],
    },
    {
        "path": ["其他与发行人主体相关的重要情况", "标题"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>其他与发行人主体相关的重要情况)",
                    r"(?P<dst>媒体质疑事项)",
                ],
            },
        ],
    },
    {
        "path": ["其他与发行人主体相关的重要情况", "正文"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["会计政策、会计估计调整对财务报表的影响"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__会计政策.会计估计调整对财务报表的影响",
                ],
            },
        ],
    },
    {
        "path": ["合并范围变化情况"],
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
                "inject_syllabus_features": [
                    r"__regex__报告期内合并及母公司财务报表",
                ],
            },
        ],
    },
    {
        "path": ["报告期内主要财务指标"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资产结构分析"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
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
        ],
    },
    {
        "path": ["负债结构分析"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    rf"__regex__(?<![{R_CN}])负债(结构|情况|构成)([{R_CONJUNCTION}]变动|情况)?(分析)?$",
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
                        rf"__regex__(?<![{R_CN}])负债(结构|情况|构成)([{R_CONJUNCTION}]变动|情况)?(分析)?$",
                        rf"__regex__(发行人)负债(结构|情况|构成)([{R_CONJUNCTION}]变动|情况)?(分析)?$",
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
        ],
    },
    {
        "path": ["盈利能力分析"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["现金流量分析"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__现金流量情况分析",
                ],
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
            },
        ],
    },
    {
        "path": ["重大未决诉讼、仲裁或行政处罚情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"重大未决诉讼、仲裁或行政处罚情况",
                    r"__regex__未决诉讼(.仲裁.)?情况",
                    r"__regex__未决诉讼（仲裁）",
                    r"__regex__未决(重大)?诉讼([、或]仲裁)?",
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
        "path": ["资产抵押、质押和其他限制用途安排"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__资产抵押、质押和其他限制用途的安排",
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
        "path": ["重大事项提示"],
        "models": [
            {
                "name": "syllabus_elt_v2",
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
        "path": ["本次债券安排所特有的风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__本[次期]债券(偿债)?安排所特有的风险",
                ],
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
        "path": ["与发行人相关的其他风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["本次债券的募集资金规模"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["偿还有息债务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__偿还(公司)?有息(债务|债券|负债)",
                    r"__regex__偿还(到期|存续)(公司)?(债务|债券|负债)",
                    r"__regex__偿还银行借款",
                ],
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "only_inject_features": True,
                "table_regarded_as_paragraph": True,
                "inject_syllabus_features": [
                    r"__regex__本期债券募集资金(使用|运用)计划",
                ],
                "include_bottom_anchor": True,
                "bottom_default": True,
                "top_anchor_range_regs": [r"股权投资具体情况如下"],
                "top_anchor_regs": [
                    r"拟偿还债务明细如下",
                ],
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "only_inject_features": True,
                "table_regarded_as_paragraph": True,
                "inject_syllabus_features": [
                    r"__regex__本期债券的?募集资金(使用|运用)计划__regex__本期债券募集资金用途",
                    r"__regex__本期债券的?募集资金(使用|运用)计划",
                    r"__regex__募集资金(使用|运用)计划",
                ],
                "include_bottom_anchor": True,
                "bottom_default": True,
                "top_anchor_regs": [
                    r"扣除发行费用后.*用于偿还.*(债务|债券|负债)",
                ],
            },
        ],
    },
    {
        "path": ["补充流动资金"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["用于固定资产投资项目"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["股权投资或资产收购"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    "对子公司和参股公司出资",
                    "科技创新领域的投资",
                    "股权投资",
                    "募集资金用于科技创新企业权益出资",
                ],
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "only_inject_features": True,
                "table_regarded_as_paras": True,
                "inject_syllabus_features": [
                    r"__regex__本期债券募集资金(使用|运用)计划",
                ],
                "bottom_default": True,
                "include_bottom_anchor": True,
                "top_anchor_regs": [
                    r"股权投资具体情况如下",
                    r"拟用于子公司.*出资",
                ],
                "bottom_anchor_regs": [
                    r"对被投资单位实施控制",
                ],
            },
        ],
    },
    {
        "path": ["设立或认购基金份额"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["本次债券募集资金专项账户管理安排"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["关于本次债券募集资金的承诺"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["发行人的有关机构及利害关系"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["投资者保护机制"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    "偿债计划和保障措施",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "multi": True,
                "include_title": True,
                "inject_syllabus_features": [
                    "__regex__投资者保护机制__regex__偿债计划",
                    "__regex__投资者保护机制__regex__偿债资金(保障措施|来源)",
                    "__regex__投资者保护机制__regex__偿债应急保障方案",
                    "__regex__投资者保护机制__regex__偿债保障方案",
                    "__regex__投资者保护机制__regex__偿债保障措施承诺",
                ],
            },
        ],
    },
    {
        "path": ["违约事项及纠纷解决机制"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["持有人会议规则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["债券受托管理人"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["信息披露安排"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["税项"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["历史评级变动的原因"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"(?P<content>.*评级均?为.*(未发生变动|无变化)。)",
                    r"(?P<content>.*不存在与本次主体评级结果有差异的情形。)",
                    r"(?P<content>.*评级无变动。)",
                    r"评级结果存在差异.*所致",
                ],
            },
        ],
    },
    {
        "path": ["发行人主要贷款银行的授信及使用"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["发行人已注册尚未发行债券"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["发行人、主承销商、证券服务机构及相关人员声明"],
        "post_process": "post_process_ocr",
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
