"""
基金合同POC
"""

predictor_options = [
    {
        "path": ["产品中文名称"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "multi": False,
                "multi_elements": False,
                "only_first": False,
                "include_title": False,
            }
        ],
    },
    {
        "path": ["产品投资类型"],
        "models": [
            {
                "name": "middle_paras",
                "multi": False,
                "multi_elements": False,
                "keep_parent": True,
                "use_syllabus_model": True,
                "use_top_crude_neighbor": False,
                "top_anchor_regs": [
                    "投资范围",
                    "本基金(主要)?投资于",
                    "本基金的投资范围为",
                    "本基金投资于.*?包括",
                ],
                "bottom_anchor_regs": [
                    "基金的投资组合比例",
                    "投资策略$",
                    "投资理念$",
                    "投资限制$",
                    "货币市场基金投资其他货币市场基金的比例",
                    "本基金股票及存托凭证投资占基金资产的比例",
                ],
                "inject_syllabus_features": [
                    "__regex__基金的投资__regex__[(（]?一二三四五[）)]?、?投资范围",
                    "__regex__[(（]?一二三四五[）)]?、?投资范围",
                ],
                "inject_features_first": True,
                "syllabus_level": 2,
                "include_top_anchor": True,
                "include_bottom_anchor": False,
                "top_default": True,
                "top_greed": True,
                "bottom_default": False,
            }
        ],
    },
    {
        "path": ["基金类别"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "multi": False,
                "multi_elements": False,
                "only_first": False,
                "include_title": False,
            }
        ],
    },
    {
        "path": ["境内托管机构名称"],
        "models": [{"name": "partial_text", "multi": False, "multi_elements": False, "use_answer_pattern": False}],
    },
    {
        "path": ["产品托管费率"],
        "models": [{"name": "partial_text", "multi": False, "multi_elements": False, "use_answer_pattern": False}],
    },
    {
        "path": ["产品运作方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "multi": False,
                "multi_elements": False,
                "only_first": False,
                "include_title": False,
            }
        ],
    },
    {
        "path": ["结算模式"],
        "models": [{"name": "partial_text", "multi": False, "multi_elements": False, "use_answer_pattern": False}],
    },
    {
        "path": ["小微基金人数触发条件"],
        "models": [{"name": "partial_text", "multi": False, "multi_elements": False, "use_answer_pattern": False}],
    },
    {
        "path": ["合同终止情形条款"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "multi": False,
                "multi_elements": False,
                "only_first": False,
                "include_title": False,
            }
        ],
    },
    {
        "path": ["投资目标"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "multi": False,
                "multi_elements": False,
                "only_first": False,
                "include_title": False,
            }
        ],
    },
    {
        "path": ["投资范围条款"],
        "models": [
            {
                "name": "middle_paras",
                "multi": False,
                "multi_elements": False,
                "keep_parent": True,
                "use_syllabus_model": True,
                "use_top_crude_neighbor": False,
                "top_anchor_regs": [
                    "投资范围",
                    "本基金(主要)?投资于",
                    "本基金的投资范围为",
                    "本基金投资于.*?包括",
                ],
                "bottom_anchor_regs": [
                    "基金的投资组合比例",
                    "投资策略$",
                    "投资理念$",
                    "投资限制$",
                    "货币市场基金投资其他货币市场基金的比例",
                    "本基金股票及存托凭证投资占基金资产的比例",
                ],
                "inject_syllabus_features": [
                    "__regex__基金的投资__regex__[(（]?一二三四五[）)]?、?投资范围",
                    "__regex__[(（]?一二三四五[）)]?、?投资范围",
                ],
                "inject_features_first": True,
                "syllabus_level": 2,
                "include_top_anchor": True,
                "include_bottom_anchor": False,
                "top_default": True,
                "top_greed": True,
                "bottom_default": False,
            }
        ],
    },
    {
        "path": ["投资配置比例条款"],
        "models": [
            {
                "name": "middle_paras",
                "multi": False,
                "multi_elements": False,
                "keep_parent": True,
                "use_top_crude_neighbor": False,
                "use_syllabus_model": True,
                "top_anchor_regs": [
                    "基金的投资组合比例",
                    "货币市场基金投资其他货币市场基金的比例",
                    "本基金股票及存托凭证投资占基金资产的比例",
                ],
                "bottom_anchor_regs": [
                    "投资限制$",
                    "组合限制$",
                    "投资策略$",
                ],
                "inject_syllabus_features": [
                    "__regex__基金的投资__regex__[(（]?一二三四五[）)]?、?投资范围",
                    "__regex__[(（]?一二三四五[）)]?、?投资范围",
                ],
                "inject_features_first": True,
                "syllabus_level": 2,
                "include_top_anchor": True,
                "include_bottom_anchor": False,
                # "top_default": True,
                "top_greed": True,
                "bottom_default": True,
            }
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
