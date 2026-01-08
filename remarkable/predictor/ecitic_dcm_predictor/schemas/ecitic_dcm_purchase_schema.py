"""
申购单
"""

predictor_options = [
    {
        "path": ["证券账户号码"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["证券账户名称"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["机构代码"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["机构名称"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["经办人姓名"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["座机电话"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["传真号码"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["手机电话"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["电子邮箱"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
