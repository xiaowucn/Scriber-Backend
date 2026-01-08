"""
18: "0406 提供财务资助"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()

predictor_options.extend(
    [
        {
            "path": ["（二级）", "标的名称"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "标的情况"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["（二级）", "投资金额"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "审议程序（是否要上股东大会决议）"],
            "models": [
                {
                    "name": "partial_text",
                    "enum": {
                        "default": "否",
                        "patterns": [("否", [r"[不无]需"])],
                    },
                },
            ],
        },
        {
            "path": ["（二级）", "对上市公司的影响"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["（二级）", "其他协议主体情况"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["（二级）", "是否是关联交易"],
            "models": [
                {
                    "name": "partial_text",
                    "enum": {
                        "default": "否",
                        "patterns": [("否", [r"[不无未]"])],
                    },
                },
            ],
        },
        {
            "path": ["（二级）", "关联关系（如是关联交易）"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "关联交易的必要性及对上市公司的影响（如是关联交易）"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "是否是重大资产重组"],
            "models": [
                {
                    "name": "partial_text",
                    "enum": {
                        "default": "否",
                        "patterns": [("否", [r"[不无]需"])],
                    },
                },
            ],
        },
    ]
)

prophet_config = {
    "depends": {},
    # 'merge_schema_answers': True,
    "predictor_options": predictor_options,
}
