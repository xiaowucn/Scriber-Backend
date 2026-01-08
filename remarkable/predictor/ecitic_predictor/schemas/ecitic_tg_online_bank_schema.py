"""托管网银标合同"""

R_ANY_SPACE = r"\s*"

predictor_options = [
    {
        "path": ["投资范围(其它-投资监督)"],
        "models": [
            {
                "name": "middle_paras",
                "inject_syllabus_features": [r"__regex__基金的投资$"],
                "only_use_syllabus_elements": True,
                "use_syllabus_model": True,
                "top_anchor_regs": [r"投资范围$"],
                "top_anchor_content_regs": [r"投资范围[:：](?P<content>.*)"],
                "bottom_anchor_regs": [r"投资策略$"],
            },
            {
                "name": "syllabus_elt_v2",
                "keep_parent": True,
                "inject_syllabus_features": [
                    r"__regex__基金的投资$__regex__投资范围",
                    r"__regex__基金的投资$__regex__基金的投资目标、投资范围和策略__regex__投资范围",
                ],
                "feature_black_list": [r"__regex__投资策略"],
            },
        ],
    },
    {
        "path": ["投资策略(其它-投资监督)"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"投资策略[:：](?P<content>.*?)[(（]",
                ],
            },
            {
                "name": "middle_paras",
                "inject_syllabus_features": [r"__regex__基金的投资$"],
                "only_use_syllabus_elements": True,
                "use_syllabus_model": True,
                "top_anchor_regs": [r"投资策略[:：]"],
                "top_anchor_content_regs": [r"投资策略[:：](?P<content>.*)"],
                "bottom_anchor_regs": [
                    r"投资方式",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__基金的投资$__regex__投资策略$",
                    r"__regex__基金的投资$__regex__基金的投资目标、投资范围和策略__regex__投资策略与风险收益特征",
                ],
            },
        ],
    },
    {
        "path": ["开放退出期(其它-投资监督)"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"本基金的开放日[:：](?P<content>.*)",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__^(本基金的)?开放日$"],
                "only_inject_features": True,
            },
            {
                "name": "syllabus_elt_v2",
                "syllabus_black_list": [r"申购和赎回的场所"],
                "ignore_pattern": [r"基金投资者可在.*并进行通知"],
                "only_first": True,
            },
            {
                "name": "score_filter",
                "threshold": 0.8,
                "aim_types": ["TABLE"],
                "multi_elements": False,
            },
        ],
    },
    {
        "path": ["风险等级(其它-投资监督)"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "keep_parent": True,
                "only_first": True,
            },
        ],
    },
    {
        "path": ["份额类型(其它-投资监督)"],
        "models": [
            {
                "name": "middle_paras",
                "table_regarded_as_paras": True,
                "inject_syllabus_features": [r"__regex__私募基金的基本情况$"],
                "only_use_syllabus_elements": True,
                "use_syllabus_model": True,
                "top_anchor_regs": [r"私募基金的份额分类"],
                "include_top_anchor": False,
                "bottom_default": True,
                "include_bottom_anchor": True,
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__基金份额分类$"],
            },
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
