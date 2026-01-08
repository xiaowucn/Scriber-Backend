"""银河回执-字段设置 FIXME: schema名字设置有误"""

predictor_options = [
    {
        "path": ["Fund"],
        "models": [
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["Trade Date"],
        "models": [
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["Settlement Date"],
        "models": [
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["Our CAMC Settlement Location"],
        "models": [
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["Our CAMC's Custodian Code Number"],
        "models": [
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["Your Counterparty's Settlement Location"],
        "models": [
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["Your Counterparty's Custodian Code Number"],
        "models": [
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["Trade Confirmation Note"],
        # "sub_primary_key": [
        #     'Securities',
        # ],
        "models": [
            {
                "name": "auto",
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
