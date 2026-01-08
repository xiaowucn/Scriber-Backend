"""
121: "1302 增持简式权益变动报告书"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors(exclude=("公司全称", "公司简称", "公司代码"))

predictor_options.extend(
    [
        {
            "path": ["公司全称"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(0, 5)),
                    "regs": [r"(?P<dst>.*?公司)"],
                }
            ],
        },
        {
            "path": ["公司简称"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(0, 10)),
                    "regs": [
                        r"(?<=简称[:：])(?P<dst>.*?)(?=\s?(公告|证券|股票|编[号码]))",
                        r"简称[:：](?P<dst>.+)(?!\s+$)",
                    ],
                }
            ],
        },
        {
            "path": ["公司代码"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(0, 10)),
                    "regs": [r"(?<=代码[:：])(?P<dst>\d{6})", r"代码[:：](?P<dst>\d{6})"],
                }
            ],
        },
        {
            "path": ["二级", "（增减持主体）"],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                    "neglect_patterns": [
                        r"[合总小]并?计",
                    ],
                },
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "二级",
                "增减持类型",
            ],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                    "neglect_patterns": [
                        r"[合总小]并?计",
                    ],
                },
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["二级", "减持人/增持人权益变动前后持股情况-变动前持股数量"],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                    "neglect_patterns": [
                        r"[合总小]并?计",
                    ],
                },
                {
                    "name": "partial_text",
                },
            ],
            "unit_depend": {"金额": "单位"},
        },
        {
            "path": [
                "二级",
                "减持人/增持人权益变动前后持股情况-变动前持股比例",
            ],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                    "neglect_patterns": [
                        r"[合总小]并?计",
                    ],
                },
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["二级", "减持人/增持人权益变动前后持股情况-变动后持股数量"],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                    "neglect_patterns": [
                        r"[合总小]并?计",
                    ],
                },
                {
                    "name": "partial_text",
                },
            ],
            "unit_depend": {"金额": "单位"},
        },
        {
            "path": [
                "二级",
                "减持人/增持人权益变动前后持股情况-变动后持股比例",
            ],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                    "neglect_patterns": [
                        r"[合总小]并?计",
                    ],
                },
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "二级",
                "权益变动的方式（二级/大宗/协议/司法化）",
            ],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                    "neglect_patterns": [
                        r"[合总小]并?计",
                    ],
                },
                {
                    "name": "partial_text",
                },
            ],
            "share_column": True,
        },
    ]
)


prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
