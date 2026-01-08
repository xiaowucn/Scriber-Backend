"""
资管合同_补充协议

有些字段没有明确的章节目录，比如: 1、《基金合同》第十二部分第(九)条约定如下:
只能固定的取十二和九来判断
https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/3827#note_446895
"""

from remarkable.predictor.common_pattern import R_CN, R_NOT_SENTENCE_END
from remarkable.predictor.ecitic_predictor.schemas import (
    R_BOTTOM_ANCHOR_REGS,
    R_CHANGE_FLAGS,
    R_CHAPTER,
    R_CONTRACT,
    R_HEADER_PATTERN,
    R_LEFT_BRACKETS,
    R_RIGHT_BRACKETS,
)
from remarkable.predictor.eltype import ElementClass

predictor_options = [
    {
        "path": ["产品名称"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"(?P<content>[^《]*资产管理计划)",
                ],
                "target_element": [ElementClass.PARAGRAPH.value],
            },
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    r"(?P<dst>[^《]*资产管理计划)",
                ],
                "model_alternative": True,
                "page_range": [0],
                "target_element": [ElementClass.PARAGRAPH.value],
            },
        ],
    },
    {
        "path": ["证券交易所释义(其它-投资监督)"],
        "models": [
            {
                "name": "trading_exchange_syllabus",
            },
        ],
    },
    {
        "path": ["期货交易所释义(其它-投资监督)"],
        "models": [
            {
                "name": "trading_exchange_syllabus",
            },
        ],
    },
    {
        "path": ["交易所释义(其它-投资监督)"],
        "models": [
            {
                "name": "trading_exchange_syllabus",
            },
        ],
    },
    {
        "path": ["投资范围(其它-投资监督)"],
        "models": [
            {
                "name": "scope_investment_middle",
                "use_top_crude_neighbor": False,
                "include_top_anchor": False,
                "top_greed": False,
                "top_anchor_range_regs": [
                    *R_CHANGE_FLAGS,
                ],
                "top_anchor_regs": [
                    r"投资范围$",
                    r"投资范围及比例[:：]?$",
                    r"允许投资的金融工具包括[:：]",
                ],
                "bottom_anchor_regs": [
                    r"投资比例$",
                    r"投资比例(为|如下)[:：]",
                    r"应符合以下比例[:：]",
                    r"风险揭示",
                    *R_BOTTOM_ANCHOR_REGS,
                ],
            },
            {
                "name": "scope_investment_middle",
                "use_top_crude_neighbor": False,
                "include_top_anchor": False,
                "top_anchor_range_regs": [
                    rf"{R_CONTRACT}“?第(十一|八){R_CHAPTER}“?资产管理计划的投资.*二",
                    rf"第八{R_CHAPTER}“?资产管理计划的投资”?第{R_LEFT_BRACKETS}二{R_RIGHT_BRACKETS}{R_CHAPTER}“?投资范围及比例",
                    rf"{R_LEFT_BRACKETS}十{R_RIGHT_BRACKETS}{R_CHAPTER}第{R_LEFT_BRACKETS}二{R_RIGHT_BRACKETS}",
                    rf"{R_LEFT_BRACKETS}十一{R_RIGHT_BRACKETS}{R_CHAPTER}第{R_LEFT_BRACKETS}二{R_RIGHT_BRACKETS}",
                ],
                "top_anchor_regs": [
                    *R_CHANGE_FLAGS,
                    r"变更后的投资范围为[：:]",
                    r"删除下述约定",
                ],
                "bottom_anchor_regs": [
                    r"投资比例$",
                    r"投资比例(为|如下)[:：]",
                    r"应符合以下比例[:：]",
                    r"风险揭示",
                    *R_BOTTOM_ANCHOR_REGS,
                ],
            },
            {
                "name": "cell_partial_text",
                "filter_by": "col",
                "header_pattern": R_HEADER_PATTERN,
                "regs": [
                    r"投资范围及比例(?P<dst>.*?)[^。]*本计划投资组合在各类资产上的投资比例",
                ],
            },
        ],
    },
    {
        "path": ["投资比例(其它-投资监督)"],
        "models": [
            {
                "name": "investment_ratio_middle_paras",
                "skip_merged_para": True,
                "include_top_anchor": False,
                "top_anchor_range_regs": [
                    *R_CHANGE_FLAGS,
                ],
                "top_anchor_regs": [
                    r"本计划的投资比例为[：:]",
                    r"投资比例(如下[：:])?$",
                ],
                "bottom_anchor_regs": [
                    # r"可以不符合上述计划配置比例规定",
                    R_CONTRACT,
                    r"投资比例超限的处理方式及流程",
                    r"投资禁止行为",
                ],
            },
            {
                "name": "investment_ratio_middle_paras",
                "skip_merged_para": True,
                "include_top_anchor": False,
                "include_bottom_anchor": True,
                "bottom_default": True,
                "top_anchor_range_regs": [
                    *R_CHANGE_FLAGS,
                ],
                "top_anchor_regs": [
                    r"本计划的投资比例为[：:]",
                    r"投资比例(如下[：:])?$",
                ],
                "bottom_anchor_regs": [
                    # r"可以不符合上述计划配置比例规定",
                    R_CONTRACT,
                    r"投资比例超限的处理方式及流程",
                    r"投资禁止行为",
                ],
            },
            {
                "name": "investment_ratio_middle_paras",
                "skip_merged_para": True,
                "include_top_anchor": False,
                "top_anchor_range_regs": [
                    rf"{R_LEFT_BRACKETS}十{R_RIGHT_BRACKETS}{R_CHAPTER}第{R_LEFT_BRACKETS}五{R_RIGHT_BRACKETS}",
                    rf"{R_LEFT_BRACKETS}八{R_RIGHT_BRACKETS}{R_CHAPTER}第{R_LEFT_BRACKETS}七{R_RIGHT_BRACKETS}",
                    r"((投资比例|投资限制)[和与及]?){2}",
                ],
                "top_anchor_regs": [
                    *R_CHANGE_FLAGS,
                ],
                "bottom_anchor_regs": [
                    # r"可以不符合上述计划配置比例规定",
                    R_CONTRACT,
                    r"投资比例超限的处理方式及流程",
                    r"投资禁止行为",
                ],
            },
            {
                "name": "investment_ratio_middle_paras",
                "use_syllabus_model": True,
                "only_inject_features": True,
                "inject_syllabus_features": [rf"__regex__{R_CONTRACT}“?第八{R_CHAPTER}“?资产管理计划的投资"],
                "top_anchor_range_regs": [r"变更为[：:]"],
                "top_anchor_regs": [r"建仓期结束后.*?符合以下比例"],
                "bottom_anchor_regs": [R_CONTRACT],
            },
            {
                "name": "cell_partial_text",
                "filter_by": "col",
                "header_pattern": R_HEADER_PATTERN,
                "regs": [
                    r"(?P<dst>本计划投资组合在各类资产上的投资比例.*?)[^。]*投资策略",
                ],
            },
        ],
    },
    {
        "path": ["投资策略(其它-投资监督)"],
        "models": [
            {
                # 不使用章节模型
                "name": "middle_paras",
                "include_top_anchor": False,
                "top_greed": False,
                "top_anchor_regs": [
                    r"投资策略.*?(增加|删除|减少).*?如下",
                ],
                "bottom_anchor_regs": [
                    r"投资限制",
                    *R_BOTTOM_ANCHOR_REGS,
                ],
            },
            {
                "name": "middle_paras",
                "use_top_crude_neighbor": False,
                "include_top_anchor": False,
                "top_greed": False,
                "top_anchor_regs": [
                    r"投资策略$",
                ],
                "top_anchor_range_regs": R_CHANGE_FLAGS,
                "bottom_anchor_regs": [
                    r"投资限制",
                    *R_BOTTOM_ANCHOR_REGS,
                ],
            },
            {
                "name": "middle_paras",
                "use_top_crude_neighbor": False,
                "include_top_anchor": False,
                "top_greed": False,
                "top_anchor_range_regs": [
                    rf"{R_LEFT_BRACKETS}八{R_RIGHT_BRACKETS}{R_CHAPTER}第{R_LEFT_BRACKETS}六{R_RIGHT_BRACKETS}",
                ],
                "top_anchor_regs": R_CHANGE_FLAGS,
                "bottom_anchor_regs": [
                    r"投资限制",
                    *R_BOTTOM_ANCHOR_REGS,
                ],
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["投资限制(其它-投资监督)"],
        "models": [
            {
                "name": "investment_restrictions_tuple_table",
                "原文": {
                    "feature_white_list": [r"__regex__资产管理计划的?投资__regex__修改后"],
                    "feature_black_list": [r"修改后|十一资产管理计划投资"],
                },
            },
            {
                "name": "investment_restrictions_middle",
                "use_top_crude_neighbor": False,
                "include_top_anchor": False,
                "top_anchor_regs": [
                    r"投资限制.*?(增加|删除|减少).*?如下",
                ],
                "neglect_top_anchor": [
                    r"对投资限制的监督",
                ],
                "bottom_anchor_regs": [
                    *R_BOTTOM_ANCHOR_REGS,
                    r"规避证券期货市场异常波动",
                    r"禁止行为$",
                ],
            },
            {
                "name": "investment_restrictions_middle",
                "use_top_crude_neighbor": False,
                "include_top_anchor": False,
                "top_greed": False,
                "top_anchor_range_regs": R_CHANGE_FLAGS,
                "top_anchor_regs": [
                    r"投资限制$",
                ],
                "neglect_top_anchor": [
                    r"投资比例和投资限制$",
                ],
                "bottom_anchor_regs": [
                    *R_BOTTOM_ANCHOR_REGS,
                    r"规避证券期货市场异常波动",
                    r"禁止行为$",
                ],
            },
            {
                "name": "investment_restrictions_middle",
                "use_top_crude_neighbor": False,
                "include_top_anchor": False,
                "top_anchor_range_regs": [
                    rf"{R_CONTRACT}“?第?八{R_CHAPTER}“?资产管理计划的投资.*七.*投资限制",
                    r"投资比例和投资限制$",
                ],
                "top_anchor_regs": [*R_CHANGE_FLAGS],
                "bottom_anchor_regs": [
                    *R_BOTTOM_ANCHOR_REGS,
                    r"规避证券期货市场异常波动",
                    r"禁止行为$",
                ],
            },
            {
                "name": "cell_partial_text",
                "filter_by": "col",
                "header_pattern": R_HEADER_PATTERN,
                "regs": [
                    r"投资限制(?P<dst>.*?)[^。;；]*本合同委托财产的投资禁止",
                ],
            },
            {
                # 章节模型
                "name": "investment_restrictions",
                "inject_syllabus_features": [r"__regex__^投资限制"],
            },
        ],
    },
    {
        "path": ["预警线(其它-投资监督)"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_top_crude_neighbor": False,
                    "top_anchor_range_regs": [r"预警|平仓|止损"],
                    "top_anchor_regs": R_CHANGE_FLAGS,
                    "bottom_anchor_regs": [
                        r"资产管理人特别提示",
                        r"管理人负责执行",
                        *R_BOTTOM_ANCHOR_REGS,
                    ],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        rf"(将(计划)?份额净值|设置)(?P<dst>{R_NOT_SENTENCE_END}*?元(\/份)?)(设置)?为?预警线",
                        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4388#note_498123
                        rf"预警线[为：:][{R_CN}]*(?P<dst>{R_NOT_SENTENCE_END}*元?(\/份)?)",
                        rf"本(单一|资产管理)?(计划|基金)([不未]设置?|无){R_NOT_SENTENCE_END}*预警{R_NOT_SENTENCE_END}*",
                    ],
                },
            },
            {
                "name": "partial_text",
                "regs": [
                    rf"(将(计划)?份额净值|设置)(?P<dst>{R_NOT_SENTENCE_END}*?元(\/份)?)(设置)?为?预警线",
                    rf"预警线为[{R_CN}]*(?P<dst>{R_NOT_SENTENCE_END}*?元(\/份)?)",
                    rf"本(单一|资产管理)?(计划|基金)([不未]设置?|无){R_NOT_SENTENCE_END}*预警{R_NOT_SENTENCE_END}*",
                ],
            },
        ],
    },
    {
        "path": ["预警线描述(其它-投资监督)"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_top_crude_neighbor": False,
                    "include_bottom_anchor": True,
                    "skip_merged_para": True,
                    "top_anchor_range_regs": [r"预警|平仓|止损"],
                    "top_anchor_regs": R_CHANGE_FLAGS,
                    "bottom_anchor_regs": [
                        r"触及(平仓|止损)线",
                        r"^本计划设置止损线",
                        r"负责(监控并)?执行",
                    ],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "order_by_index": True,
                    "regs": [
                        rf"预警线为.*元([\(（]{R_NOT_SENTENCE_END}*[）\)])?[。，,.;；](?P<dst>.*)",
                        r"(?P<dst>.*份额净值[^。，,.;；(（]*?预警线.*)",
                        r".*触及预警线.*",
                    ],
                    "neglect_patterns": [
                        r"特别提示",
                        r"设置为预警线",
                        r"预警.*由.*负责(监控并)?执行",
                    ],
                },
            },
            {
                "name": "para_match",
                "paragraph_pattern": [r"(?P<content>当(基金|资产)?(管理人|托管人).*(相关|提示)风险)"],
            },
        ],
    },
    {
        "path": ["止损线(其它-投资监督)"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_top_crude_neighbor": False,
                    "include_bottom_anchor": True,
                    "top_anchor_range_regs": [r"预警|平仓|止损"],
                    "top_anchor_regs": R_CHANGE_FLAGS,
                    "bottom_anchor_regs": [
                        r"资产管理人特别提示",
                        r"管理人负责执行",
                    ],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        rf"[，,](?P<dst>{R_NOT_SENTENCE_END}*?元(\/份)?)为?止损线",
                        rf"(将(计划)?份额净值|设置)为?(?P<dst>{R_NOT_SENTENCE_END}*?元(\/份)?)(设置)?为?止损线",
                        rf"止损线为[{R_CN}]*(?P<dst>{R_NOT_SENTENCE_END}*?元(\/份)?)",
                        rf"本(单一|资产管理)?(计划|基金)([不未]设置?|无){R_NOT_SENTENCE_END}*(止损|平仓){R_NOT_SENTENCE_END}*",
                    ],
                },
            },
            {
                "name": "partial_text",
                "syllabus_regs": [r"止损"],
                "regs": [
                    rf"[，,](?P<dst>{R_NOT_SENTENCE_END}*?元(\/份)?)为?止损线",
                    rf"(将(计划)?份额净值|设置)为?(?P<dst>{R_NOT_SENTENCE_END}*?元(\/份)?)(设置)?为?止损线",
                    rf"止损线为[{R_CN}]*(?P<dst>{R_NOT_SENTENCE_END}*?元(\/份)?)",
                    rf"本(单一|资产管理)?(计划|基金)([不未]设置?|无){R_NOT_SENTENCE_END}*(止损|平仓){R_NOT_SENTENCE_END}*",
                ],
            },
        ],
    },
    {
        "path": ["止损线描述(其它-投资监督)"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "include_bottom_anchor": True,
                    "skip_merged_para": True,
                    "top_anchor_range_regs": [r"预警|平仓|止损"],
                    "top_anchor_regs": R_CHANGE_FLAGS,
                    "bottom_anchor_regs": [
                        r"资产管理人特别提示",
                        r"管理人负责执行",
                    ],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "order_by_index": True,
                    "regs": [
                        rf"止损线为.*元([\(（]{R_NOT_SENTENCE_END}*[）\)])?[。，,.;；](?P<dst>.*?)[^。]*负责执行",
                        rf"止损线为.*元([\(（]{R_NOT_SENTENCE_END}*[）\)])?[。，,.;；](?P<dst>.*)",
                        r"(?P<dst>当.*)",
                        r".*资产(全部)?变现后本?计划提前终止.*",
                        r".*触及(平仓|止损)线.*",
                    ],
                    "neglect_patterns": [
                        r"特别提示",
                        r"设置[为了](止损线|预警止损机制)",
                        r"预警线",
                        r"计划的预警和止损由资产管理人负责执行",
                    ],
                },
            },
            {
                "name": "middle_paras",
                "include_bottom_anchor": True,
                "top_anchor_range_regs": R_CHANGE_FLAGS,
                "top_anchor_regs": [r"交易日内"],
                "bottom_anchor_regs": [r"资产管理人特别提示"],
            },
        ],
    },
    {
        "path": ["关联交易(其它-投资监督)"],
        "models": [
            {
                "name": "table_tuple",
                "feature_white_list": [r"__regex__关联交易__regex__修改后"],
            },
            {
                "name": "cell_partial_text",
                "filter_by": "col",
                "title_patterns": [
                    r"利益冲突及关联交易",
                ],
                "header_pattern": R_HEADER_PATTERN,
                "regs": [
                    r".*",
                ],
            },
            {
                "name": "cell_partial_text",
                "filter_by": "col",
                "title_patterns": [
                    r"对照明细表",
                ],
                "header_pattern": R_HEADER_PATTERN,
                "regs": [
                    r"(?P<dst>[^。].利益冲突.*?)[^。]*第",
                ],
            },
            {
                "name": "middle_paras",
                "use_top_crude_neighbor": False,
                "include_top_anchor": False,
                "top_anchor_regs": [
                    r"利益冲突及关联交易.*整[章体](修改|变更)(为|如下)[：:。]",
                    r"利益冲突及关联交易.*如下变更[：:。]",
                ],
                "bottom_anchor_regs": [
                    r"(表述|约定)(如下|为)[：:。]",
                    r"如下(变更|条款)[：:。]",
                    r"^[\d一二三四五六七八九十]+、\s*将.*(中|修改为[：:。])$",
                    r"^[\d一二三四五六七八九十]+、修改",
                    r"^[\d一二三四五六七八九十]+、.*?对.*进行修改",
                    r"原约定[:：]",
                    r"书面同意",
                    r"(删除|增加|减少)[如以]下内容[:：]",
                ],
            },
            {
                "name": "middle_paras",
                "use_top_crude_neighbor": False,
                "include_top_anchor": False,
                "top_anchor_range_regs": [
                    rf"(第|(将|合同)“){R_LEFT_BRACKETS}十[四二]{R_RIGHT_BRACKETS}",
                    r"将.*利益冲突及关联交易.*中",
                ],
                "top_anchor_regs": R_CHANGE_FLAGS,
                "bottom_anchor_regs": [
                    r"(表述|约定)(如下|为)[：:。]",
                    r"如下条款[：:。]",
                    r"^[\d一二三四五六七八九十]+、\s*将.*(中|修改为[：:。])$",
                    r"^[\d一二三四五六七八九十]+、修改",
                    r"^[\d一二三四五六七八九十]+、.*?对.*进行修改",
                    r"原约定[:：]",
                    r"书面同意",
                    r"(删除|增加|减少)[如以]下内容[:：]",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "include_title": True,
                "break_para_pattern": [
                    rf"(修改|将){R_CONTRACT}",
                ],
            },
        ],
    },
    {
        "path": ["越权交易(其它-投资监督)"],
        "models": [  # TODO fid:2514 章节识别有误
            {
                "name": "syllabus_based",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"越权交易",
                ],
                "extract_from": "same_type_elements",
                "match_method": "similarity",
                "use_syllabus_model": True,
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        r"(变更|修改)为[：:](?P<dst>.*)",
                    ]
                },
            },
            {
                "name": "middle_paras",
                "include_top_anchor": False,
                "top_anchor_regs": [
                    r"越权交易.*(增加|删除|减少)[如以]下内容[：:]",
                ],
                "bottom_anchor_regs": [
                    r"后续章节序号顺延[：:]",
                    r"(表述|约定)如下[：:]",
                    r"如下条款[：:]",
                ],
            },
            {
                "name": "middle_paras",
                "multi_blocks": True,
                "use_top_crude_neighbor": False,
                "include_top_anchor": False,
                "top_anchor_regs": R_CHANGE_FLAGS,
                "top_anchor_range_regs": [
                    r"越权交易",
                ],
                "bottom_anchor_regs": [
                    r"(表述|约定)如下[：:]",
                    r"如下条款[：:]",
                    r"^\d+、\s*将.*中$",
                    r"^[一二三四五六七八九十]+、修改",
                ],
                "bottom_anchor_range_regs": [
                    r"^(?!.*越权交易)(?!原).*?(表述|约定)如下[：:]",
                    r"^(?!.*越权交易).*?如下条款[：:]",
                    r"后续章节序号顺延[：:]",
                    r"^\d+、\s*将.*中$",
                ],
            },
        ],
    },
    {
        "path": ["禁止行为(其它-投资监督)"],
        "models": [
            {
                "name": "table_tuple",
                "feature_white_list": [r"__regex__禁止行为__regex__修改后"],
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金的备案(其它-投资监督)"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["调整期(其它-投资监督)"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"恢复交易的?(?P<dst>.*个交易日)(进行调整|内.*?调整至符合(相关)?要求)",
                ],
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["建仓期(其它-投资监督)"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["产品风险等级(其它-投资监督)"],
        "models": [
            {
                "name": "investment_ratio_middle_paras",
                "skip_merged_para": True,
                "include_top_anchor": False,
                "top_greed": False,
                "top_anchor_range_regs": [
                    *R_CHANGE_FLAGS,
                ],
                "top_anchor_regs": [
                    r"风险收益特征",
                ],
                "bottom_anchor_regs": [
                    R_CONTRACT,
                ],
            },
            {
                "name": "cell_partial_text",
                "filter_by": "col",
                "header_pattern": R_HEADER_PATTERN,
                "regs": [
                    r"本计划风险等级[：:](?P<dst>.*?)[^。]*本计划存续期限",
                ],
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
