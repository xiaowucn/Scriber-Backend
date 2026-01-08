"""
schema id: 132
schema name: "21 资产查封冻结公告"
"""

predictor_options = [
    {
        "path": ["查封/冻结概述"],
        "models": [
            {
                "name": "partial_text",
                "multi": True,
                "multi_elements": True,
                "regs": {
                    "资产类型": [r""],
                    "资产账面价值合计": [r""],
                    "资产账面价值合计占总资产比例": [r""],
                },
            },
        ],
        "sub_primary_key": ["资产类型", "资产账面价值合计"],
    },
    {
        "path": ["查封/冻结详情"],
        "models": [
            {
                "name": "table_row",
                "neglect_patterns": [
                    r"[合总小]计",
                ],
                "multi": True,
                "multi_elements": True,
                "from_title": {"资产类型": r"(?P<dst>(股权|土?地及地上附着物|银行账户))冻结情况"},
            },
        ],
        "sub_primary_key": ["公司名称", "账面价值", "权属编号", "执行裁定文号", "账号"],
        "unit_depend": {"账面价值": "单位"},
    },
    # {
    #     "path": ["查封/冻结详情", "资产类型"],
    #     "models": [
    #         {'name': 'partial_text', 'multi': True, "multi_elements": True,},
    #     ],
    # },
]


prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
