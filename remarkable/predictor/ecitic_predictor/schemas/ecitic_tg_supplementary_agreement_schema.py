"""
私募基金合同_补充协议
"""

from remarkable.predictor.common_pattern import R_NOT_SENTENCE_END
from remarkable.predictor.ecitic_predictor.schemas import R_BOTTOM_ANCHOR_REGS_BASE, R_CHANGE_FLAGS
from remarkable.predictor.eltype import ElementClass

R_CONTRACT = r"[《\(（]?基金合同[\)）》]?"

R_BOTTOM_ANCHOR_REGS = [
    *R_BOTTOM_ANCHOR_REGS_BASE,
    rf"{R_CONTRACT}规定的专用术语",
    r"视为同意前述变更",
    rf"同意本次{R_NOT_SENTENCE_END}变更",
]


option_interpretation = {
    "name": "syllabus_based",
    "inject_syllabus_features": [
        r"__regex__自本协议的变更执行日起.《基金合同》第【.】部分增加(如下内容|下述约定)",
    ],
    "extract_from": "same_type_elements",
    "only_inject_features": True,
    "table_model": "table_kv",
    "table_config": {
        "use_complete_table": True,
        "skip_empty_cell": True,
    },
}


predictor_options = [
    {
        "path": ["产品名称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    r"(?P<dst>.*)基金合同",
                    r"(关于)?(?P<dst>.*投资基金)",
                    r"关于(?P<dst>.*)变更.*(通知|意见)函",
                    r"关于(?P<dst>.*)",
                ],
                "page_range": [0],
                "model_alternative": True,
                "target_element": [ElementClass.PARAGRAPH.value],
                "neglect_patterns": [
                    r"^根据.*",
                ],
            }
        ],
    },
    {
        "path": ["证券交易所释义(其它-投资监督)"],
        "models": [
            {
                "name": "trading_exchange_kv",
            },
            {
                "name": "trading_exchange_syllabus",
            },
        ],
    },
    {
        "path": ["期货交易所释义(其它-投资监督)"],
        "models": [
            {
                "name": "trading_exchange_kv",
            },
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
                "name": "supplementary_agreement_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__基金变更后的?投资范围为",
                    rf"__regex__{R_CONTRACT}.*十二.*二.*(增加|新增)如下投资标的",
                ],
                "break_para_pattern": R_BOTTOM_ANCHOR_REGS,
            },
            {
                "name": "supplementary_agreement_elt_v2",
                "segmentation_regs": [
                    r"上述内容变更如下[：:]",
                    r"[(（]?[\d一二三四五六七八九十]+.投资范围",
                ],
                "break_para_pattern": R_BOTTOM_ANCHOR_REGS,
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["投资策略(其它-投资监督)"],
        "models": [
            {
                "name": "investment_restrictions_middle",
                "include_top_anchor": False,
                "top_greed": False,
                "top_anchor_range_regs": [
                    r"上述内容变更如下[：:]",
                ],
                "top_anchor_regs": [
                    r"[(（]?[\d一二三四五六七八九十]+.投资策略",
                ],
                "bottom_anchor_regs": [
                    r"[(（]?[\d一二三四五六七八九十]+.投资限制",
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
                "name": "investment_restrictions_middle",
                "use_top_crude_neighbor": False,
                "top_greed": False,
                "include_top_anchor": False,
                "top_anchor_regs": [
                    rf"{R_CONTRACT}.*十二.*五.*(增加|新增)如下约定[：:]",
                ],
                "bottom_anchor_regs": R_BOTTOM_ANCHOR_REGS,
            },
            {
                "name": "investment_restrictions_middle",
                "use_top_crude_neighbor": False,
                "top_greed": False,
                "include_bottom_anchor": True,
                "skip_merged_para": True,
                "top_anchor_range_regs": [
                    R_CHANGE_FLAGS,
                ],
                "top_anchor_regs": ["本基金的投资组合将遵循以下限制.*[：:]$"],
                "bottom_anchor_regs": [
                    r"法律法规另有规定的从其规定",
                    r"托管人对本?基金的?投资的?监督自本?基金成立之日起开始",
                    *R_BOTTOM_ANCHOR_REGS,
                ],
                "bottom_anchor_content_regs": [
                    r"(?P<content>.*从其规定)",
                    r"(?P<content>.*基金成立之日起开始)",
                ],
            },
            {
                "name": "investment_restrictions_middle",
                "use_top_crude_neighbor": False,
                "top_greed": False,
                "include_top_anchor": False,
                "skip_merged_para": True,
                "top_anchor_range_regs": [
                    rf"{R_CONTRACT}.*十二.*五",
                ],
                "top_anchor_regs": [
                    R_CHANGE_FLAGS,
                ],
                "bottom_anchor_regs": R_BOTTOM_ANCHOR_REGS,
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
                    "include_top_anchor": False,
                    "include_bottom_anchor": True,
                    "top_greed": False,
                    "top_anchor_regs": [
                        r"上述内容变更如下[:：]",
                    ],
                    "bottom_anchor_regs": [
                        r"预警线",
                    ],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        r"本基金不设置预警(线)?和平仓(机制|线)",
                        r"预警线为?(?P<dst>[-—–]?[\d\.]+元)",
                    ],
                },
            },
            {
                "name": "partial_text",
                "regs": [
                    r"本基金不设置预警(线)?和平仓(机制|线)",
                    r"预警线为?(?P<dst>[-—–]?[\d\.]+元)",
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
                    "include_top_anchor": False,
                    "include_bottom_anchor": True,
                    "top_greed": False,
                    "top_anchor_regs": [r"上述内容变更如下"],
                    "bottom_anchor_regs": [r"当(基金)?管理人.*进行清算"],
                },
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"当(基金)?(管理人|托管人).*基金触及预警线.*"],
                },
            },
        ],
    },
    {
        "path": ["平仓线(其它-投资监督)"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "include_top_anchor": False,
                    "include_bottom_anchor": True,
                    "top_greed": False,
                    "top_anchor_regs": [
                        r"上述内容变更如下[:：]",
                    ],
                    "bottom_anchor_regs": [
                        r"平仓线",
                    ],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        r"本基金不设置预警(线)?和平仓(机制|线)",
                        r"预警线为?(?P<dst>[-—–]?[\d\.]+元)",
                    ],
                },
            },
            {
                "name": "partial_text",
                "regs": [
                    r"本基金不设置预警(线)?和平仓(机制|线)",
                    r"平仓线为?(?P<dst>-?[\d\.]+元)",
                ],
            },
        ],
    },
    {
        "path": ["平仓线描述(其它-投资监督)"],
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
                        rf"(平仓|止损)线为.*元([\(（]{R_NOT_SENTENCE_END}*[）\)])?[。，,.;；](?P<dst>.*?)[^。]*负责执行",
                        rf"(平仓|止损)线为.*元([\(（]{R_NOT_SENTENCE_END}*[）\)])?[。，,.;；](?P<dst>.*)",
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
        ],
    },
    {
        "path": ["关联交易(其它-投资监督)"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["越权交易(其它-投资监督)"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["禁止行为(其它-投资监督)"],
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
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "include_top_anchor": False,
                    "include_bottom_anchor": True,
                    "top_anchor_regs": [r"上述内容变更如下"],
                    "bottom_anchor_regs": [r"合同的?变更"],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        r"恢复交易的?(?P<dst>.*个交易日)内.*?调整至符合(相关)?要求",
                        r"(基金|资产)管理人在(?P<dst>\d+个交易日)内调整完毕",
                        r"(基金|资产)管理人.*((可出售|可转让|恢复)(与|和|及|或|、|(或者))?){1,3}交易的?(?P<dst>\d+个交易日)内调整完毕",
                    ],
                },
            },
            {
                "name": "partial_text",
                "regs": [
                    r"恢复交易的?(?P<dst>.*个交易日)内.*?调整至符合(相关)?要求",
                    r"(基金|资产)管理人在(?P<dst>\d+个交易日)内调整完毕",
                    r"(基金|资产)管理人.*((可出售|可转让|恢复)(与|和|及|或|、|(或者))?){1,3}交易的?(?P<dst>\d+个交易日)内调整完毕",
                ],
            },
        ],
    },
    {
        "path": ["产品风险等级(其它-投资监督)"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"[^“\"]*基金.*风险等级[^”\"]*"],
            },
        ],
    },
    {
        "path": ["建仓期(其它-投资监督)"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_top_crude_neighbor": False,
                    "top_greed": False,
                    "top_anchor_regs": [r"投资限制$"],
                    "bottom_anchor_regs": [
                        r"对本基金的投资的监督自本基金成立之日起开始",
                    ],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        r"自本基金成立之日起(?P<dst>\d+个[年月日])内",
                    ],
                },
            },
        ],
    },
    {
        "path": ["债权类资产释义(其它-投资监督)"],
        "models": [
            option_interpretation,
        ],
    },
    {
        "path": ["股权类资产释义(其它-投资监督)"],
        "models": [
            option_interpretation,
        ],
    },
    {
        "path": ["期货和衍生品持仓合约价值释义(其它-投资监督)"],
        "models": [
            option_interpretation,
        ],
    },
    {
        "path": ["期货和衍生品账户权益释义(其它-投资监督)"],
        "models": [
            option_interpretation,
        ],
    },
    {
        "path": ["已投资产释义(其它-投资监督)"],
        "models": [
            option_interpretation,
        ],
    },
    {
        "path": ["同一资产释义(其它-投资监督)"],
        "models": [
            option_interpretation,
        ],
    },
    {
        "path": ["债券评级规则释义(其它-投资监督)"],
        "models": [
            option_interpretation,
        ],
    },
    {
        "path": ["利率债释义(其它-投资监督)"],
        "models": [
            option_interpretation,
        ],
    },
    {
        "path": ["信用债释义(其它-投资监督)"],
        "models": [
            option_interpretation,
        ],
    },
    {
        "path": ["流动性受限资产释义(其它-投资监督)"],
        "models": [
            option_interpretation,
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
