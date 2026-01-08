"""
63: "2401 股份被质押"
"""

from remarkable.predictor.sse_predictor.predictor_config import SPECIAL_ATTR_PATTERNS, filter_predictors

predictor_options = filter_predictors(exclude=("公告时间",))

predictor_options.extend(
    [
        {
            "path": ["公告日期"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(-10, 0))[::-1],
                    "regs": SPECIAL_ATTR_PATTERNS["date"],
                }
            ],
        },
        {
            "path": ["公告类型"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["是否属于控股股东及其一致行动人质押股份占其所持股份的比例达到50%以上的情况"],
            "models": [
                {
                    "name": "enum_value",
                    "simple": "否",
                },
            ],
        },
        {
            "path": [
                "是否属于控股股东及其一致行动人质押股份占其所持股份的比例达到50%以上，且出现债务逾期或其他资信恶化情形"
            ],
            "models": [
                {
                    "name": "enum_value",
                    "simple": "否",
                },
            ],
        },
        {
            "path": ["是否属于控股股东及其一致行动人质押股份占其所持股份的比例达到80%以上的情况"],
            "models": [
                {
                    "name": "enum_value",
                    "simple": "否",
                },
            ],
        },
        {
            "path": ["是否属于控股股东及其一致行动人质押股份出现平仓风险"],
            "models": [
                {
                    "name": "enum_value",
                    "simple": "否",
                },
            ],
        },
        # {
        #     'path': ['二级'],
        #     'sub_primary_key': ['出质人名称'],
        # },
        {
            "path": ["二级", "出质人名称"],
            "models": [
                {
                    "name": "table_row",
                }
            ],
        },
        {
            "path": ["二级", "出质人是否是控股股东及其一致行动人"],
            "models": [
                {
                    "name": "table_row",
                }
            ],
        },
        {
            "path": ["二级", "质权人名称"],
            "models": [
                {
                    "name": "table_row",
                }
            ],
        },
        {
            "path": ["二级", "质押起始日"],
            "models": [
                {
                    "name": "table_row",
                }
            ],
        },
        {
            "path": ["二级", "质押到期日"],
            "models": [
                {
                    "name": "table_row",
                }
            ],
        },
        {
            "path": ["二级", "质押股份是否为限售流通股"],
            "models": [
                {
                    "name": "table_row",
                }
            ],
        },
        {
            "path": ["二级", "质押股份数量", "质押股份数量"],
            "models": [
                {
                    "name": "table_row",
                }
            ],
        },
        {
            "path": ["二级", "质押股份数量", "质押股份单位"],
            "models": [
                {
                    "name": "table_row",
                }
            ],
        },
        {
            "path": ["二级", "质押股份数量占公司总股本比例"],
            "models": [
                {
                    "name": "table_row",
                }
            ],
        },
        {
            "path": ["二级", "出质人持有上市公司股份总数", "出质人持有上市公司股份总数"],
            "models": [
                {
                    "name": "table_row",
                }
            ],
        },
        {
            "path": ["二级", "出质人持有上市公司股份总数", "出质人持有上市公司股份单位"],
            "models": [
                {
                    "name": "table_row",
                }
            ],
        },
        {
            "path": ["二级", "出质人持有上市公司股份总数占公司总股本比例"],
            "models": [
                {
                    "name": "table_row",
                }
            ],
        },
        {
            "path": ["二级", "质押股份是否负担业绩补偿义务"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["二级", "本次质押后累计质押股份数量", "本次质押后累计质押股份数量"],
            "models": [
                {
                    "name": "table_row",
                }
            ],
        },
        {
            "path": ["二级", "本次质押后累计质押股份数量", "本次质押后累计质押股份单位"],
            "models": [
                {
                    "name": "table_row",
                }
            ],
        },
        {
            "path": ["二级", "本次质押后累计质押股份数量占其持股总数的比例"],
            "models": [
                {
                    "name": "table_row",
                }
            ],
        },
        {
            "path": ["二级", "本次质押后累计质押股份数量占公司总股本的比例"],
            "models": [
                {
                    "name": "table_row",
                }
            ],
        },
        {
            "path": ["二级", "股份质押的目的、用途"],
            "models": [
                {
                    "name": "table_row",
                }
            ],
        },
        {
            "path": ["股份质押对上市公司控制权和日常经营的影响"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["可能被平仓的股份数量"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["可能被平仓的股份数比例"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["平仓风险的化解措施"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
