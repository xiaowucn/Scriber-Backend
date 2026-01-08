"""产品承销/认购额度表"""

predictor_options = [
    {
        "path": ["发行人中文全称"],
        "models": [
            {
                "name": "octopus_kv",
                "pattern": [
                    r"发行人中文全称[:：](?P<dst>.*?公司)",
                ],
            },
        ],
    },
    {
        "path": ["发行人账户账号"],
        "models": [
            {
                "name": "octopus_kv",
                "pattern": [
                    r"发行人账户账号[:：](?P<dst>S\d+)",
                ],
            },
        ],
    },
    {
        "path": ["产品简称"],
        "models": [
            {
                "name": "octopus_kv",
                "pattern": [
                    r"产品简称[:：](?P<dst>.*?)产品代码",
                ],
            },
        ],
    },
    {
        "path": ["产品代码"],
        "models": [
            {
                "name": "octopus_kv",
                "pattern": [
                    r"产品代码[:：](?P<dst>\d+)",
                ],
            },
        ],
    },
    {
        "path": ["持有人"],
        "sub_primary_key": ["持有人全称"],
        "models": [
            {
                "name": "holder_row",
            },
        ],
    },
    {
        "path": ["合计（万元）"],
        "models": [
            {
                "name": "octopus_amount",
                "pattern": [
                    r"合计（万元）",
                ],
            },
        ],
    },
    {
        "path": ["未成功发行额度（万元）"],
        "models": [
            {
                "name": "octopus_amount",
                "pattern": [
                    r"未成功发行额度（万元）",
                ],
            },
        ],
    },
    {
        "path": ["计划发行额度（万元）"],
        "models": [
            {
                "name": "octopus_amount",
                "pattern": [
                    r"计划发行额度（万元）",
                ],
            },
        ],
    },
    {
        "path": ["日期"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
