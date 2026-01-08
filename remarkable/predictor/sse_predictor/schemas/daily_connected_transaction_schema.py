"""
33: "0501 日常关联交易"

todo:
（二级） 关联方名称/关联关系
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()
predictor_options.extend(
    [
        {
            "path": ["审议程序"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["董事会投票情况"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["日常关联交易对上市公司的影响"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["本次日常关联交易", "本次日常关联交易预计金额"],
            "models": [
                {"name": "table_row", "multi": True},
            ],
        },
        {
            "path": ["本次日常关联交易", "本次日常关联交易预计金额单位"],
            "models": [
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["本次日常关联交易", "本次日常关联交易类别"],
            "models": [
                {"name": "table_row", "multi": True},
            ],
        },
        {
            "path": ["本次日常关联交易", "关联方名称"],
            "models": [
                {"name": "table_row", "multi": True},
            ],
        },
        {
            "path": ["前次日常关联交易", "前次日常关联交易的执行情况"],
            "models": [
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["前次日常关联交易", "前次日常关联交易的执行情况单位"],
            "models": [
                {"name": "table_row", "multi": True},
            ],
        },
        {
            "path": ["前次日常关联交易", "前次日常关联交易的预计"],
            "models": [
                {"name": "table_row", "multi": True},
            ],
        },
        {
            "path": ["前次日常关联交易", "前次日常关联交易的预计单位"],
            "models": [
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["前次日常关联交易", "关联方名称"],
            "models": [
                {"name": "table_row", "multi": True},
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
