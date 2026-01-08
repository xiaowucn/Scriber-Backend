"""
schema id: 48
schema name: "0806 业绩快报"
TODO:
    1. 主要财务数据和指标单位, 需要一个从表格or段落中提取出单位的通用方法
    2. 业绩快报期间, 从表格中提取特定单元格内容
    3. 业绩快报, 只取2所在列的内容
"""

from remarkable.predictor.sse_predictor.predictor_config import SPECIAL_ATTR_PATTERNS, filter_predictors

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
            "path": ["公告日期"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(-10, 0))[::-1],
                    "regs": SPECIAL_ATTR_PATTERNS["date"],
                }
            ],
        },
        # {"path": ["业绩快报期间"], "models": [{'name': 'partial_text', }, ], },
        {
            "path": ["业绩快报"],
            "sub_primary_key": ["主要财务数据和指标名称"],
            "unit_depend": {"主要财务数据和指标": "主要财务数据和指标单位"},
            "models": [{"name": "table_row", "multi": True, "neglect_patterns": [r"项目"], "lazy_match": True}],
        },
        {
            "path": ["增减变动的原因"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
