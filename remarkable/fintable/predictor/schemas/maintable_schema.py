"""
三大报表财务数据
"""

report_year_patterns = [r"(?:1\d|20|21)\d{2}.*", r"^[本当上][年期]"]

predictor_options = [
    {
        "path": [
            "资产负债表",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_tuple",
                "distinguish_year": False,
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": report_year_patterns,
                    }
                ],
            },
        ],
        "location_threshold": 1,
    },
    {
        "path": [
            "利润表",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_tuple",
                "distinguish_year": False,
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": report_year_patterns,
                    }
                ],
                "息税前利润": {
                    "feature_black_list": [r"__regex__综合收益__regex__year"],
                },
                "净利润": {
                    "feature_black_list": [r"__regex__^利润总额__regex__DATE"],
                },
            },
        ],
        "location_threshold": 1,
    },
    {
        "path": [
            "现金流量表",
        ],
        "sub_primary_key": [
            "报告期",
        ],
        "models": [
            {
                "name": "table_tuple",
                "distinguish_year": False,
                "dimensions": [
                    {
                        "column": "报告期",
                        "pattern": report_year_patterns,
                    }
                ],
            },
        ],
        "location_threshold": 1,
    },
]


prophet_config = {"depends": {}, "predictor_options": predictor_options}
