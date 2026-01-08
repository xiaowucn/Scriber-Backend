"""
105: "1906 可转债付息"
"""

from remarkable.predictor.sse_predictor.predictor_config import SPECIAL_ATTR_PATTERNS, filter_predictors

predictor_options = filter_predictors(exclude=("公司全称",))
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
            "path": ["（二级）", "事项类别"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "公告日期"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "债权登记日"],
            "models": [
                {"name": "partial_text", "regs": ["登记日[：:]%s" % SPECIAL_ATTR_PATTERNS["date"][0]]},
            ],
        },
        {
            "path": ["（二级）", "付息日"],
            "models": [
                {"name": "partial_text", "regs": ["[付兑]息.*日[：:]%s" % SPECIAL_ATTR_PATTERNS["date"][0]]},
            ],
        },
        {
            "path": ["（二级）", "兑付日"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "公告链接"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "所得税代扣代缴方式"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
    ]
)

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
