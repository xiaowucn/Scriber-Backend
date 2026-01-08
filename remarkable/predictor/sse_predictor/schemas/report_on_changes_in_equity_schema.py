"""
schema id: 74
schema name: "20 权益变动报告"
"""

from remarkable.predictor.sse_predictor.predictor_config import SPECIAL_ATTR_PATTERNS

predictor_options = [
    {
        "path": ["公司全称"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["公司简称"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["公司代码"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["公告时间"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(20)),
                "pages": (0,),
                "regs": [rf"签署日期[:：]?{SPECIAL_ATTR_PATTERNS['date'][0]}"],
            }
        ],
    },
    {
        "path": ["公告编号"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["主体类型"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["股份变动性质"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["股份变动数量"],
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
