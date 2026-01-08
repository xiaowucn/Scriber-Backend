"""
资管合同
"""

from remarkable.plugins.cgs.common.patterns_util import R_CONJUNCTION
from remarkable.predictor.common_pattern import NUMBER_CHAR_PATTERN, R_CN, R_COLON, R_NOT_SENTENCE_END
from remarkable.predictor.eltype import ElementClass

R_LIQUIDATION_LINE = "止损|平仓|清盘"

predictor_options = [
    {
        "path": ["产品名称"],
        "models": [
            {
                "name": "syllabus_based",
                "include_title": False,
                "extract_from": "same_type_elements",
                "inject_syllabus_features": [
                    r"__regex__名称",
                    r"__regex__基本情况__regex__名称$",
                ],
                "only_inject_features": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": r"(?P<content>[^。]*)",
                },
            },
            {
                "name": "para_match",
                "paragraph_pattern": (r"((资产管理|单一)计划的?)?名称[:：](?P<content>[^。]*)",),
            },
        ],
    },
    {
        "path": ["证券交易所释义(其它-投资监督)", "原文"],
        "models": [
            {
                "name": "trading_exchange_para_match",
                "paragraph_pattern": (r"交易所[:：](?P<content>.*)",),
                "neglect_regs": [r"期货交易所"],
            },
            {
                "name": "syllabus_based",
                "include_title": False,
                "inject_syllabus_features": [r"__regex__^释义$"],
                "only_inject_features": True,
                "table_model": "trading_exchange_kv",
                "table_config": {
                    "skip_empty_cell": True,
                    "feature_white_list": [r"证券交易所"],
                },
            },
        ],
    },
    {
        "path": ["期货交易所释义(其它-投资监督)", "原文"],
        "models": [
            {
                "name": "trading_exchange_kv",
            },
            {
                "name": "syllabus_based",
                "include_title": False,
                "inject_syllabus_features": [r"__regex__^释义$"],
                "only_inject_features": True,
                "ignore_syllabus_range": True,
                "table_model": "trading_exchange_kv",
                "table_config": {
                    "skip_empty_cell": True,
                    "feature_white_list": [
                        r"期货交易所",
                        r"证券/期货交易所",
                    ],
                },
                "extract_from": "same_type_elements",
                "paragraph_model": "trading_exchange_para_match",
                "para_config": {
                    "paragraph_pattern": (r"期货交易所[:：](?P<content>.*)",),
                },
            },
        ],
    },
    {
        "path": ["交易所释义(其它-投资监督)"],
        "models": [
            {
                "name": "syllabus_based",
                "include_title": False,
                "inject_syllabus_features": [r"__regex__^释义$"],
                "only_inject_features": True,
                "ignore_syllabus_range": True,
                "table_model": "trading_exchange_kv",
                "table_config": {
                    "skip_empty_cell": True,
                    "feature_white_list": [
                        r"<!(证券|期货))交易所",
                    ],
                },
                "extract_from": "same_type_elements",
                "paragraph_model": "trading_exchange_para_match",
                "para_config": {
                    "paragraph_pattern": (r"(?<!(证券|期货))交易所[:：](?P<content>.*)",),
                },
            },
        ],
    },
    {
        "path": ["投资范围(其它-投资监督)"],
        "models": [
            {
                # http://100.64.0.9:55816/scriber/#/project/remark/11328?projectId=130&treeId=165&fileId=2377&schemaId=129
                "name": "scope_investment_syllabus_based",
                "extract_from": "same_type_elements",
                "match_method": "similarity",
                "break_para_pattern": [
                    r"投资限制",
                    r"投资策略",
                ],
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        r".*[(（]\d+\.[A-Z]+[)）].*",
                    ],
                },
            },
            {
                "name": "scope_investment_middle",
                "use_syllabus_model": True,
                "top_greed": False,
                "include_top_anchor": False,
                "inject_syllabus_features": [
                    r"__regex__^基金的投资$__regex__^投资范围$",
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
            {
                "name": "scope_investment_middle",
                "top_default": True,
                "use_syllabus_model": True,
                "inject_syllabus_features": [
                    r"__regex__^基金的投资$__regex__^投资范围$",
                ],
                "top_anchor_ignore_regs": [
                    r"详见本合同",
                ],
                "bottom_anchor_ignore_regs": [
                    r"投资比例",
                ],
                "bottom_anchor_regs": [
                    r"投资比例[：:]?$",
                    r"投资范围的变更程序",
                    r"投资策略$",
                ],
            },
            {
                "name": "scope_investment_syllabus",
                "syllabus_black_list": [r"资产管理计划份额的登记"],
                "keep_parent": True,
                "multi_level": True,
                "include_title": False,
                "break_para_pattern": [
                    rf"投资比例为?[{R_COLON}]",
                ],
            },
        ],
    },
    {
        "path": ["投资比例(其它-投资监督)"],
        "post_process": "post_process_investment_ratio",
        "models": [
            {
                "name": "investment_ratio_syllabus",
                "keep_parent": True,
                "multi_level": True,
                "inject_syllabus_features": [
                    r"__regex__(资产管理计划)?的?投资(管理)?$__regex__(投资范围及比例|投资比例)",
                    r"__regex__(资产管理计划)?的?投资(管理)?$__regex__投资范围及比例__regex__资产配置比例$",
                    r"__regex__投资((比例限制)[与和]?)｛2｝",
                    r"__regex__资产配置比例$",
                    r"__regex__(资产管理计划)?的?投资(管理)?$__regex__本计划的投资比例",
                    r"__regex__资产管理计划的投资$__regex__本计划可开展证券回购投资__regex__投资比例",
                    r"__regex__(资产管理计划)?的?投资(管理)?$__regex__投资比例与投资限制__regex__投资比例与投资限制",
                ],
            },
        ],
    },
    {
        "path": ["投资策略(其它-投资监督)"],
        "models": [
            {
                "name": "middle_paras",
                "include_title": True,
                "use_syllabus_model": True,
                "include_top_anchor": False,
                "inject_syllabus_features": [
                    r"__regex__投资策略及投资比例",
                ],
                "top_anchor_regs": [
                    r"投资策略及投资比例",
                ],
                "bottom_anchor_regs": [
                    r"投资比例如下[：:]",
                ],
            },
            {
                "name": "middle_paras",
                "include_title": True,
                "use_syllabus_model": True,
                "include_top_anchor": False,
                "inject_syllabus_features": [
                    r"__regex__资产管理计划的投资",
                ],
                "top_anchor_regs": [
                    r"本计划的投资策略",
                ],
                "bottom_anchor_regs": [
                    r"本计划的投资比例",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__本计划的?投资策略",
                ],
            },
        ],
    },
    {
        "path": ["投资限制(其它-投资监督)"],
        "models": [
            {
                "name": "investment_restrictions_middle",
                "use_syllabus_model": True,
                "only_inject_features": True,
                "include_top_anchor": False,
                "inject_syllabus_features": [
                    r"__regex__投资((比例|限制|禁止)[与和]?)｛2｝",
                ],
                "top_anchor_regs": [
                    r"投资于股指期货仅以套期保值为目的",
                ],
                "bottom_anchor_regs": [
                    r"上述合同约定",
                ],
            },
            {
                "name": "investment_restrictions_middle",
                "use_syllabus_model": True,
                "only_inject_features": True,
                "include_top_anchor": False,
                "inject_syllabus_features": [
                    r"__regex__资产管理计划的投资",
                ],
                "top_anchor_regs": [
                    r"第.{,3}条本计划的投资限制",
                ],
                "bottom_anchor_regs": [
                    r"第.{,3}条投资禁止行为",
                ],
            },
            {
                "name": "investment_restrictions",
                "inject_syllabus_features": [
                    r"__regex__资产管理计划的投资__regex__本计划的投资限制",
                    r"__regex__投资限制及投资禁止行为$",
                    r"__regex__遵循以下限制$",
                    r"__regex__投资((比例|限制|禁止)[和及与]?){2}$",
                    r"__regex__((投资比例|投资限制|投资禁止)[和及与]?){2}$",
                ],
                "ignore_pattern": [r"不再受相关限制[:：]$"],
                "break_para_pattern": [
                    r"投资禁止(行为)?[:：]?$",
                    r"禁止行为[:：]?$",
                    r"资产管理计划财产禁止从事下列行为",
                ],
            },
        ],
    },
    {
        "path": ["预警线(其它-投资监督)"],
        "models": [
            {
                "name": "partial_text",
                "neglect_syllabus_regs": [r"预警止损机制风险"],
                "regs": [
                    rf"(将(计划)?份额净值|设置)(?P<dst>{R_NOT_SENTENCE_END}*?元(\/份)?)(设置)?为?预警线",
                    rf"预警线[为:：][{R_CN}【]*(?P<dst>{R_NOT_SENTENCE_END}*?元?(\/份)?)",
                    rf"预警线(设置)?(累计单位净值)?[为:：][{R_CN}【]*(?P<dst>[\d.]+元?(\/份)?)",
                    rf"本(单一|资产管理)?((集合)?计划|基金)([不未]设置?|无){R_NOT_SENTENCE_END}*预警{R_NOT_SENTENCE_END}*",
                ],
            },
        ],
    },
    {
        "path": ["预警线描述(其它-投资监督)"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__预警线.平仓线",
                ],
                "top_anchor_regs": [
                    r"预警线[为:：].*元",
                ],
                "top_anchor_content_regs": [
                    rf"预警线[为:：].*元([\(（]{R_NOT_SENTENCE_END}*[）\)])?[。，,.;；](?P<content>.*)"
                ],
                "bottom_anchor_regs": [
                    "平仓线[为:：]",
                ],
            },
            {
                "name": "partial_text",
                "multi_elements": True,
                "order_by_index": True,
                "regs": [
                    rf"预警线[为:：].*元([\(（]{R_NOT_SENTENCE_END}*[）\)])?[。，,.;；](?P<dst>.*)",
                    r"(?P<dst>.*份额净值[^。，,.;；(（]*?预警线.*)",
                ],
                "neglect_patterns": [
                    r"特别提示",
                    r"设置为预警线",
                    r"预警.*由.*负责(监控并)?执行",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "syllabus_black_list": [r"禁止行为$"],
                "ignore_pattern": [
                    r"预警线为",
                    rf"({R_LIQUIDATION_LINE})(机制|线|卖出)",
                    rf"(不设置?|无)((预警|{R_LIQUIDATION_LINE})[{R_CONJUNCTION}]?){{1,2}}",
                    r"计划持有(多个)?流通受限",
                ],
                "break_para_pattern": [
                    r"禁止行为[概包][括含][：:]",
                    r"禁止从事下列行为[：:]",
                    r"特别提示",
                    r"卖出过程中",
                    r"资产管理合同的((变更|终止|财产清算)[、与]?){3}",
                    r"预警.*由.*负责(监控并)?执行",
                    r"以上预警(卖出|平仓)",
                    r"^[^。]*?(根据|按照)(以上|上述)约定(进行平仓处理|采取的?措施)",
                ],
            },
        ],
    },
    {
        "path": ["止损线(其它-投资监督)"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": [rf"{R_LIQUIDATION_LINE}"],
                "neglect_syllabus_regs": [r"预警止损机制风险"],
                "regs": [
                    rf"[，,](?P<dst>{R_NOT_SENTENCE_END}*?元(\/份)?)为?({R_LIQUIDATION_LINE})线",
                    rf"(将(计划)?份额净值|设置)为?(?P<dst>{R_NOT_SENTENCE_END}*?元(\/份)?)(设置)?为?({R_LIQUIDATION_LINE})线",
                    rf"({R_LIQUIDATION_LINE})线(设置)?(累计单位净值)?[为:：][{R_CN}【]*(?P<dst>[\d.]+元?(\/份)?)",
                    rf"({R_LIQUIDATION_LINE})线为[{R_CN}【]*(?P<dst>{R_NOT_SENTENCE_END}*?元(\/份)?)",
                    rf"本(单一|资产管理)?((集合)?计划|基金)([不未]设置?|无){R_NOT_SENTENCE_END}*({R_LIQUIDATION_LINE}){R_NOT_SENTENCE_END}*",
                ],
            },
            {
                "name": "partial_text",
                "regs": [
                    rf"第.{{1,3}}条本计划的({R_LIQUIDATION_LINE})线[为:：][{R_CN}]*(?P<dst>[\d.]+元?(\/份)?)",
                ],
            },
            {
                "name": "syllabus_based",
                "only_inject_features": True,
                "inject_syllabus_features": [rf"__regex__预警线、({R_LIQUIDATION_LINE})线$"],
                "paragraph_model": "partial_text",
                "extract_from": "same_type_elements",
                "para_config": {
                    "regs": [
                        rf"[，,](?P<dst>{R_NOT_SENTENCE_END}*?元(\/份)?)为?止损线",
                        rf"(将(计划)?份额净值|设置)为?(?P<dst>{R_NOT_SENTENCE_END}*?元(\/份)?)(设置)?为?({R_LIQUIDATION_LINE})线",
                        rf"({R_LIQUIDATION_LINE})线为[{R_CN}]*(?P<dst>{R_NOT_SENTENCE_END}*?元(\/份)?)",
                        rf"({R_LIQUIDATION_LINE})线[为:：][{R_CN}]*(?P<dst>[\d.]+元?(\/份)?)",
                        rf"本(单一|资产管理)?(计划|基金)([不未]设置?|无){R_NOT_SENTENCE_END}*({R_LIQUIDATION_LINE}){R_NOT_SENTENCE_END}*",
                    ],
                },
            },
        ],
    },
    {
        "path": ["止损线描述(其它-投资监督)"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__预警止损机制",
                ],
                "include_bottom_anchor": True,
                "top_anchor_regs": [
                    r"当T日计划份额净值低于或等于止损线",
                ],
                "bottom_anchor_regs": [
                    r"本计划的预警、止损线由资产管理人负责监控并执行",
                ],
            },
            {
                "name": "partial_text",
                "multi_elements": True,
                "order_by_index": True,
                "regs": [
                    rf"({R_LIQUIDATION_LINE})线[为:：].*元([\(（]{R_NOT_SENTENCE_END}*[）\)])?[。，,.;；](?P<dst>.*?)[^。]*负责执行",
                    rf"({R_LIQUIDATION_LINE})线[为:：].*([\d.】]+|元)([\(（]{R_NOT_SENTENCE_END}*[）\)])?[。，,.;；](?P<dst>.*)",
                    r".*资产(全部)?变现后本?计划提前终止.*",
                    rf".*触发({R_LIQUIDATION_LINE})机制.*",
                    rf".*低于或等于({R_LIQUIDATION_LINE})线.*",
                ],
                "neglect_patterns": [
                    r"特别提示",
                    r"设置[为了](止损线|预警止损机制)",
                    r"预警线",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "remove_para_begin_number": True,
                "inject_syllabus_features": [
                    r"止损线及相应措施",
                    r"__regex__本集合计划的预警与止损机制__regex__止损机制",
                ],
                "syllabus_black_list": [r"禁止行为$"],
                "ignore_pattern": [
                    r"止损线(设置)?为",
                    r"预警线",
                    rf"预警([{R_CONJUNCTION}]止损)?(机制|线)",
                    rf"(不设置?|无)((预警|{R_LIQUIDATION_LINE})[{R_CONJUNCTION}]?){{1,2}}",
                    r"计划持有(多个)?流通受限",
                    r"资产管理有限公司",
                    r"资产管理计划资产管理合同",
                ],
                "break_para_pattern": [
                    r"设置[为了](止损线|预警止损机制)",
                    r"禁止行为[概包][括含][：:]",
                    r"禁止从事下列行为[：:]",
                    r"特别提示",
                    r"卖出过程中",
                    r"资产管理合同的((变更|终止|财产清算)[、与]?){3}",
                    r"止损.*由.*负责执行",
                    r"以上止损(卖出|平仓)",
                    r"^[^。]*?(根据|按照)(以上|上述)约定(进行平仓处理|采取的?措施)",
                ],
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__资产管理计划的投资",
                ],
                "include_top_anchor": False,
                "top_anchor_regs": [
                    r"第.{,3}条本计划的清盘线",
                ],
                "bottom_default": True,
                "bottom_anchor_regs": [
                    "^第.{,3}条",
                ],
            },
        ],
    },
    {
        "path": ["关联交易(其它-投资监督)"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__关联交易$",
                    r"__regex__关联交易决策及信息披露机制$",
                ],
                "break_para_pattern": [
                    r"授权并同意",
                ],
                "multi_level": True,
            },
        ],
    },
    {
        "path": ["越权交易(其它-投资监督)"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__越权(交易|投资)(的?((界定|处理)[与和及]?){1,2})?$",
                ],
                "skip_types": [ElementClass.STAMP.value],
            },
        ],
    },
    {
        "path": ["禁止行为(其它-投资监督)"],
        "models": [
            {
                "name": "middle_paras",
                "include_top_anchor": False,
                "top_anchor_regs": [
                    rf"((管理人|托管人|相关(从业)?人员)[{R_CONJUNCTION}]?){{1,3}}不得有下[列面]行为[：:]$",
                    r"投资应遵循以下投资禁止[：:]$",
                    r"资产管理计划财产禁止从事下列行为[：:]$",
                ],
                "bottom_anchor_regs": [
                    rf"((法律|行政法规|中国证监会)[{R_CONJUNCTION}]?){{1,3}}禁止的(其[他|它])?行为",
                    r"建仓期$",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": [r"投资限制"],
                "inject_syllabus_features": [
                    "__regex__不得有下[列面]行为[：:]$",
                ],
            },
        ],
    },
    {
        "path": ["基金的备案(其它-投资监督)"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    "__regex__资产管理计划的成立与备案__regex__(资产管理|单一)计划的成立与?备案",
                    "__regex__资产管理计划的成立与备案__regex__资产管理计划的备案及备案前投资",
                ],
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__集合计划的成立与备案__regex__集合计划成立的条件和日期",
                ],
                "include_bottom_anchor": True,
                "top_anchor_regs": [
                    r"报.*协会备案",
                ],
                "bottom_anchor_regs": [
                    r"设立完成前",
                ],
            },
        ],
    },
    {
        "path": ["调整期(其它-投资监督)"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": [
                    r"投资(比例|限制)超限的?处理(方式|流程)",
                    r"((资产配置比例|投资限制)[与和及]?){2}",
                    r"投资(限制|比例)$",
                    r"资产管理计划的建仓期",
                ],
                "regs": [
                    r"恢复交易(之日起)?的?(?P<dst>.*个(交易|工作)日)内.*?(调整至符合(相关)?要求|降至许可范围内)",
                    rf"(基金|资产)?管理人在(?P<dst>{NUMBER_CHAR_PATTERN}+个(交易|工作)日)内调整完毕",
                    rf"(基金|资产)?管理人.*((可出售|可转让|恢复|具备)(与|和|及|或|、|(或者))?){1, 3}交易(条件)?的?(?P<dst>{NUMBER_CHAR_PATTERN}+个(交易|工作)日)内(调整|将投资比例)",
                ],
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__基金的?投资__regex__投资的?限制$",
                    r"__regex__资产管理计划的?投资目标__regex__资产配置比例$",
                ],
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        r"恢复交易的?(?P<dst>.*个交易日)内.*?调整至符合(相关)?要求",
                        rf"(基金|资产)?管理人在(?P<dst>{NUMBER_CHAR_PATTERN}+个交易日)内调整完毕",
                        rf"(基金|资产)?管理人.*((可出售|可转让|恢复|具备)(与|和|及|或|、|(或者))?){1, 3}交易(条件)?的?(?P<dst>{NUMBER_CHAR_PATTERN}+个交易日)内(调整|将投资比例)",
                    ],
                },
            },
            {
                "name": "syllabus_based",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__被动超标",
                ],
                "extract_from": "same_type_elements",
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        r"恢复交易(之日起)?的?(?P<dst>.*个交易日)内.*?调整.?[以至](符合|满足).*要求",
                    ],
                },
            },
        ],
    },
    {
        "path": ["建仓期(其它-投资监督)"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    rf"建仓期为?[\u4e00-\u9fff]+(?P<dst>{R_NOT_SENTENCE_END}*[\d一二三四五六七八九十]+{R_NOT_SENTENCE_END}*个月)",
                    rf"本(集合|单一)?计划自?成立之日起(?P<dst>{R_NOT_SENTENCE_END}*[\d一二三四五六七八九十]+{R_NOT_SENTENCE_END}*个月).{{,2}}建仓期",
                    r"管理人自本计划成立之日起(?P<dst>.*)内使本计划的投资组合比例符合上述投资限制的约定",
                ],
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["产品风险等级(其它-投资监督)"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    rf"(?P<dst>本(资产管理)?计划的?风险评级评价为?{R_NOT_SENTENCE_END}*)",
                    rf"(?P<dst>本(集合)?(单一)?计划{R_NOT_SENTENCE_END}*风险{R_NOT_SENTENCE_END}*等级{R_NOT_SENTENCE_END}*)",
                    rf"(?P<dst>本(资产管理)?计划属于{R_NOT_SENTENCE_END}*风险{R_NOT_SENTENCE_END}*品种)",
                    rf"(?P<dst>本(资产管理)?计划的?风险等级为?{R_NOT_SENTENCE_END}*)",
                    r"(?P<dst>本(单一)?计划风险等级为属.*高风险等级)",
                    r"产品风险等级[:：](?P<dst>.*)",
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
