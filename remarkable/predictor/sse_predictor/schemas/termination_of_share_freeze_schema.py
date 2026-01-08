"""
66: "2404 股份冻结解除"
"""

from remarkable.predictor.sse_predictor.predictor_config import SPECIAL_ATTR_PATTERNS, filter_predictors

predictor_options = filter_predictors()

predictor_options.extend(
    [
        {
            "path": ["公告类别"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
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
            "path": ["二级", "被解冻人名称"],
            "models": [
                {
                    "name": "table_kv",
                },
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["二级", "解冻时间"],
            "models": [
                {
                    "name": "table_kv",
                },
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["二级", "解冻股份数量"],
            "models": [
                {
                    "name": "table_kv",
                },
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["二级", "解冻股份数量占公司总股本比例"],
            "models": [
                {
                    "name": "table_kv",
                },
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["二级", "被解冻人持有上市公司股份总数"],
            "models": [
                {
                    "name": "table_kv",
                },
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["二级", "被解冻人持有上市公司股份总数占公司总股本比例"],
            "models": [
                {
                    "name": "table_kv",
                },
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["二级", "本次解冻后剩余被冻结股份数量"],
            "models": [
                {
                    "name": "table_kv",
                },
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["二级", "本次解冻后剩余被冻结股份数量占其持股总数比例"],
            "models": [
                {
                    "name": "table_kv",
                },
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["二级", "本次解冻后剩余被冻结股份数量占公司总股本比例"],
            "models": [
                {
                    "name": "table_kv",
                },
                {
                    "name": "partial_text",
                },
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
