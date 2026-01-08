"""
schema id: 78
schema name: "2101 股权激励计划草案摘要"
"""

from remarkable.predictor.sse_predictor.predictor_config import SPECIAL_ATTR_PATTERNS, filter_predictors

predictor_options = filter_predictors(exclude=("公司全称", "公告时间"))

predictor_options.extend(
    [
        {
            "path": ["公司全称"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": (0,),
                    "regs": [r"(?P<dst>.*?公司)"],
                    "use_crude_answer": True,
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
            "path": ["激励对象"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["激励方式"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["股份来源"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["股份激励总数"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["股份激励总数单位"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["股份激励占公司股本总额比例"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["股权激励计划的有效期"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["普通限制性股票授予价格"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["普通限制性股票授予价格单位"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["普通限制性股票授予价格确定方法"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["普通限制性股票授予价格确定方法"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["普通限制性股票授予条件"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["普通限制性股票解锁条件"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["限制性股票单元授予价格"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["限制性股票单元授予价格单位"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["限制性股票单元授予价格确定方法"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["限制性股票单元授予条件"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["限制性股票单元归属条件"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["股票期权行权价格"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["股票期权行权价格单位"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["股票期权行权价格的确定方法"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["股票期权授予条件"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["股票期权行权条件"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["对公司各期经营业绩的影响"],
            "models": [
                {"name": "syllabus_elt", "table_only": True},
            ],
        },
    ]
)

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
