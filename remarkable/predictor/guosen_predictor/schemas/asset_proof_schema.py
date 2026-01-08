"""
国信证券 资产证明
"""

predictor_options = [
    {
        "path": ["投资人资产证明"],
        "models": [
            {
                "name": "table_row",
                "neglect_row_header_regs": [r"基(全|金)(账号|名称)", r"记录数"],
            },
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
