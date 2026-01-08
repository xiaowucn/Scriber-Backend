# -*- coding: utf-8 -*-

"""
Mole id: 96
Mole name: 2108 股权激励计划授予
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()


predictor_options.extend(
    [
        {
            "path": ["股权激励权益授予日"],
            "models": [
                {"name": "partial_text", "regs": [r"限制性股票(首次)?授予日：(?P<dst>.*)"]},
            ],
        },
        {
            "path": ["股权激励权益授予数量"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["股权激励方式"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["授予价格（限制性股票）"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["行权价格（期权）"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["激励计划的期限安排情况"],
            "models": [
                {
                    "name": "score_filter",
                },
            ],
        },
        {
            "path": ["激励对象名单及授予情况", "董事、高管、核心技术人员"],
            "sub_primary_key": [
                "姓名",
            ],
            "models": [
                {
                    "name": "table_row",
                    "neglect_patterns": [r"[合总小]计", r"董事会|预留", "首次授予"],
                    "multi": True,
                },
            ],
        },
        {
            "path": ["激励对象名单及授予情况", "其他人员"],
            "models": [
                {
                    "name": "table_row",
                    "header_regs": [r"董事会"],
                },
            ],
        },
        {
            "path": ["激励对象名单及授予情况", "预留部分"],
            "models": [
                {
                    "name": "table_row",
                    "header_regs": [r"预留"],
                },
            ],
        },
        {
            "path": ["是否存在以下情况：激励对象为董事、高管的，在限制性股票授予日前6个月卖出公司股份"],
            "models": [
                {
                    "name": "para_match",
                    "paragraph_pattern": r"(?P<content>无公司的?董事、高级管理人员参与|高级管理人员.*?不存在买?卖出?公司股票|本计划激励对象不包括独立董事.*?及其.*子女)",
                },
            ],
        },
        {
            "path": ["预计实施本次激励计划应计提的费用"],
            "models": [
                {
                    "name": "table_tuple",
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": ["对公司会计年度经营业绩的影响"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
    ]
)

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
