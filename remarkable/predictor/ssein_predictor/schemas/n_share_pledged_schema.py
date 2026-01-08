"""临时公告-股份被质押"""

from remarkable.predictor.ssein_predictor.schemas import filter_predictors

predictor_options = filter_predictors(exclude=("公司简称", "公司代码"))
predictor_options.extend(
    [
        {
            "path": ["证券简称"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(0, 3)),
                    "regs": [
                        r"(?<=简称[:：])(?P<dst>.*?)(?=\s?(公告|证券|股票|编[号码]))",
                        r"简称[:：](?P<dst>.+)(?!\s+$)",
                    ],
                }
            ],
        },
        {
            "path": ["证券代码"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(0, 3)),
                    "regs": [r"(?<=代码[:：])(?P<dst>\d{6})", r"代码[:：](?P<dst>\d{6})"],
                }
            ],
        },
        {
            "path": ["股份质押情况", "股东名称"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["股份质押情况", "是否控股股东"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["股份质押情况", "持股数量"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["股份质押情况", "持股比例"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["股份质押情况", "持股数量单位"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["股份质押情况", "质权人"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["股份质押情况", "质押起始日"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["股份质押情况", "质押到期日"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["股份质押情况", "质押期限"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["股份质押情况", "质押用途"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["股份质押情况", "本次质押股数"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["股份质押情况", "占其所持股份比例"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["股份质押情况", "占公司总股本比例"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["股份质押情况", "是否为限售股"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["股份质押情况", "累计质押数量"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["股份质押情况", "累计质押占所持比例"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["股份质押情况", "累计质押占总股本比例"],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["股份质押情况", "质押股数单位"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
