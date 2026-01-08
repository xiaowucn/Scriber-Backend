"""
基金合同
"""

from remarkable.predictor.cmbchina_predictor.schemas import (
    get_predictor_options,
    p_holding_period,
    p_holding_period_unit,
)
from remarkable.predictor.cmbchina_predictor.schemas.cmbchina_rate_adjustment_schema import R_FUND_SUFFIX
from remarkable.predictor.common_pattern import R_CONJUNCTION
from remarkable.predictor.eltype import ElementClass

predictor_options = [
    {
        "path": ["基金名称"],
        "models": [
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5020#note_556871
            {
                "name": "middle_paras",
                "top_anchor_content_regs": [
                    r"公司(?P<content>.*)",
                    r"(?P<content>.*)",
                ],
                "bottom_anchor_content_regs": [
                    rf"公司(?P<content>.*?基金(中基金)?{R_FUND_SUFFIX}?)基金合同",
                    rf"(?P<content>.*?基金(中基金)?{R_FUND_SUFFIX}?)基金合同",
                ],
                "top_anchor_regs": [r"指数型", r"发起式", r"混合型"],
                "bottom_anchor_regs": [r"基金合同$"],
                "include_bottom_anchor": True,
                "elements_in_page_range": [0],
            },
            {
                "name": "partial_text",
                "regs": [
                    rf"公司(?P<dst>.*?基金(中基金)?{R_FUND_SUFFIX}?)基金合同",
                    rf"(?P<dst>.*?基金(中基金)?{R_FUND_SUFFIX}?)基金合同",
                ],
                "model_alternative": True,
                "target_element": [ElementClass.PARAGRAPH.value],
            },
        ],
    },
    {
        "path": ["基金代码"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["是否升降级"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__基金份额的(升级和降级|自动升降级)"],
                "only_inject_features": True,
                "include_title": False,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"[升降]级(?!的?数量限制及规则.?由基金管理人在招募说明书中规定)"],
                },
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__基金销售服务费",
                    r"__regex__基金份额类别设置",
                ],
                "only_inject_features": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [
                        r"(?P<dst>根据.*取消.*自动升降级业务)",
                        r"(?P<dst>本基金.*可自动升降级.*升降级.*规则.*说明书中规定)",
                    ],
                },
            },
            {
                "name": "para_match",
                "syllabus_regs": [r"释义"],
                "multi_elements": True,
                "paragraph_pattern": [
                    r"\d+.[升降]级[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["赎回限制类型"],
        "models": [
            {
                "name": "para_match",
                "order_by_index": True,
                "multi_elements": True,
                "multi_elements_limit": 1,
                "paragraph_pattern": [
                    r"(最短|锁定)持有期|锁定期",
                    r"基金以.*滚动的?方式运作",
                    r"设.*天的滚动(运作|持有)期",
                ],
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__基金的运作方式",
                ],
                "only_inject_features": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [
                        r"(最短|锁定)持有期|锁定期",
                        r"基金以.*滚动的?方式运作",
                        r"设.*天的滚动(运作|持有)期",
                    ],
                },
            },
        ],
    },
    {
        "path": ["赎回限制"],
        "models": [
            {
                "name": "reference",
                "from_path": ["赎回限制类型"],
            },
        ],
    },
    {
        "path": ["管理费率"],
        "sub_primary_key": ["基金名称", "管理费"],
        "divide_answers": True,
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__基金管理人的管理费"],
                "only_inject_features": True,
                "one_result_per_feature": False,
                "extract_from": "same_type_elements",
                "paragraph_model": "partial_text",
                "para_config": {
                    "merge_char_result": False,
                    "multi": True,
                    "multi_elements": True,
                    "neglect_patterns": [
                        r"计提浮动管理费",
                    ],
                    "regs": {
                        "基金名称": [r"(?P<dst>[A-Z]\s*类(基金)?份额)[\u4e00-\u9fa5]*(?<!固定)管理费"],
                        "管理费": [
                            r"管理费(年费)?率?为(年费率?)?(?P<dst>[\d.%％]+)",
                            # http://100.64.0.9:55842/scriber/#/project/remark/9506?treeId=10&fileId=64&schemaId=3
                            r"管理费按.*?净值.*?的?\s*(?P<dst>[\d.%％]+)",
                        ],
                    },
                },
            },
        ],
    },
    {
        "path": ["销售服务费率"],
        "sub_primary_key": ["基金名称"],
        "divide_answers": True,
        "models": [
            {
                "name": "subscription",
                "syllabus_regs": [
                    r"基金份额的(分类|等级|申购|赎回)",
                    rf"基金的?(?:(?:费用|税收)[{R_CONJUNCTION}]?){{2}}",
                    r"销售.?服务费",
                ],
                "neglect_syllabus_regs": [
                    r"申购费|托管费|管理费",
                    r"基金合同的?(内容)?摘要",
                    r"其他事项",
                ],
                "para_regs": [
                    r"[A-Z](类|级).*([%％]|费率为[0零]|不收取(基金)?销售服务费)",
                    r"([%％]|费率为[0零]|不收取(基金)?销售服务费).*[A-Z](类|级)",
                ],
                "multi_config": {
                    "基金名称": True,
                    "销售服务费": True,
                },
                "regs": {
                    "基金名称": [
                        r"(?P<dst>[A-Z][类级])",
                    ],
                    "销售服务费": [
                        r"(?P<dst>([\d\.]+[%％]?|不收取(基金)?销售服务费))",
                    ],
                },
                "splits": [r"[。,，;；]"],
                "need_distinct": True,
            },
            # 没有分级基金的情况 https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5014#note_560813
            {
                "name": "subscription",
                "syllabus_regs": [
                    r"基金份额的(分类|等级|申购|赎回)",
                    rf"基金的?(?:(?:费用|税收)[{R_CONJUNCTION}]?){{2}}",
                    r"销售.?服务费",
                ],
                "neglect_syllabus_regs": [
                    r"申购费|托管费|管理费",
                ],
                "para_regs": [
                    r"本基金.*([%％]|费率为[0零]|不收取(基金)?销售服务费)",
                    r"([%％]|费率为[0零]|不收取(基金)?销售服务费).*本基金",
                ],
                "multi_config": {
                    "基金名称": False,
                    "销售服务费": False,
                },
                "regs": {
                    "基金名称": [
                        r"(?P<dst>本基金)",
                    ],
                    "销售服务费": [
                        r"(?P<dst>([\d\.]+[%％]?|不收取(基金)?销售服务费))",
                    ],
                },
                "splits": [r"[。,，;；]"],
                "need_distinct": True,
            },
            {
                "name": "partial_text",
                "syllabus_regs": [r"基金的?费用与税收"],
                "merge_char_result": False,
                "multi_elements": True,
                "multi": True,
                "regs": {
                    "基金名称": [
                        r"(?P<dst>[A-Z]类(基金份额)?([和、][A-Z]类)?基金份额)[\u4e00-\u9fa5]*销售服务费",
                    ],
                    "销售服务费": [
                        r"不收取销售服务费",
                        r"销售服务费(年费)?率?为(?P<dst>[\d.%％]+)",
                        r"销售服务费按.*净值的(?P<dst>[\d.%％]+)",
                    ],
                },
            },
        ],
    },
    {
        "path": ["费率生效日期"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["首次认购下限-原文"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["首次认购下限", "基金名称"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["首次认购下限", "最低限额"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["首次认购下限", "销售平台"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["追加认购最低金额-原文"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["追加认购最低金额", "基金名称"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["追加认购最低金额", "最低限额"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["追加认购最低金额", "销售平台"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["产品持有期"],
        "models": [
            {
                "name": "fixed_position",
                "target_element": [ElementClass.PARAGRAPH.value],
                "pages": [0],
                "regs": p_holding_period,
            }
        ],
    },
    {
        "path": ["产品持有期单位"],
        "models": [
            {
                "name": "fixed_position",
                "target_element": [ElementClass.PARAGRAPH.value],
                "pages": [0],
                "regs": p_holding_period_unit,
            }
        ],
    },
    {"path": ["管理费率优惠开始日期"], "models": [{"name": "partial_text"}]},
    {"path": ["管理费率优惠结束日期"], "models": [{"name": "partial_text"}]},
    {"path": ["销售服务费率优惠开始日期"], "models": [{"name": "partial_text"}]},
    {"path": ["销售服务费率优惠结束日期"], "models": [{"name": "partial_text"}]},
    {"path": ["产品简称"], "models": [{"name": "partial_text"}]},
    {"path": ["产品成立日"], "models": [{"name": "partial_text"}]},
]

prophet_config = {
    "depends": {},
    "predictor_options": get_predictor_options(predictor_options),
}
