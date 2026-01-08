"""
私募基金合同
"""

from remarkable.predictor.common_pattern import R_CN, R_NOT_SENTENCE_END


def option_interpretation_paras(keyword, table_config=None):
    basic_table_config = {
        "skip_empty_cell": True,
        "feature_white_list": [rf"__regex__{keyword}"],
    }
    if table_config:
        basic_table_config.update(table_config)
    option = {
        "name": "syllabus_based",
        "inject_syllabus_features": [
            r"__regex__释义$",
        ],
        "extract_from": "same_type_elements",
        "ignore_syllabus_range": True,
        "only_inject_features": True,
        "table_model": "trading_exchange_from_merged_kv",
        "table_config": basic_table_config,
        "paragraph_model": "trading_exchange_para_match",
        "para_config": {
            "paragraph_pattern": (rf"{keyword}[:：](?P<content>.*)",),
        },
    }
    return option


predictor_options = [
    {
        "path": ["产品名称"],
        "models": [
            {
                "name": "syllabus_based",
                "include_title": False,
                "inject_syllabus_features": [
                    r"__regex__名称$",
                    r"__regex__基本情况__regex__名称$",
                ],
                "only_inject_features": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": r"(?P<content>[^。]*)",
                },
            },
            {
                "name": "partial_text",
                "regs": [r"私募基金的名称[:：](?P<dst>[^。]*)"],
            },
        ],
    },
    {
        "path": ["证券交易所释义(其它-投资监督)"],
        "models": [
            {
                "name": "trading_exchange_kv",
                "skip_empty_cell": True,
            },
            option_interpretation_paras("证券交易所"),
        ],
    },
    {
        "path": ["期货交易所释义(其它-投资监督)"],
        "models": [
            {
                "name": "trading_exchange_kv",
                "skip_empty_cell": True,
            },
            option_interpretation_paras("期货交易所"),
        ],
    },
    {
        "path": ["交易所释义(其它-投资监督)"],
        "models": [
            # {
            #     "name": "trading_exchange_kv",
            #     "skip_empty_cell": True,
            # },
            option_interpretation_paras(rf"(?<![{R_CN}])交易所"),
        ],
    },
    {
        "path": ["投资范围(其它-投资监督)"],
        "models": [
            {
                "name": "scope_investment_syllabus",
                "keep_parent": True,
                "inject_syllabus_features": [
                    r"__regex__基金的投资$__regex__投资范围$",
                ],
                "neglect_patterns": [r"基金的基本情况"],
            },
            {
                "name": "scope_investment_middle",
                "use_syllabus_model": True,
                "top_greed": False,
                "include_top_anchor": False,
                "inject_syllabus_features": [
                    r"__regex__^基金的投资$",
                    r"__regex__资产管理计划的投资$",
                ],
                "top_anchor_regs": [
                    r"投资范围[：:]?$",
                ],
                "bottom_anchor_regs": [
                    r"投资比例[：:]?$",
                    r"投资范围的变更程序",
                    r"投资策略$",
                ],
            },
        ],
    },
    {
        "path": ["投资策略(其它-投资监督)"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["投资限制(其它-投资监督)"],
        "models": [
            {
                "name": "investment_restrictions",
                "multi": False,
                "multi_elements": False,
                "only_first": False,
                "include_title": False,
                "inject_syllabus_features": [r"__regex__^投资限制"],
            },
        ],
    },
    {
        "path": ["预警线(其它-投资监督)"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    rf"本基金(不设置|无){R_NOT_SENTENCE_END}*预警{R_NOT_SENTENCE_END}*",
                    r"预警线为?(?P<dst>[^,，。]*元)",
                ],
            },
        ],
    },
    {
        "path": ["预警线描述(其它-投资监督)"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"(?P<content>当(基金|资产)?(管理人|托管人).*预警线.*)",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "ignore_pattern": [
                    r"(预警|平仓)线为",
                    r"平仓(机制|卖出)",
                    r"(不设置|无)((预警|止损|平仓)[和、]?){1,2}(机制|安排)",
                    r"计划持有(多个)?流通受限",
                    r"特别提示",
                ],
            },
        ],
    },
    {
        "path": ["平仓线(其它-投资监督)"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    rf"本基金(不设置|无){R_NOT_SENTENCE_END}*平仓{R_NOT_SENTENCE_END}*",
                    r"本基金不设置预警、止损机制。",
                    r"平仓线为?(?P<dst>[^,，。]*元)",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": ["__regex__预警平仓机制$"],
                "keep_parent": True,
                "neglect_patterns": [r"越权交易的界定"],
            },
        ],
    },
    {
        "path": ["平仓线描述(其它-投资监督)"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"(?P<content>当(基金|资产)?(管理人|托管人).*平仓线.*)",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "ignore_pattern": [
                    r"(预警|平仓)线为",
                    r"预警(机制|卖出)",
                    r"(不设置|无)((预警|止损|平仓)[和、]?){1,2}(机制|安排)",
                    r"计划持有(多个)?流通受限",
                    r"特别提示",
                ],
            },
        ],
    },
    {
        "path": ["关联交易(其它-投资监督)"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": [r"释义"],
                "inject_syllabus_features": [
                    r"__regex__关联交易决策及信息披露机制",
                    r"__regex__利益冲突及处理",
                ],
                "break_para_pattern": [
                    r"授权并同意",
                ],
            },
        ],
    },
    {
        "path": ["越权交易(其它-投资监督)"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__越权交易处理$"],
            },
        ],
    },
    {
        "path": ["禁止行为(其它-投资监督)"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__投资禁止行为$"],
            },
        ],
    },
    {
        "path": ["基金的备案(其它-投资监督)"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__基金的成立与备案__regex__基金的成立与备案"],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"(?P<content>本基金已成立并已完成备案.*)",
                ],
            },
        ],
    },
    {
        "path": ["免责条款(其它-投资监督)"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"因上述机构提供的?信息的?存在瑕疵而所引发的?损失承担任何责任",
                ],
            },
        ],
    },
    {
        "path": ["调整期(其它-投资监督)"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"基金管理人(应|应当)?在(知悉被动超标后)?(?P<dst>\d+个交易日)内调整(完毕|至符合要求)",
                ],
            },
        ],
    },
    {
        "path": ["建仓期(其它-投资监督)"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"基金管理人自本基金成立之日起(?P<dst>.*?个月)内使本基金的投资组合比例符合上款约定",
                ],
            },
        ],
    },
    {
        "path": ["产品风险等级(其它-投资监督)"],
        "models": [
            {
                "name": "syllabus_based",
                "include_title": False,
                "inject_syllabus_features": [
                    r"__regex__资金损失风险",
                ],
                "only_inject_features": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [
                        r"本基金属于.*投资品种.*",
                    ],
                },
            },
            {
                "name": "syllabus_based",
                "include_title": False,
                "inject_syllabus_features": [
                    r"__regex__基金的风险收益特征",
                ],
                "only_inject_features": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [
                        r"本基金属于.*投资品种.*",
                    ],
                },
            },
            {
                "name": "syllabus_based",
                "include_title": False,
                "inject_syllabus_features": [
                    r"__regex__私募基金的基本情况",
                ],
                "only_inject_features": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [
                        r"私募基金的风险收益特征[:：](?P<content>.*)",
                    ],
                },
            },
        ],
    },
    {
        "path": ["债权类资产释义(其它-投资监督)"],
        "models": [
            option_interpretation_paras("债权类资产"),
        ],
    },
    {
        "path": ["股权类资产释义(其它-投资监督)"],
        "models": [
            option_interpretation_paras("股权类资产"),
        ],
    },
    {
        "path": ["期货和衍生品持仓合约价值释义(其它-投资监督)"],
        "models": [
            option_interpretation_paras("期货和衍生品持仓合约价值")
            | {
                "table_config": {
                    "multi": True,
                    "merge_same_key_pairs": True,
                    "skip_empty_cell": True,
                    "feature_white_list": [
                        r"期货和衍生品持仓合约价值",
                    ],
                },
            },
        ],
    },
    {
        "path": ["期货和衍生品账户权益释义(其它-投资监督)"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [
                    r"__regex__释义$",
                ],
                "only_inject_features": True,
                "ignore_syllabus_children": True,
                "top_anchor_regs": [
                    r"期货和衍生品账户权益",
                ],
                "top_anchor_content_regs": [r"期货和衍生品账户权益[:：](?P<content>.*)"],
                "bottom_anchor_regs": ["已投资产"],
            },
            option_interpretation_paras("期货和衍生品账户权益"),
        ],
    },
    {
        "path": ["已投资产释义(其它-投资监督)"],
        "models": [
            option_interpretation_paras(
                "已投资产",
                table_config={
                    "regs": [
                        r"(?P<dst>指基金资产总值-现金管理工具市值.*不包含.*?[。])",
                    ],
                },
            ),
        ],
    },
    {
        "path": ["同一资产释义(其它-投资监督)"],
        "models": [
            option_interpretation_paras("同一资产")
            | {
                "table_config": {"multi": True, "merge_same_key_pairs": True, "skip_empty_cell": True},
            },
            option_interpretation_paras(
                "同一资产",
                table_config={
                    "regs": [
                        r"指基金资产总值-现金管理工具市值.*不包含.*?[。](?P<dst>.*)",
                    ],
                },
            ),
        ],
    },
    {
        "path": ["债券评级规则释义(其它-投资监督)"],
        "models": [
            option_interpretation_paras("债券评级(规则)?"),
        ],
    },
    {
        "path": ["利率债释义(其它-投资监督)"],
        "models": [
            option_interpretation_paras("利率债"),
        ],
    },
    {
        "path": ["信用债释义(其它-投资监督)"],
        "models": [
            option_interpretation_paras("信用债"),
        ],
    },
    {
        "path": ["流动性受限资产释义(其它-投资监督)"],
        "models": [
            option_interpretation_paras(
                "流动性受限资产",
                table_config={
                    "multi": True,
                    "neglect_regs": [r"^[一二三四五六七八九十]、"],
                },
            ),
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
