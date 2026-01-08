"""
3: 上交所合规检查
"""

from remarkable.common.constants import TableType

neglect_patterns = [r"[小合总共]计$"]

predictor_options = [
    {
        "path": ["主营业务-分产品"],
        "models": [
            {
                "name": "main_business",
                "multi": True,
                "neglect_patterns": neglect_patterns + [r"^[\d,\.]+$"],
                "prefer_table_title_patterns": [r"主营业务分.*?情[况行]$"],
                "inject_syllabus_features": ["主营业务分析"],
            },
        ],
        "sub_primary_key": ["产品"],
    },
    {
        "path": ["主营业务-分行业"],
        "models": [
            {
                "name": "main_business",
                "multi": True,
                "neglect_patterns": neglect_patterns + [r"^[\d,\.]+$"],
                "prefer_table_title_patterns": [r"主营业务分.*?情[况行]$"],
                "inject_syllabus_features": ["主营业务分析"],
            },
        ],
        "sub_primary_key": ["行业"],
    },
    {
        "path": ["营业收入"],
        "models": [
            {
                "name": "main_business",
                "multi_level": True,  # 尽可能匹配到多的表格
                "table_type": TableType.TUPLE.value,
                "prefer_table_title_patterns": [r"合并利润表"],
                "inject_syllabus_features": ["合并利润表", r"财务报[表告]", r"审计报[告表]"],
                "inject_table_features": {
                    "营业收入": [r"__regex__^(largest_year_minus_0|[本当][年期])__regex__(?<=其中).*?营业总?收入$"],
                    "数值": [r"__regex__^(largest_year_minus_0|[本当][年期])__regex__(?<=其中).*?营业总?收入$"],
                },
            },
        ],
    },
    {
        "path": ["营业收入-主营业务"],
        "models": [
            {
                "name": "main_business",
                "neglect_patterns": neglect_patterns + [r"^(主营|其他)业务$"],
                "multi": True,
                "neglect_title_patterns": [r"营业收入[和及]营业成本情况$", r"(合同产生|履约义务)的.*"],
                "inject_table_features": {
                    "主营业务收入金额": [
                        r"__regex__^(largest_year_minus_0|[本当][年期])__regex__收入$",
                        "主营业务|收入",
                    ],
                },
                "prefer_table_title_patterns": [r"按业务"],
            },
        ],
        "sub_primary_key": ["业务名称"],
    },
    {
        "path": ["营业收入-其他业务收入"],
        "models": [
            {
                "name": "main_business",
                "neglect_patterns": neglect_patterns + [r"^主营业务$"],
                "neglect_title_patterns": [r"营业收入[和及]营业成本情况$", r"(合同产生|履约义务)的.*"],
                "multi": True,
            },
        ],
        "sub_primary_key": ["业务名称"],
    },
    {
        "path": ["营业收入-所有细分业务收入"],
        "models": [
            {
                "name": "main_business",
                "multi_level": True,
                "inject_syllabus_features": [r"__regex__收入.*?按业务"],
                "inject_table_features": {
                    "业务名称": [r"__regex__业务$__regex__^项目$"],
                    "细分业务收入金额": [
                        r"__regex__^(largest_year_minus_0|[本当][年期])__regex__业务$",
                        r"__regex__^(largest_year_minus_0|[本当][年期])__regex__收入$__regex__业务$",
                    ],
                },
                "neglect_patterns": neglect_patterns + [r"^(主营|其他)业务$"],
                "neglect_title_patterns": [
                    "(主营|其他)业务",
                    r"营业收入[和及]营业成本情况$",
                    r"(合同产生|履约义务)的.*",
                    r"按地区",
                ],
                "multi": True,
            },
        ],
        "sub_primary_key": ["业务名称"],
    },
    {
        "path": ["附注-分部信息"],
        "models": [
            {
                "name": "main_business",
                "parse_by": "col",
                "neglect_patterns": neglect_patterns,
                "multi": True,
                "neglect_title_patterns": ["地区分部"],
                "inject_syllabus_features": ["报告分部的财务信息"],
                "inject_table_features": {
                    "分部业务收入金额": [
                        r"__regex__^[总主]?营营?业[总务]{,2}收入$",
                        r"__regex__^对外交易收入|营业收入|分部营业收入$__regex__^收入$",
                    ],
                },
            },
        ],
        "sub_primary_key": ["业务名称"],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
