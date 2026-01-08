"""中信建投 国债发行公告POC"""

predictor_options = [
    {
        "path": ["债券名称"],
        "models": [
            {
                "name": "fixed_position",
                "positions": (0, 3),
                "regs": [r"关于(?P<dst>.*国债.*发行)"],
            },
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["招标日期"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["招标时间（起）"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["招标时间（止）"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["总发行规模"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [r"竞争性招标面值总额(?P<dst>[\d]+亿元)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["发行期限"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [r"国债（(?P<dst>\d年)期）"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["票面利率"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["招标方式"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["付息方式"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [r"(?P<dst>按年付息，每年.*支付利息，.*?支付最后一次利息)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["公告手续费"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["起息日（年份）"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["起息日（具体日期）"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["缴款日期"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["上市日期"],
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
