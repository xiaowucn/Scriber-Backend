"""股票认购邀请书"""

predictor_options = [
    {
        "path": ["募集资金"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"募集资金总额不超过(人民币)?\s?(?P<dst>[\d,.]+\s?[亿万]元)",
                ],
            },
        ],
    },
    {
        "path": ["申购上限"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["申购下限"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["最小变动单位"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["限售期"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["非公开发行数量"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                # 'neglect_patterns': [r'累计认购数量合计大于'],
                "regs": [
                    r"非公开发行不超过\s?(?P<dst>[\d,.]+\s?股)\s?A\s?股股票",
                ],
            },
        ],
    },
    {
        "path": ["发行底价"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["主承销商"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["联席主承销商"],
        "models": [
            {
                "name": "partial_text",
                "multi": True,
                "model_alternative": True,
                "regs": [
                    r"牵头主承销商）(?P<dst>\w*?证券股份有限公司)",
                    r"联席主承销商(?P<dst>\w*?证券股份有限公司)",
                    # r'(牵头主承销商）|联席主承销商)(?P<dst>\w*?证券股份有限公司)',
                ],
            },
        ],
    },
    {
        "path": ["申购报价日期"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
]


prophet_config = {"depends": {}, "predictor_options": predictor_options}
