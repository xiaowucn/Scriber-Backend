"""
118: "0426 与私募基金合作投资"

todo: multi_para（基金决策程序/利润分配）
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors(exclude=("公司全称",))
predictor_options.extend(
    [
        {
            "path": ["公司全称"],
            "models": [
                {
                    "name": "fixed_position",
                    "regs": [r"(?P<dst>.*?公司)"],
                    "use_crude_answer": True,
                }
            ],
        },
        {"path": ["(二级)", "合作对手方"], "models": [{"name": "partial_text"}]},
        {"path": ["(二级)", "出资方式"], "models": [{"name": "partial_text"}]},
        {
            "path": [
                "投资金额",
            ],
            "models": [
                {"name": "partial_text"},
            ],
            "unit_depend": {"金额": "单位"},
        },
        {
            "path": [
                "基金管理人情况",
            ],
            "models": [{"name": "partial_text"}],
        },
        {
            "path": [
                "基金管理人情况",
            ],
            "models": [{"name": "partial_text"}],
        },
        {
            "path": [
                "基金存续期和退出情况",
            ],
            "models": [{"name": "partial_text"}],
        },
        {
            "path": [
                "基金投向",
            ],
            "models": [{"name": "partial_text"}],
        },
        {
            "path": [
                "基金决策程序",
            ],
            "models": [{"name": "score_filter", "threshold": 0.3, "aim_types": ["PARAGRAPH"]}],
        },
        {
            "path": [
                "利润分配",
            ],
            "models": [{"name": "score_filter", "threshold": 0.3, "aim_types": ["PARAGRAPH"]}],
        },
        {
            "path": [
                "对公司影响",
            ],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": [
                "风险提示",
            ],
            "models": [
                {
                    "name": "syllabus_elt",
                },
                {"name": "partial_text"},
            ],
        },
        {
            "path": [
                "合同期限",
            ],
            "models": [{"name": "partial_text"}],
        },
    ]
)

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
