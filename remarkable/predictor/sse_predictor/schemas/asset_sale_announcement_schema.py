"""
schema id: 83
schema name: "10 出售资产公告"
TODO:
    1. 交易双方, 定位不够精准, partial text模型拿不到答案
    2. 交易标的情况, 子属性所在位置既有段落也有表格, 在表格内的位置也不固定, 如基准日
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors(exclude=("公司全称",))

predictor_options.extend(
    [
        {
            "path": ["公司全称"],
            "models": [
                {"name": "fixed_position", "positions": (0,), "regs": [r"(?P<dst>.*?公司)"], "use_crude_answer": True}
            ],
        },
        {
            "path": ["交易详情"],
            "sub_primary_key": [
                "年度",
                "标的名称",
            ],
            "models": [
                {
                    "name": "partial_text",
                    "multi": True,
                },
            ],
            "unit_depend": {"资产总额": "单位"},
        },
        {
            "path": ["交易详情", "年度"],
            "models": [
                {
                    "name": "partial_text",
                    "multi": True,
                },
            ],
        },
        {
            "path": ["交易详情", "转让方"],
            "models": [
                {
                    "name": "partial_text",
                    "multi": True,
                },
            ],
            "share_column": True,
        },
        {
            "path": ["交易详情", "受让方"],
            "models": [
                {
                    "name": "partial_text",
                    "multi": True,
                },
            ],
        },
        {
            "path": ["交易详情", "标的名称"],
            "models": [
                {
                    "name": "partial_text",
                    "multi": True,
                },
            ],
        },
        {
            "path": ["交易详情", "资产总额"],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                    "multi_elements": True,
                },
            ],
            "group": {"lookup_strategy": "lookahead", "range_num": 10},
        },
        {
            "path": ["交易详情", "负债总额"],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                    "multi_elements": True,
                },
            ],
            "group": {"lookup_strategy": "lookahead", "range_num": 10},
        },
        {
            "path": ["交易详情", "净资产"],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                    "multi_elements": True,
                },
            ],
            "group": {"lookup_strategy": "lookahead", "range_num": 10},
        },
        {
            "path": ["交易详情", "营业收入"],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                    "multi_elements": True,
                },
            ],
            "group": {"lookup_strategy": "lookahead", "range_num": 10},
        },
        {
            "path": ["交易详情", "净利润"],
            "models": [
                {
                    "name": "table_row",
                    "multi": True,
                    "multi_elements": True,
                },
            ],
            "group": {"lookup_strategy": "lookahead", "range_num": 10},
        },
        # {
        #     "path": ["交易详情", "单位"],
        #     "models": [{"name": "partial_text", "regs": [r'单位[:：]?(?P<dst>.*元)'], "multi": True,},],
        # },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
