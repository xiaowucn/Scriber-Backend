# -*- coding: utf-8 -*-

"""
Mole id: 131
Mole name: 2604 计提大额资产减值准备
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()


predictor_options.extend(
    [
        {
            "path": ["减值情况"],
            "sub_primary_key": ["计提科目"],
            # 'models': [
            #     {
            #         'name': 'table_row',
            #         'multi': True,
            #     },
            # ],
        },
        {
            "path": ["减值情况", "计提科目"],
            "models": [
                # {
                #     'name': 'para_match',
                #     'paragraph_pattern': r'（[一二三四五六七八九十]{1,2}）.*?(减值|坏账准备)',
                #     'multi': True,
                #     'multi_elements': True,
                # },
                {
                    "name": "partial_text",
                    "multi": True,
                    "multi_elements": True,
                },
                {
                    "name": "table_row",
                    "multi": True,
                },
            ],
        },
        {
            "path": ["减值情况", "计提大额资产减值准备金额"],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                },
                {
                    "name": "partial_text",
                    "multi": True,
                    "multi_elements": True,
                },
            ],
            "group": {"lookup_strategy": "both"},
        },
        {
            "path": ["减值情况", "单位"],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [r"单位[:：]?(?P<dst>.*元)"],
                },
            ],
            # 'share_column': True,
            "group": {"lookup_strategy": "both"},
        },
        {
            "path": ["减值情况", "原因及合理性说明"],
            "models": [
                {"name": "syllabus_elt", "multi": True, "order_by": "level", "reverse": True},
                {
                    "name": "partial_text",
                    "regs": ["(?P<dst>(因|为了?).*?减值(测试|准备))"],
                    "multi": True,
                },
            ],
            # 'pick_answer_strategy': 'all',
            "group": {"lookup_strategy": "both"},
        },
        {
            "path": ["对当年利润影响数"],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [],
                    "multi": True,
                },
                {"name": "syllabus_elt", "regs": []},
                # {'name': 'para_match', 'paragraph_pattern': r'本激励计划.*需要激励的人员',},
            ],
        },
    ]
)

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
