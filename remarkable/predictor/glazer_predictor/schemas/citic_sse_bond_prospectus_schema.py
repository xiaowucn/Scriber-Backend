"""
上交所公司债募集说明书
"""

from remarkable.common.pattern import MatchMulti, NeglectPattern
from remarkable.predictor.common_pattern import R_CN, R_CONJUNCTION, R_LEFT_BRACKET, R_RIGHT_BRACKET
from remarkable.predictor.eltype import ElementClass
from remarkable.predictor.glazer_predictor.schemas import ASSET_DEBT_ACCOUNTS

R_SCOPE_OF_CONSOLIDATION = r"(发行人)?合并(财务)?(报表)?范围"
R_MORE_THAN = r"(大于|高于|超过)"
R_LESS_THAN = r"(小于|低于|(未|不)(超过|高于|足))"
R_CONTROLLER = (
    rf"(政府国有资产监督管理委员会|{R_LEFT_BRACKET}集团{R_RIGHT_BRACKET}有限公司|委员会|公司|集团|政府|(国务院)?国资委)"
)
R_ISSUER = r"(发行人|公司)"


DEBT_PATTERNS = ASSET_DEBT_ACCOUNTS + [
    r"^(?P<content>短期借款)$",
    r"^(?P<content>应付账款)$",
    r"^(?P<content>其他流动负债)$",
    r"^(?P<content>长期借款)$",
    r"^(?P<content>一年内到期的?非流动负债)$",
    r"^(?P<content>应付债券)$",
    r"^(?P<content>合同负债)$",
    r"^(?P<content>合同负债.预收款项.)$",
    r"^(?P<content>长期应付款)$",
    r"^(?P<content>其他应付款)$",
    r"^(?P<content>其他应付款.不含应付利息.)$",
    r"^(?P<content>年内到期的非流动负债)$",
    r"^(?P<content>其他非流动负债)$",
    r"^(?P<content>租赁保证金)$",
    r"^(?P<content>应付票据)$",
    "^(?P<content>担保合同准备金)$",
]

SUB_TOTAL_DEBT_PATTERNS = NeglectPattern(
    match=MatchMulti.compile(
        "流动负债$",
        "非流动负债(结构)?分析$",
        "有息负债分析$",
        rf"^{R_LEFT_BRACKET}?[\d一二三四五六七八九十]+.*(情况|分析)$",
        operator=any,
    ),
    unmatch=MatchMulti.compile(
        r"^\d{4}年",
        r"^表",
        operator=any,
    ),
)

ASSET_PATTERNS = ASSET_DEBT_ACCOUNTS + [
    r"^(?P<content>货币资金)$",
    "^(?P<content>年内到期的非流动资产)$",
    "^(?P<content>其他应收款)$",
    "^(?P<content>应收票据及应收账款)$",
    "^(?P<content>在建工程)$",
    "^(?P<content>固定资产)$",
    "^(?P<content>长期股权投资)$",
    "^(?P<content>存货)$",
    "^(?P<content>无形资产)$",
    "^(?P<content>其他权益工具投资)$",
    "^(?P<content>投资性房地产)$",
    "^(?P<content>交易性金融资产)$",
    "^(?P<content>应收账款)$",
    "^(?P<content>递延所得税资产)$",
    "^(?P<content>其他流动资产)$",
    "^(?P<content>长期应收款)$",
    "^(?P<content>预付账款)$",
    "^(?P<content>预付款项)$",
    "^(?P<content>应收融资租赁款)$",
    "^(?P<content>抵债资产)$",
    "^(?P<content>其他非流动资产)$",
    "^(?P<content>合同资产)$",
]

SUB_TOTAL_ASSET_PATTERNS = NeglectPattern(
    match=MatchMulti.compile(
        "流动资产$",
        "非流动资产(结构|项目)?分析$",
        rf"^{R_LEFT_BRACKET}?[\d一二三四五六七八九十]+.*(情况|分析)$",
        r"非流动资产同行业对比",
        operator=any,
    ),
    unmatch=MatchMulti.compile(
        r"^\d{4}年",
        r"^表",
        r"单项金额重大并单项计提坏账准备及单项金额虽不重大但单项计提坏账准备的情况",
        r"1）投资性房地产中的房屋建筑物情况",
        r"2）投资性房地产中的土地使用权情况",
        operator=any,
    ),
)

predictor_options = [
    {
        "path": ["发行人设立情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["发行人历史沿革"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    rf"__regex__{R_ISSUER}历史沿革__regex__变更情况",
                    rf"__regex__{R_ISSUER}的历史沿革",
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
                "syllabus_regs": [
                    r"控股股东[及和]实际控制人(基本)?(情况)?$",
                    r"股权结构",
                    r"控股股东(基本)?(情况)?$",
                ],
                "regs": [
                    rf"(控股)?股东([{R_CONJUNCTION}]实际控制人均?)?为(?P<dst>.*?{R_CONTROLLER})",
                    rf"(?P<dst>[{R_CN}]+?{R_CONTROLLER})系{R_ISSUER}的?控股股东",
                    rf"(?P<dst>[{R_CN}]+?{R_CONTROLLER}).*(股权|出资)比例[为占].*?是.*的?(控股股东|出资人)",
                    rf"(?P<dst>[{R_CN}]+?{R_CONTROLLER})(直接)?持有.*股权.[是为]{R_ISSUER}的控股股东",
                ],
                "model_alternative": True,
            },
            {
                "name": "table_kv",
                "syllabus_regs": [
                    r"控股股东(基本)?(情况)?$",
                ],
                "feature_white_list": [rf"{R_ISSUER}名称"],
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
                    rf"{R_ISSUER}的?实际控制人为(?P<dst>.*?{R_CONTROLLER})",
                    rf"{R_ISSUER}的?(控股)?股东([{R_CONJUNCTION}]实际控制人均?)?为(?P<dst>.*?{R_CONTROLLER})",
                ],
            },
            {
                "name": "partial_text",
                "syllabus_regs": [
                    r"控股股东及实际控制人情况$",
                    r"股权结构",
                ],
                "regs": [
                    rf"{R_ISSUER}的?控股股东及实际控制人均?为(?P<dst>.*?(委员会|公司))",
                    rf"(?P<dst>[{R_CN}]+?{R_CONTROLLER}).*(股权|出资)比例[为占].*?是.*的?(控股股东|出资人)[{R_CONJUNCTION}]实际控制人",
                    rf"(?P<dst>[{R_CN}]+?{R_CONTROLLER})作为.*出资者.*是{R_ISSUER}的实际控制人",
                    rf"(?P<dst>[{R_CN}]+?{R_CONTROLLER})持有.*股权.是{R_ISSUER}的实际控制人",
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
                    rf"__regex__{R_ISSUER}(的重要)?权益投资情况",
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
                    rf"__regex__持股比例(大于|高于|超过)50[%％]但[不未]纳入{R_SCOPE_OF_CONSOLIDATION}",
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
                    rf"存在.*{R_ISSUER}持股比例{R_MORE_THAN}50[%％]但[不未]纳入{R_SCOPE_OF_CONSOLIDATION}的.*公司",
                ],
                "bottom_anchor_regs": [
                    rf"因此未将.*纳入{R_SCOPE_OF_CONSOLIDATION}",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [
                    rf"存在.*发行人持股比例{R_MORE_THAN}50[%％]但[不未]纳入{R_SCOPE_OF_CONSOLIDATION}的.*公司",
                    rf"发行人持股比例{R_MORE_THAN}50[%％]但[不未]纳入{R_SCOPE_OF_CONSOLIDATION}的.*公司",
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
                    rf"__regex__报告期内发行人持股比例(不高于|小于|低于)(等于)?50[%％]但纳入{R_SCOPE_OF_CONSOLIDATION}的情况",
                    rf"__regex__发行人持股比例(不高于|小于|低于)(等于)?50[%％]但纳入{R_SCOPE_OF_CONSOLIDATION}的子公司",
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
                ],
                "include_bottom_anchor": True,
                "bottom_continue_greed": True,
                "bottom_greed": True,
                "top_anchor_regs": [
                    rf"发行人存在.*家持股比例{R_LESS_THAN}或等于50%但纳入{R_SCOPE_OF_CONSOLIDATION}的子公司",
                    rf"存在.*发行人持股比例{R_LESS_THAN}50[%％]但纳入{R_SCOPE_OF_CONSOLIDATION}的子公司",
                ],
                "bottom_anchor_regs": [
                    rf"发行人(持有|拥有).*([(（].*[)）])?([1234][\d.]+[%％]的股权|实际控制权).*纳入{R_SCOPE_OF_CONSOLIDATION}",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [
                    rf"发行人.*持股比例{R_LESS_THAN}50[%％]但纳入{R_SCOPE_OF_CONSOLIDATION}的子公司",
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
                "neglect_syllabus_regs": [
                    r"发行人主要财务情况",
                ],
            },
        ],
    },
    {
        "path": ["发行人的治理结构等情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    rf"__regex__{R_ISSUER}的?治理结构等情况",
                    rf"__regex__{R_ISSUER}的?组织架构和公司治理",
                ],
            },
        ],
    },
    {
        "path": ["发行人董事、监事、高级管理人员基本情况表"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__董事、监事、高级管理人员基本情况",
                ],
                "valid_types": [ElementClass.TABLE.value],
            },
        ],
    },
    {
        "path": ["董事、监事、高级管理人员简介"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [
                    rf"__regex__{R_ISSUER}的董监高情况__regex__董事、监事及其他非董事高级管理人员基本情况"
                ],
                "bottom_continue_greed": True,
                "bottom_greed": True,
                "top_anchor_regs": [
                    r"董事会成员$",
                ],
                "bottom_anchor_regs": [
                    rf"{R_ISSUER}高管人员设置符合《公司法》等相关法律法规及公司章程的规定",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    rf"__regex__董事(、监事)?[{R_CONJUNCTION}]高级管理人员的?主要工作经历",
                    r"__regex__董事、监事、高级管理人员简历",
                ],
                "skip_table": True,
            },
        ],
    },
    {
        "path": ["董事、监事、高级管理人员设置符合《公司法》等相关法律法规及公司章程的说明"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    rf"{R_ISSUER}.*符合.*《?公司章程》?.*(相关)?(规定|要求)",
                    rf"根据《公司章程》.*{R_ISSUER}目前在任监事不存在《公司法》等相关法律法规规定的不得担任监事的情形",
                    rf"{R_ISSUER}.*管理人员的设置.*的规定.不存在重大违纪违法情况",
                    rf"{R_ISSUER}.*不存在.*法律法规所规定的不得担任.*的情形.*不存在重大违法违纪行为",
                    rf"{R_ISSUER}.*有关规定选举和任命产生.*不存在.*超越公司董事会职权做出人事任免决定的情况",
                    r"公司董事、监事、高级管理人员的任职符合《公司法》的规定",
                    rf"{R_ISSUER}.*高级管理人员的设置《公司法》等相关法律法规的规定，不存在重大违纪违法情况",
                    rf"{R_ISSUER}.*高级管理人员报告期内不存在违法违规情况，任职资格符合《公司法》及《公司章程》的规定。",
                ],
                "neglect_regs": [r"董事会的召集、召开等相关程序符合《公司章程》"],
            },
        ],
    },
    {
        "path": ["所在行业状况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__所[处在]行业[情状]况",
                    r"__regex__行业(现状|概况)",
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
                    rf"__regex__{R_ISSUER}的行业地位",
                    rf"__regex__{R_ISSUER}在行业所处地位",
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
                    rf"__regex__{R_ISSUER}未来发展面临的竞争格局及挑战",
                    rf"__regex__{R_ISSUER}的?竞争优势$",
                ],
                "syllabus_black_list": [
                    r"发行人发展战略及面临的主要竞争",
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
                    rf"__regex__{R_ISSUER}的经营方针和战略",
                    r"__regex__发展战略",
                ],
                "syllabus_black_list": [
                    r"发行人发展战略及面临的主要竞争",
                ],
            },
        ],
    },
    {
        "path": ["发行人行业地位、竞争优势、战略目标、发展规划"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    rf"__regex__{R_ISSUER}在?行业(中的)?地位[{R_CONJUNCTION}]竞争优势",
                    rf"__regex__{R_ISSUER}发展战略[{R_CONJUNCTION}]面临的主要竞争",
                ],
            },
        ],
    },
    {
        "path": ["发行人主营业务情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    rf"__regex__{R_ISSUER}主营业务情况",
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
                    rf"(?P<dst>其他与{R_ISSUER}主体相关的重要情况)",
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
        "path": ["发行人财务报告编制基础、审计情况、财务会计信息适用《企业会计准则》情况等"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__财务报表编制基础、审计情况、财务会计信息适用《企业会计准则》情况等",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    rf"__regex__{R_ISSUER}财务报告总体情况",
                ],
                "break_para_pattern": [r"会计(政策|估计变更)"],
                "child_features": [
                    r"财务报表编制基础",
                ],
            },
        ],
    },
    {
        "path": ["重大会计政策变更、会计估计变更、会计差错更正情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__会计政策、会计估计变更及差错更正",
                    rf"__regex__重大会计政策变更、会计估计变更[{R_CONJUNCTION}]会计差错更正情况",
                    r"__regex__会计政策/会计估计调整对财务报表的影响",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "multi": True,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    rf"__regex__{R_ISSUER}财务报告总体情况__regex__重大会计政策变更、会计估计变更情况$",
                    rf"__regex__{R_ISSUER}财务报告总体情况__regex__重要前期差错更正及影响$",
                ],
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
        "path": ["合并范围变化情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    rf"__regex__{R_ISSUER}财务报表合并范围变化",
                    r"__regex__合并报表范围的变化",
                    r"__regex__合并范围主要变化情况",
                ],
                "neglect_patterns": [
                    rf"{R_ISSUER}财务报告总体情况",
                ],
            },
        ],
    },
    {
        "path": ["会计师事务所变更"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": [
                    rf"{R_ISSUER}财务报告编制基础、审计情况、财务会计信息适用《企业会计准则》情况等",
                    r"财务报告编制基础、审计情况、财务会计信息适用《企业会计准则》情况",
                ],
                "inject_syllabus_features": [
                    r"__regex__会计师事务所变更情况",
                ],
            },
            {
                "name": "para_match",
                "syllabus_regs": [
                    rf"{R_ISSUER}财务报告编制基础、审计情况、财务会计信息适用《企业会计准则》情况等",
                    r"财务报告编制基础、审计情况、财务会计信息适用《企业会计准则》情况",
                ],
                "paragraph_pattern": [
                    r"会计师事务所.*变更前后会计政策和会计估计不存在重大变化",
                    r"会计师事务所.*会计师事务所",
                ],
            },
        ],
    },
    {
        "path": ["发行人财务会计信息及主要财务指标"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__最近两年及一期的会计报表",
                    r"__regex__最近两年及一期主要财务指标",
                ],
                "multi": True,
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    rf"__regex__{R_ISSUER}财务会计信息及主要财务指标",
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
        "path": ["现金流量分析"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__现金使用分析",
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
        "path": ["盈利能力分析"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["关联交易情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__关联交易(情况)?$",
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
                    r"__regex__发行人财务状况分析__regex__对外担保情况",
                    r"__regex__对外担保(情况|事项)?$",
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
        "path": ["受限资产情况"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "invalid_parent_features": [
                    r"__regex__发行人\d{4}年\d{1,2}-\d{1,2}月经营及财务情况__regex__其他财务重要事项",
                ],
                "inject_syllabus_features": [
                    r"__regex__受限资产(情况)?",
                ],
            },
        ],
    },
    {
        "path": ["与发行人相关的重大事项"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__发行人相关的重大事项",
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
        "path": ["利率风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__本[次期]债券特有的利率风险$",
                ],
            },
        ],
    },
    {
        "path": ["流动性风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "keep_parent": True,
            },
        ],
    },
    {
        "path": ["偿付风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__本[次期]债券特有的偿付风险$",
                ],
            },
        ],
    },
    {
        "path": ["其他投资风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__本[次期]债券特有的其他投资风险$",
                ],
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
        "path": ["偿还到期债务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"置换前期自有资金偿还的公司债券本金",
                    r"用于科技创新类股权投资",
                    r"__regex__偿还(到期|存续)?(公司)?(有息)?(债务|债券|负债)$",
                    r"__regex__偿还银行借款",
                ],
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "only_inject_features": True,
                "table_regarded_as_paragraph": True,
                "inject_syllabus_features": [
                    r"__regex__(本(期|次)债券)?募集资金(使用|运用)计划$",
                ],
                "include_bottom_anchor": True,
                "top_anchor_regs": [
                    r"因本次债券的发行时间及实际(发行)?规模尚?有一定的?不确定性",
                ],
                "bottom_anchor_regs": [
                    r"不影响偿债计划.*补充流动资金",
                ],
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "only_inject_features": True,
                "table_regarded_as_paragraph": True,
                "inject_syllabus_features": [
                    r"__regex__(本(期|次)债券)?募集资金(使用|运用)计划$",
                ],
                "keywords": [
                    rf"偿还[{R_CN}]*(债务|债券|负债|本金).{{,5}}(明细|如下)",
                ],
                "include_bottom_anchor": True,
                "bottom_default": True,
                "top_anchor_regs": [
                    rf"偿还[{R_CN}]*(债务|债券|负债|本金)",
                ],
            },
        ],
    },
    {
        "path": ["补充流动资金"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    "补充流动资金",
                    "补充营运资金",
                ],
            },
            {
                "name": "syllabus_based",
                "include_title": False,
                "inject_syllabus_features": [
                    r"__regex__(本(期|次)债券)?募集资金(使用|运用)计划$",
                ],
                "only_inject_features": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [rf"元拟?(用于)?补充[{R_CN}]*流动资金"],
                },
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
                    r"用于科技创新类股权投资",
                ],
            },
        ],
    },
    {
        "path": ["设立或认购基金份额"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "only_inject_features": True,
                "table_regarded_as_paragraph": True,
                "inject_syllabus_features": [
                    r"__regex__科创领域投资$",
                ],
                "include_bottom_anchor": True,
                "top_anchor_regs": [
                    r"主要用于创业投资基金出资",
                ],
                "bottom_default": True,
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
        "path": ["发行人关于本次债券募集资金的承诺"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["发行人有关机构"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["投资者保护机制"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["违约事项及纠纷解决机制"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["持有人会议规则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["债券受托管理人"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["信息披露安排"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["税项"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["历史评级变动的原因"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"(?P<content>.*评级均?为.*(未发生变动|无变化))",
                    r"(?P<content>.*不存在与本次主体评级结果有差异的情形。)",
                    r"(?P<content>.*评级无变动。)",
                    r"评级结果存在差异.*(显著(增强|提升)|所致)",
                    r"评级为.*较其.*评级.*显著(增强|提升)",
                ],
            },
        ],
    },
    {
        "path": ["发行人主要贷款银行的授信及使用"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["发行人已注册尚未发行债券"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"尚未发行的债券额度情况",
                    r"发行人及子公司已注册未发行债券情况",
                ],
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [
                    r"__regex__发行人及其?主要子公司境内外债券发行、偿还及尚未发行额度情况",
                    r"__regex__发行人境内外债券发行、偿还及尚未发行额度情况",
                    r"发行人尚未发行的各债券品种额度",
                ],
                "table_regarded_as_paragraph": True,
                "include_bottom_anchor": True,
                "bottom_default": True,
                "top_anchor_regs": [
                    r"截至本募集说明书签署日，除本次债券外，发行人及主要子公司已注册",
                    r"(?<!不)存在已注册尚未发行(完毕)?的债券",
                    r"已注册尚未发行的债券(.?(具体)?情况|\d)",
                    r"尚未发行的公司信用类债券如下",
                    r"该批文项下额度尚未发行",
                ],
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [
                    r"发行人尚未发行的额度情况",
                ],
                "table_regarded_as_paragraph": True,
                "include_bottom_anchor": True,
                "bottom_default": True,
                "top_anchor_regs": [
                    r"截至本募集说明书签署日，除本次债券外，发行人及主要子公司已注册",
                    r"(?<!不)存在已注册尚未发行(完毕)?的债券",
                    r"已注册尚未发行的债券(.?(具体)?情况如下|\d)",
                    r"尚未发行的公司信用类债券如下",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"不存在已注册尚未发行的债券",
                ],
            },
        ],
    },
    {
        "path": ["其他影响资信重大事项"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["发行人、主承销商、证券服务机构及相关人员声明"],
        "post_process": "post_process_ocr",
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    "发行人、主承销商、证券服务机构及相关人员声明",
                    "发行人、中介机构及相关人员声明",
                    "发行人声明",
                ],
            }
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
