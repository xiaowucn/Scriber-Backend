"""华夏营销部-招募说明书V1"""

from remarkable.predictor.common_pattern import R_NOT_SENTENCE_END
from remarkable.predictor.eltype import ElementClass

R_FUND_NAME_FEEDER = r"华夏.+基金.*联接基金([(（]?[a-zA-Z]+[）)])?"
R_FUND_NAME = r"华夏.+(基金中)?基金([(（]?[a-zA-Z]+[）)])?"

R_REGS_A = [
    # （华夏MSCI中国A50互联互通ETF联接A）基金产品资料概要
    r"(联接A|A类基金|债券A|混合A|[(（]?[a-zA-Z]+[）)])A[^C]*产品资料概要",
    rf"[(（]华夏{R_NOT_SENTENCE_END}*A[）)]",
]

ELEMENT_NEARBY_PRODUCT_A = {
    "elements_nearby": {
        "regs": R_REGS_A,
        "amount": 60,
        "step": -1,
    },
}

R_REGS_C = [
    # （华夏MSCI中国A50互联互通ETF联接A）基金产品资料概要
    r"(联接C|C类基金|债券C|混合C|[(（]?[a-zA-Z]+[）)])C[^A]*产品资料概要",
    rf"[(（]华夏{R_NOT_SENTENCE_END}*C[）)]",
]

ELEMENT_NEARBY_PRODUCT_C = {
    "elements_nearby": {
        "regs": R_REGS_C,
        "amount": 60,
        "step": -1,
    },
}

ELEMENT_NEARBY_PRODUCT_NO_TYPE = {
    "elements_nearby": {
        "regs": [
            r"产品资料概要",
        ],
        "amount": 60,
        "step": -1,
    },
}

SCOPE_INVESTMENT = {
    "regs": [
        # http://100.64.0.9:55819/scriber/#/project/remark/10386?treeId=75&fileId=1534&schemaId=4
        # 表格识别问题兼容
        r"(?P<dst>.*?纳入投资范围.)",
        r"(?P<dst>.*?本基金可根据法律法规的规定[^。]*)",
        r"(?P<dst>.*?基金可[根依]据相关法律法规和《基金合同》的?约定.参与融资业务.)",
        r"(?P<dst>.*?)[^。]*(投资于?标的指数成份股[和、与及]备选成份股的比例|投资(组合)?比例)",
        r"(?P<dst>.*或中国证监会允许基金投资的其他金融工具。)",
        r"(?P<dst>.*主要投资于.*)",
    ],
    "neglect_regs": [
        r"主要投资策略包括",
    ],
}
PROPORTION_INVESTMENT = {
    "regs": [
        r"(?P<dst>[^。]*基金可[根依]据相关法律法规和《基金合同》的?约定.*)",
        r"(?P<dst>[^。]*(投资于?标的指数成份股[和、与及]备选成份股的比例|投资(组合)?比例).*)",
        r"(?P<dst>.*?)[^。]*投资策略",
        r"(?P<dst>[^。]*投资于[^。]*比例.*)",
    ]
}

predictor_options = [
    {
        "path": ["001基金名称"],
        "models": [
            {
                "name": "middle_paras",
                "page_range": [0],
                "top_anchor_regs": [
                    r"^华夏",
                ],
                "bottom_anchor_regs": [r"招募说明书"],
                "top_anchor_content_regs": [
                    r"(?P<content>^华夏.*)",
                ],
                "bottom_anchor_content_regs": [
                    r"(?P<content>.*)招募说明书",
                ],
                "include_bottom_anchor": True,
            },
            {
                "name": "auto",
                "page_range": [0],
                "use_answer_pattern": False,
                "custom_regs": [
                    rf"(?P<dst>{R_FUND_NAME_FEEDER})",
                    rf"(?P<dst>{R_FUND_NAME})",
                ],
            },
            {
                "name": "fund_name",
                "page_range": [0],
                "use_answer_pattern": False,
                "regs": [
                    # rf"(?P<dst>{R_FUND_NAME_FEEDER})",
                    # rf"(?P<dst>{R_FUND_NAME})",
                    r"(?P<dst>华夏.*)",
                ],
            },
        ],
    },
    {
        "path": ["002管理人"],
        "models": [
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["003托管人"],
        "models": [
            {
                "name": "auto",
                "regs": [r"[:：](?P<dst>.*)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["004基金名称"],
        "models": [
            {
                "name": "auto",
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    rf"(?P<dst>{R_FUND_NAME_FEEDER})([(（]以下简称)",
                    rf"(?P<dst>{R_FUND_NAME})([(（]以下简称)",
                    rf"(?P<dst>{R_FUND_NAME_FEEDER})",
                    rf"(?P<dst>{R_FUND_NAME})",
                ],
            },
        ],
    },
    {
        "path": ["005基金名称"],
        "models": [
            {
                "name": "fixed_position",
                "pages": [1],
                "target_element": [ElementClass.PAGE_HEADER.value],
                "regs": [r"(?P<dst>.*)招募说明书"],
            },
            {
                "name": "auto",
                "model_alternative": True,
                "target_element": [ElementClass.PAGE_HEADER.value],
            },
        ],
    },
    {
        "path": ["006基金名称"],
        "models": [
            {"name": "auto", "model_alternative": True, "regs": [r"(?P<dst>华夏[^。]*)"]},
        ],
    },
    {
        "path": ["007管理人"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    rf"管理人.*[:：]指(?P<dst>{R_NOT_SENTENCE_END}*)",
                ],
            },
        ],
    },
    {
        "path": ["008托管人"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    rf"托管人.*[:：]指(?P<dst>{R_NOT_SENTENCE_END}*)",
                ],
            },
        ],
    },
    {
        "path": ["009基金名称"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    r"基金合同》[:：]指《(?P<dst>.*?)基金合同",
                ],
            },
        ],
    },
    {
        "path": ["010基金名称"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    r"托管协议.*[<《](?P<dst>[^》>]*)托管协议",
                ],
            },
        ],
    },
    {
        "path": ["011基金名称"],
        "models": [
            {
                "name": "auto",
                "use_answer_pattern": False,
                "regs": [
                    r"[<《](?P<dst>[^》>]*基金([(（][a-zA-Z]+[）)])?)基金招募说明书",
                    r"[<《](?P<dst>[^》>]*)招募说明书",
                ],
            },
        ],
    },
    {
        "path": ["012基金名称"],
        "models": [
            {
                "name": "auto",
                "use_answer_pattern": False,
                "regs": [
                    r"[<《](?P<dst>[^》>]*基金([(（][a-zA-Z]+[）)])?)基金产品",
                    r"[<《](?P<dst>[^》>]*)产品",
                ],
            },
        ],
    },
    {
        "path": ["013基金名称"],
        "models": [
            {
                "name": "auto",
                "use_answer_pattern": False,
                "regs": [
                    r"[<《](?P<dst>[^》>]*基金([(（][a-zA-Z]+[）)])?)集中申购期",
                    r"[<《](?P<dst>[^》>]*基金([(（][a-zA-Z]+[）)])?)基金份额",
                    r"[<《](?P<dst>[^》>]*)份额",
                ],
            },
        ],
    },
    {
        "path": ["014管理人"],
        "models": [
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["015基金经理"],
        "models": [
            {
                "name": "syllabus_based",
                "include_title": False,
                "inject_syllabus_features": [r"__regex__基金经理"],
                "syllabus_black_list": [
                    r"主要职权",
                    r"承诺",
                ],
                "one_result_per_feature": False,
                "only_inject_features": True,
                "paragraph_model": "partial_text",
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4123
                "skip_merged_para": True,
                "para_config": {
                    "use_answer_pattern": False,
                    "multi_elements": True,
                },
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["016基金经理介绍"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "syllabus_black_list": [
                    r"主要职权",
                    r"承诺",
                ],
                "one_result_per_feature": False,
                "inject_syllabus_features": [r"__regex__基金经理"],
                "only_inject_features": True,
            },
            {
                "name": "auto",
                "multi_elements": True,
            },
        ],
    },
    {
        "path": ["017托管人"],
        "models": [
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["018运作方式"],
        "models": [
            {
                "name": "middle_paras",
                "include_bottom_anchor": True,
                "top_anchor_range_regs": [
                    r"运作方式[:：].*开放式",
                ],
                "top_anchor_regs": [
                    r"基金份额设置.*持有期.?$",
                ],
                "bottom_anchor_regs": [
                    r"提出赎回申请",
                ],
            },
            {
                "name": "middle_paras",
                "include_top_anchor": False,
                "top_anchor_range_regs": [
                    r"运作方式[:：].*开放式",
                ],
                "top_anchor_regs": [
                    r"运作期.?$",
                    r"持有期.?$",
                ],
                "bottom_anchor_regs": [
                    r"(运作期到期日|转型日之后).*赎回申请",
                    r"开放日及开放时间$",
                ],
            },
            {
                # 定期开发
                "name": "middle_paras",
                "include_top_anchor": False,
                "include_bottom_anchor": True,
                "top_anchor_range_regs": [
                    r"运作方式[:：].*定期开放式",
                ],
                "top_anchor_regs": [
                    r"运作方式[:：].*定期开放式",
                ],
                "bottom_anchor_regs": [
                    r"开放期的具体时间以(基金)?管理人届时公告为准",
                ],
                "bottom_anchor_content_regs": ["(?P<content>.*?开放期的具体时间以(基金)?管理人届时公告为准.)"],
            },
            {
                "name": "auto",
                "custom_regs": [
                    r"运作方式[:：](?P<dst>[^。]*)",
                ],
            },
        ],
    },
    {
        "path": ["019认购费率"],
        "models": [
            {
                "name": "syllabus_based",
                "include_title": False,
                "table_model": "table_titles",
                "inject_syllabus_features": [
                    r"__regex__认购费用",
                ],
                "table_config": {
                    "multi_elements": True,
                    "first_row_as_title": True,
                    "feature_white_list": [
                        rf"认购费.*如下{R_NOT_SENTENCE_END}*?[:：]",
                    ],
                },
            },
            {
                "name": "syllabus_based",
                "include_title": False,
                "shape_as_table": True,
                "force_use_all_elements": True,
                "table_model": "shape_titles",
                "table_config": {
                    "regs": [
                        rf"认购费.*如下{R_NOT_SENTENCE_END}*?[:：]",
                    ],
                },
            },
        ],
    },
    {
        "path": ["020运作方式"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "include_title": True,
                    "inject_syllabus_features": [
                        r"__regex__封闭期",
                    ],
                    "top_anchor_regs": [
                        r"封闭期",
                    ],
                    "bottom_anchor_regs": [
                        r"开放日及开放时间$",
                    ],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "regs": [
                        r".*进入下一个封闭期.*",
                        rf".*进入开放期.*具体时间{R_NOT_SENTENCE_END}*",
                    ],
                },
            },
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r"其他情形的影响因素消除之日起的下一个工作日"],
                "include_break_para": True,
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["021申购费率"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "table_regarded_as_paras": True,
                "top_anchor_regs": [
                    r"申购费.*如下[:：]",
                ],
                "bottom_anchor_regs": [
                    r"赎回费",
                ],
                "include_top_anchor": False,
                "middle_content_regs": [r"\d[、）)](?P<content>.+)", r"(?P<content>.+)"],
            },
            {
                "name": "auto",
                "multi": True,
            },
        ],
    },
    {
        "path": ["022赎回费率"],
        "pick_answer_strategy": "all",
        "models": [
            {
                "name": "syllabus_based",
                "include_title": False,
                "inject_syllabus_features": [
                    r"__regex__((赎回费|申购费)[和与]?){2}__regex__赎回费用",
                    r"__regex__((赎回费|申购费)[和与]?){2}$",
                ],
                "only_inject_features": True,
                "table_model": "table_titles",
                "table_config": {
                    "multi_elements": True,
                    "first_row_as_title": True,
                    "feature_white_list": [
                        r"赎回费.*如下[:：]",
                        r"赎回费全部归于基金资产",
                        r"赎回费用",
                    ],
                },
            },
            {
                "name": "partial_text",
                "neglect_patterns": [
                    r"不收取赎回费",
                ],
            },
        ],
    },
    {
        "path": ["023投资目标"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["024投资范围"],
        "models": [
            {
                "name": "middle_paras",
                "include_top_anchor": False,
                "top_anchor_regs": [
                    r"投资范围$",
                ],
                "bottom_anchor_regs": [
                    rf"投资于{R_NOT_SENTENCE_END}*比例",
                    r"投资标的指数",
                    r"投资(组合)?比例",
                    r"基金的?比例",
                    r"投资策略",
                ],
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["025投资比例"],
        "models": [
            {
                "name": "middle_paras",
                "top_anchor_regs": [
                    r"比例为[：:]",
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4122
                    rf"投资于{R_NOT_SENTENCE_END}*比例",
                    r"投资标的指数",
                ],
                "bottom_anchor_regs": [
                    r"投资策略$",
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4314
                    r"首次发售募集资金投资的?(资产支持证券|基础设施项目)",
                ],
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["026投资策略"],
        "models": [
            {
                "name": "middle_paras",
                "inject_syllabus_features": [r"__regex__投资策略$"],
                "use_syllabus_model": True,
                "top_default": True,
                "bottom_greed": True,
                "table_regarded_as_paras": True,
                "bottom_anchor_regs": [
                    r"^未来",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__投资策略$"],
                "break_para_pattern": [r"^未来"],
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["027投资限制"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": False,
                "top_anchor_regs": [
                    r"限制[:：]",
                ],
                "bottom_anchor_regs": [r"合同生效"],
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": True,
                "top_default": True,
                "bottom_anchor_regs": [r"合同生效"],
            },
        ],
    },
    {
        "path": ["028业绩比较基准"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    r"比较基准[为:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["029估值对象"],
        "models": [
            {
                "name": "auto",
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["030估值原则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["031估值方法"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__估值方法$",
                ],
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["032收益分配原则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__基金收益分配.*原则",
                ],
            },
        ],
    },
    {
        "path": ["033管理费率"],
        "models": [
            {
                "name": "table_titles",
                "feature_white_list": [
                    r"管理费率",
                ],
            },
            {
                "name": "auto",
                "regs": [r"管理费.*?(?P<dst>[\d\.]+[%％])"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["034管理费率"],
        "models": [
            {
                "name": "syllabus_based",
                "include_title": False,
                "skip_merged_para": True,
                "only_inject_features": True,
                "inject_syllabus_features": [r"__regex__((计提方法|计提标准|支付方式)[、和与及]?){1,3}__regex__管理费"],
                "break_para_pattern": [r"托管费"],
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        r"[H][＝=][E]×(?P<dst>[\d\.]+[%％])[÷/]",
                        r"[B][＝=][A]×(?P<dst>[\d\.]+[%％])[÷/]",
                    ],
                },
            },
        ],
    },
    {
        "path": ["035托管费率"],
        "models": [
            {
                "name": "auto",
                "regs": [r"托管费.*?(?P<dst>[\d\.]+[%％])"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["036托管费率"],
        "models": [
            {
                "name": "auto",
                "regs": [r"H=.*?(?P<dst>[\d\.]+[%％])"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["037销售服务费"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [r"其中.(?P<dst>.*?类.*?销售服务费[^。]*)"],
            },
        ],
    },
    {
        "path": ["038投资范围"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>.*?根据(相关)?法律法规[^。]*)",
                    r"(?P<dst>.*?包括国内依法发行[^。]*)",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__((市场|行业|资产)[和及、，]?){2,3}的?流动性风险评估$",
                ],
            },
        ],
    },
    {
        "path": ["039基金名称"],
        "models": [
            {
                "name": "auto",
                "target_element": [ElementClass.PARAGRAPH.value],
                "neglect_patterns": [
                    r"[:：《》]",
                    r"的批复",
                ],
                "regs": [
                    rf"(?P<dst>{R_FUND_NAME_FEEDER}).*?基金产品资料概要",
                    rf"(?P<dst>{R_FUND_NAME}).*?基金产品资料概要",
                ],
            },
            {
                "name": "auto",
                "target_element": [ElementClass.PARAGRAPH.value],
                "neglect_patterns": [
                    r"[:：《》]",
                    r"的批复",
                ],
                "regs": [
                    rf"(?P<dst>{R_FUND_NAME})",
                ],
                "elements_nearby": {
                    "regs": R_REGS_A,
                    "amount": 60,
                    "step": 1,
                },
            },
            {
                "name": "fund_name",
                "target_element": [ElementClass.PARAGRAPH.value],
                "neglect_patterns": [
                    r"[:：《》]",
                    r"的批复",
                ],
                "regs": [
                    r"(?P<dst>华夏.*)[(（]华夏",
                    r"(?P<dst>华夏.*)",
                ],
                "follow_paras_patterns": [
                    r"产品资料概要",
                    r"联接基金$",
                ],
            },
        ],
    },
    {
        "path": ["040管理人"],
        "models": [
            {
                "name": "table_kv",
                "title_patterns": [
                    r"产品概况",
                ],
                **ELEMENT_NEARBY_PRODUCT_A,
            },
            {
                "name": "table_kv",
                "title_patterns": [
                    r"产品概况",
                ],
                **ELEMENT_NEARBY_PRODUCT_NO_TYPE,
            },
        ],
    },
    {
        "path": ["041托管人"],
        "models": [
            {
                "name": "table_kv",
                "keep_dummy": True,
                "feature_black_list": [r"__regex托管人"],
                "regs": [
                    r"托管人[:：]?(?P<dst>.*)",
                ],
                **ELEMENT_NEARBY_PRODUCT_A,
            },
            {
                "name": "table_kv",
                "keep_dummy": True,
                "feature_black_list": [r"__regex托管人"],
                "regs": [
                    r"托管人[:：]?(?P<dst>.*)",
                ],
                **ELEMENT_NEARBY_PRODUCT_NO_TYPE,
            },
        ],
    },
    {
        "path": ["042基金经理"],
        "models": [
            {
                "name": "table_kv",
                "keep_dummy": True,
                "multi": True,
                "row_pattern": [
                    r"基金经理",
                ],
                "content_pattern": [
                    r"(?P<dst>.*)",
                ],
                **ELEMENT_NEARBY_PRODUCT_A,
            },
            {
                "name": "table_kv",
                "keep_dummy": True,
                "multi": True,
                "row_pattern": [
                    r"基金经理",
                ],
                "content_pattern": [
                    r"(?P<dst>.*)",
                ],
                **ELEMENT_NEARBY_PRODUCT_NO_TYPE,
            },
        ],
    },
    {
        "path": ["043投资目标"],
        "models": [
            {
                "name": "table_kv",
                **ELEMENT_NEARBY_PRODUCT_A,
            },
            {
                "name": "table_kv",
                **ELEMENT_NEARBY_PRODUCT_NO_TYPE,
            },
        ],
    },
    {
        "path": ["044投资范围"],
        "models": [
            {
                "name": "table_kv",
                "feature_white_list": [
                    r"主要投资策略",
                ],
                "only_matched_value": True,
                "multi": True,
                **SCOPE_INVESTMENT,
                **ELEMENT_NEARBY_PRODUCT_A,
            },
            {
                "name": "table_kv",
                "feature_white_list": [
                    r"主要投资策略",
                ],
                "only_matched_value": True,
                "multi": True,
                **SCOPE_INVESTMENT,
                **ELEMENT_NEARBY_PRODUCT_NO_TYPE,
            },
        ],
    },
    {
        "path": ["045投资比例"],
        "models": [
            {
                "name": "cell_partial_text",
                "filter_by": "col",
                "regs": [
                    r"(?P<dst>[^，。]*投资(组合)?比例为.*?。)(主要)?投资策略",
                    r"(?P<dst>[^，。]*的比例不低于本基金资产的.*?。)(主要)?投资策略",
                ],
                **ELEMENT_NEARBY_PRODUCT_A,
            },
            {
                "name": "table_kv",
                "only_matched_value": True,
                # http://100.64.0.9:55819/scriber/#/project/remark/10386?projectId=75&treeId=75&fileId=1534&schemaId=4&schemaKey=057%E6%8A%95%E8%B5%84%E6%AF%94%E4%BE%8B
                # 由于跨页合并的问题，在find_kv_pairs时，会匹配到最后一个，导致无法匹配到正则，故需要多行匹配
                "multi": True,
                "neglect_regs": [
                    r"投资策略",
                ],
                **PROPORTION_INVESTMENT,
                **ELEMENT_NEARBY_PRODUCT_A,
            },
            {
                "name": "table_tuple",
                "feature_black_list": [
                    r"__regex__策略|不超过",
                ],
                **ELEMENT_NEARBY_PRODUCT_A,
            },
            {
                "name": "table_kv",
                "only_matched_value": True,
                "multi": True,
                "feature_white_list": [
                    r"主要投资策略",
                ],
                **PROPORTION_INVESTMENT,
                **ELEMENT_NEARBY_PRODUCT_A,
            },
            {
                "name": "cell_partial_text",
                "filter_by": "col",
                "regs": [
                    r"(?P<dst>[^，。]*投资(组合)?比例为.*?。)(主要)?投资策略",
                    r"(?P<dst>[^，。]*的比例不低于本基金资产的.*?。)(主要)?投资策略",
                ],
                **ELEMENT_NEARBY_PRODUCT_NO_TYPE,
            },
            {
                "name": "table_kv",
                "only_matched_value": True,
                # http://100.64.0.9:55819/scriber/#/project/remark/10386?projectId=75&treeId=75&fileId=1534&schemaId=4&schemaKey=057%E6%8A%95%E8%B5%84%E6%AF%94%E4%BE%8B
                # 由于跨页合并的问题，在find_kv_pairs时，会匹配到最后一个，导致无法匹配到正则，故需要多行匹配
                "multi": True,
                "neglect_regs": [
                    r"投资策略",
                ],
                **PROPORTION_INVESTMENT,
                **ELEMENT_NEARBY_PRODUCT_NO_TYPE,
            },
            {
                "name": "table_tuple",
                "feature_black_list": [
                    r"__regex__策略|不超过",
                ],
                **ELEMENT_NEARBY_PRODUCT_NO_TYPE,
            },
        ],
    },
    {
        "path": ["046业绩比较基准"],
        "models": [
            {
                "name": "table_kv",
                "regs": [
                    r"(?P<dst>[^。:：]*[-+×].*?。)",
                ],
                **ELEMENT_NEARBY_PRODUCT_A,
            },
            {
                "name": "table_kv",
                "regs": [
                    r"(?P<dst>[^。:：]*[-+×].*?。)",
                ],
                **ELEMENT_NEARBY_PRODUCT_NO_TYPE,
            },
        ],
    },
    {
        "path": ["047认购费率"],
        "models": [
            {
                "name": "row_match",
                "keep_dummy": True,
                "row_pattern": [
                    r"认购费",
                ],
                "content_pattern": [
                    r"(?P<dst>.*)",
                ],
                "multi": True,
                **ELEMENT_NEARBY_PRODUCT_A,
            },
            {
                "name": "partial_text",
                "multi": True,
                **ELEMENT_NEARBY_PRODUCT_A,
            },
            {
                "name": "row_match",
                "keep_dummy": True,
                "row_pattern": [
                    r"认购费",
                ],
                "content_pattern": [
                    r"(?P<dst>.*)",
                ],
                "multi": True,
                **ELEMENT_NEARBY_PRODUCT_NO_TYPE,
            },
            {
                "name": "partial_text",
                "multi": True,
                **ELEMENT_NEARBY_PRODUCT_NO_TYPE,
            },
        ],
    },
    {
        "path": ["048申购费率"],
        "models": [
            {
                "name": "row_match",
                "keep_dummy": True,
                "row_pattern": [
                    r"申购费",
                ],
                "neglect_row_pattern": [
                    r"前端",
                ],
                "content_pattern": [
                    r"(?P<dst>.*)",
                ],
                "multi": True,
                **ELEMENT_NEARBY_PRODUCT_A,
            },
            {
                "name": "partial_text",
                "multi": True,
                "regs": [r"(?P<dst>申购赎回.*收取佣金)"],
                **ELEMENT_NEARBY_PRODUCT_A,
            },
            {
                "name": "row_match",
                "keep_dummy": True,
                "row_pattern": [
                    r"申购费",
                ],
                "neglect_row_pattern": [
                    r"前端",
                ],
                "content_pattern": [
                    r"(?P<dst>.*)",
                ],
                "multi": True,
                **ELEMENT_NEARBY_PRODUCT_NO_TYPE,
            },
            {
                "name": "partial_text",
                "multi": True,
                "regs": [r"(?P<dst>申购赎回.*收取佣金)"],
                **ELEMENT_NEARBY_PRODUCT_NO_TYPE,
            },
        ],
    },
    {
        "path": ["049管理费率"],
        "models": [
            {
                "name": "table_kv",
                "regs": [
                    r"(?P<dst>[\d\.]+[%％])",
                ],
                **ELEMENT_NEARBY_PRODUCT_A,
            },
            {
                "name": "table_kv",
                "regs": [
                    r"(?P<dst>[\d\.]+[%％])",
                ],
                **ELEMENT_NEARBY_PRODUCT_NO_TYPE,
            },
        ],
    },
    {
        "path": ["050托管费率"],
        "models": [
            {
                "name": "table_kv",
                "regs": [
                    r"(?P<dst>[\d\.]+[%％])",
                ],
                **ELEMENT_NEARBY_PRODUCT_A,
            },
            {
                "name": "table_kv",
                "regs": [
                    r"(?P<dst>[\d\.]+[%％])",
                ],
                **ELEMENT_NEARBY_PRODUCT_NO_TYPE,
            },
        ],
    },
    {
        "path": ["051基金名称"],
        "models": [
            {
                "name": "auto",
                "target_element": [ElementClass.PARAGRAPH.value],
                "use_answer_pattern": False,
                "regs": [
                    rf"(?P<dst>{R_FUND_NAME_FEEDER}).*C.*基金产品资料概要",
                    rf"(?P<dst>{R_FUND_NAME}).*C.*基金产品资料概要",
                ],
            },
            {
                "name": "auto",
                "target_element": [ElementClass.PARAGRAPH.value],
                "use_answer_pattern": False,
                "regs": [
                    rf"(?P<dst>{R_FUND_NAME_FEEDER}).*C",
                    rf"(?P<dst>{R_FUND_NAME}).*C",
                ],
                "elements_nearby": {
                    "regs": [r"资料概要"],
                    "amount": 1,
                    "step": 1,
                },
            },
            {
                "name": "auto",
                "target_element": [ElementClass.PARAGRAPH.value],
                "regs": [
                    rf"(?P<dst>{R_FUND_NAME_FEEDER})",
                    rf"(?P<dst>{R_FUND_NAME})",
                ],
                "elements_nearby": {
                    "regs": R_REGS_C,
                    "amount": 3,
                    "step": 1,
                },
            },
            {
                "name": "middle_paras",
                "top_anchor_regs": [
                    "华夏",
                ],
                "bottom_anchor_regs": [
                    "[(（]华夏.*?C",
                ],
                "top_anchor_content_regs": ["(?P<content>华夏.*)"],
                "bottom_anchor_content_regs": ["(?P<content>.*?)[(（]华夏"],
                "include_bottom_anchor": True,
            },
            {
                "name": "fund_name",
                "target_element": [ElementClass.PARAGRAPH.value],
                "regs": [
                    r"(?P<dst>华夏.*)",
                ],
                "elements_nearby": {
                    "regs": R_REGS_C,
                    "amount": 3,
                    "step": 1,
                },
            },
        ],
    },
    {
        "path": ["052管理人"],
        "models": [
            {
                "name": "table_kv",
                **ELEMENT_NEARBY_PRODUCT_C,
            },
            {
                "name": "auto",
                **ELEMENT_NEARBY_PRODUCT_C,
            },
        ],
    },
    {
        "path": ["053托管人"],
        "models": [
            {
                "name": "table_kv",
                **ELEMENT_NEARBY_PRODUCT_C,
                "keep_dummy": True,
                "multi": True,
                "feature_black_list": [r"__regex托管人"],
                "regs": [
                    r"托管人[:：]?(?P<dst>.*)",
                ],
            },
            {
                "name": "auto",
                **ELEMENT_NEARBY_PRODUCT_C,
            },
        ],
    },
    {
        "path": ["054基金经理"],
        "models": [
            {
                "name": "table_kv",
                **ELEMENT_NEARBY_PRODUCT_C,
            },
            {
                "name": "auto",
                **ELEMENT_NEARBY_PRODUCT_C,
            },
        ],
    },
    {
        "path": ["055投资目标"],
        "models": [
            {
                "name": "table_kv",
                **ELEMENT_NEARBY_PRODUCT_C,
            },
            {
                "name": "auto",
                **ELEMENT_NEARBY_PRODUCT_C,
            },
        ],
    },
    {
        "path": ["056投资范围"],
        "models": [
            {
                "name": "table_kv",
                "feature_white_list": [
                    r"主要投资策略",
                ],
                "only_matched_value": True,
                "multi": True,
                **SCOPE_INVESTMENT,
                **ELEMENT_NEARBY_PRODUCT_C,
            },
            {
                "name": "auto",
                **ELEMENT_NEARBY_PRODUCT_C,
            },
        ],
    },
    {
        "path": ["057投资比例"],
        "models": [
            {
                "name": "cell_partial_text",
                "filter_by": "col",
                "regs": [
                    r"(?P<dst>[^，。]*投资(组合)?比例为.*?。)(主要)?投资策略",
                ],
                **ELEMENT_NEARBY_PRODUCT_C,
            },
            {
                "name": "table_kv",
                "only_matched_value": True,
                # http://100.64.0.9:55819/scriber/#/project/remark/10386?projectId=75&treeId=75&fileId=1534&schemaId=4&schemaKey=057%E6%8A%95%E8%B5%84%E6%AF%94%E4%BE%8B
                # 由于跨页合并的问题，在find_kv_pairs时，会匹配到最后一个，导致无法匹配到正则，故需要多行匹配
                "multi": True,  #
                "regs": [
                    r"(?P<dst>[^，。]*投资(组合)?比例.*)",
                    r"(?P<dst>[^。]*投资于[^。]*比例.*)",
                ],
                **ELEMENT_NEARBY_PRODUCT_C,
            },
            {
                "name": "auto",
                "feature_black_list": [
                    r"__regex__投资策略|不超过",
                ],
                **ELEMENT_NEARBY_PRODUCT_C,
            },
        ],
    },
    {
        "path": ["058业绩比较基准"],
        "models": [
            {
                "name": "cell_partial_text",
                "regs": [
                    r"业绩比较基准(?P<dst>[^的].*)",
                ],
                **ELEMENT_NEARBY_PRODUCT_C,
            },
            {
                "name": "auto",
                **ELEMENT_NEARBY_PRODUCT_C,
                "use_answer_pattern": False,
                "need_match_length": False,
                "model_alternative": True,
                "regs": [
                    r"比较基准[为:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["059认购费率"],
        "models": [
            {
                "name": "row_match",
                "keep_dummy": True,
                "row_pattern": [
                    r"认购费",
                ],
                "content_pattern": [
                    r"(?P<dst>.*)",
                ],
                "multi": True,
                **ELEMENT_NEARBY_PRODUCT_C,
            },
            {
                "name": "auto",
                "multi": True,
                **ELEMENT_NEARBY_PRODUCT_C,
                "regs": [
                    r"(?P<dst>认购)(/申购)[A-Z]类基金份额",
                    r"认购.*(?P<dst>[A-Z]类基金份额的?)",
                    r"不?收取认购费",
                    r"(?P<dst>认购).*?费用为\d+",
                    r"费用为\d+",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["060申购费率"],
        "models": [
            {
                "name": "row_match",
                "keep_dummy": True,
                "row_pattern": [
                    r"申购费",
                ],
                "content_pattern": [
                    r"(?P<dst>.*)",
                ],
                "multi": True,
                **ELEMENT_NEARBY_PRODUCT_C,
            },
            {
                "name": "auto",
                "multi": True,
                **ELEMENT_NEARBY_PRODUCT_C,
                "regs": [
                    r"申购[A-Z]类基金份额",
                    r"(?P<dst>不?收取).*申购费(用为\d+)?",
                    r"申购费(用为\d+)?",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["061赎回费率"],
        "models": [
            {
                "name": "row_match",
                "keep_dummy": True,
                "row_pattern": [
                    r"赎回费",
                ],
                "content_pattern": [
                    r"(?P<dst>.*)",
                ],
                "multi": True,
                **ELEMENT_NEARBY_PRODUCT_C,
            },
            {
                "name": "auto",
                **ELEMENT_NEARBY_PRODUCT_C,
            },
        ],
    },
    {
        "path": ["062管理费率"],
        "models": [
            {
                "name": "table_kv",
                "regs": [
                    r"(?P<dst>[\d\.]+[%％])",
                ],
                **ELEMENT_NEARBY_PRODUCT_C,
            },
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    r"管理费.*?(?P<dst>[\d\.]+[%％])",
                ],
                **ELEMENT_NEARBY_PRODUCT_C,
            },
        ],
    },
    {
        "path": ["063托管费率"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"托管费.*?(?P<dst>[\d\.]+[%％])",
                ],
                **ELEMENT_NEARBY_PRODUCT_C,
            },
            {
                "name": "cell_partial_text",
                "regs": [
                    r"托管费.*?(?P<dst>[\d\.]+[%％])",
                ],
                **ELEMENT_NEARBY_PRODUCT_C,
            },
        ],
    },
    {
        "path": ["064销售服务费"],
        "models": [
            {
                "name": "partial_text",
                **ELEMENT_NEARBY_PRODUCT_C,
            },
            {
                "name": "cell_partial_text",
                "regs": [
                    r"销售服务费.*?(?P<dst>[\d\.]+[%％])",
                ],
                **ELEMENT_NEARBY_PRODUCT_C,
            },
        ],
    },
    {
        "path": ["065基金名称"],
        "models": [
            {
                "name": "middle_paras",
                "top_anchor_regs": [
                    "本页无",
                ],
                "bottom_anchor_regs": [
                    "招募说明书",
                ],
                "top_anchor_content_regs": ["(?P<content>华夏.*)"],
                "bottom_anchor_content_regs": ["(?P<content>.*?)招募说明书"],
                "include_bottom_anchor": True,
            },
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    rf"(?P<dst>{R_FUND_NAME_FEEDER})",
                    rf"(?P<dst>{R_FUND_NAME})",
                ],
                "order_by_index": True,
                "page_range": [-1],
            },
            {
                "name": "fund_name",
                "use_answer_pattern": False,
                "regs": [
                    r"(?P<dst>华夏.*)",
                ],
                "order_by_index": True,
                "multi_elements": True,
                "page_range": [-1],
            },
        ],
    },
    {
        "path": ["066管理人"],
        "models": [
            {
                "name": "auto",
                "page_range": [-1],
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
