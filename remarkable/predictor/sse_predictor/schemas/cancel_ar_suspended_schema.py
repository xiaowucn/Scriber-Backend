"""
110: "1603 取消重大资产重组并复牌"
"""

from remarkable.predictor.sse_predictor.predictor_config import SPECIAL_ATTR_PATTERNS, filter_predictors

predictor_options = filter_predictors()
predictor_options.extend(
    [
        {
            "path": ["停复牌原因描述"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["停牌时间"],
            "models": [
                {"name": "partial_text", "regs": ["股票[已将]?[自于从]%s.*停牌" % SPECIAL_ATTR_PATTERNS["date"][0]]},
            ],
        },
        {
            "path": ["复牌时间"],
            "models": [
                {"name": "partial_text", "regs": ["股票将?[自于从]%s.*复牌" % SPECIAL_ATTR_PATTERNS["date"][0]]},
            ],
        },
    ]
)

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
