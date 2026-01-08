# -*- coding: utf-8 -*-
"""
schema_id: 22
schema_name: 0401 购买资产
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()

trade_detail_pattern = r"(\d{1,3}(\.\d{2})?%的?股权)|\d{1,3}(,\d{3})*\s*股股份(（.*）)?"

predictor_options.extend(
    [
        {
            "path": ["（二级）"],
            "sub_primary_key": ["出售或购买的标的名称（key）"],
            "crude_answer_path": ["（二级）", "出售或购买的标的名称（key）"],
            "models": [
                {
                    "name": "relation_entity",
                    "relation_pattern": r"(向|通过).*(竞|购)买.*?((\d{1,2}(\.\d{2})?%的?股权)|\d{1,3}(,\d{3})*\s*股股份)",
                    "stop_patterns": [
                        "(以|通过).*?(股份|股票?|债券|现金)的方式，?",
                        "(?<=买)其(合计)?持有的?(不超过)?",
                    ],
                    "entity_options": [
                        {
                            "schema_name": "出售或购买的标的名称（补充）",
                            "patterns": [rf"(?<=买).*?(?P<entity>{trade_detail_pattern})"],
                        },
                        {
                            "schema_name": "出售或购买的标的名称（key）",
                            "patterns": [rf"(?<=买)(.*持有的?)?(?P<entity>.*?)(合计\s*)?({trade_detail_pattern})"],
                        },
                        {
                            "schema_name": "出售或购买的标的类别",
                            "patterns": [rf"(?<=买).*?(?P<entity>{trade_detail_pattern})"],
                        },
                        {
                            "schema_name": "交易对手方",
                            "patterns": [r"向(?P<entity>.*?)购买", r"通过.*(竞|购)买(?P<entity>.*?)持有的"],
                        },
                    ],
                    "syllabus_pattern": r"本次(重组情况|交易方案)概(述|要)",
                    "multi": True,
                }
            ],
        },
        {"path": ["（二级）", "交易事项"], "models": [{"name": "enum_value", "simple": "购买"}], "share_column": True},
        {
            "path": ["（二级）", "是否属于境外资产"],
            "models": [
                {"name": "table_kv", "syllabus_pattern": r"(标的公司|置入资产)基本情况", "multi_elements": True}
            ],
            "group": {"lookup_strategy": "lookahead"},
            "location_threshold": 0.1,
        },
        {
            "path": ["（二级）", "本次交易带来的影响"],
            "models": [{"name": "syllabus_elt"}],
            "need_syl": True,
            "share_column": True,
        },
        {
            "path": ["（二级）", "交易对手方与公司是否有关联关系"],
            "models": [{"name": "syllabus_elt"}],
            "share_column": True,
            "need_syl": True,
        },
        {"path": ["（二级）", "关联关系（如是关联交易）"], "models": [{"name": "partial_text"}], "share_column": True},
        {
            "path": ["（二级）", "交易金额"],
            "models": [{"name": "table_row", "multi": True, "multi_elements": True}, {"name": "partial_text"}],
            "unit_depend": {"金额": "单位"},
            "group": {"lookup_strategy": "lookahead"},
        },
        {
            "path": ["（二级）", "标的的账面价值"],
            "models": [
                {"name": "table_tuple", "multi_elements": True},
                {"name": "table_row", "multi_elements": True},
            ],
            "unit_depend": {"金额": "单位"},
            "group": {"lookup_strategy": "lookahead"},
        },
        {
            "path": ["（二级）", "标的评估值"],
            "models": [
                {"name": "table_row", "multi": True, "multi_elements": True},
                {
                    "name": "partial_text",
                },
            ],
            "unit_depend": {"金额": "单位"},
            "group": {"lookup_strategy": "lookahead"},
        },
        {
            "path": ["（二级）", "标的的增值率"],
            "models": [
                {"name": "table_row", "multi": True, "multi_elements": True},
            ],
            "group": {"lookup_strategy": "lookahead"},
        },
        {
            "path": ["（二级）", "定价方式"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
            "share_column": True,
        },
        {
            "path": ["（二级）", "资金来源"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
