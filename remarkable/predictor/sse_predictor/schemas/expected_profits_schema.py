"""
40: "0801 预盈"
43: "0803 预亏"
45: "0804 业绩大幅提升"
46: "0805 业绩大幅下降"
"""

from remarkable.predictor.sse_predictor.predictor_config import SPECIAL_ATTR_PATTERNS, filter_predictors

predictor_options = filter_predictors()

predictor_options.extend(
    [
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
            "path": ["（二级）", "业绩预告区间"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(3, 20)),
                    "regs": [r"(?P<dst>2.*至.*日)"],
                }
            ],
        },
        {
            "path": ["（二级）", "业绩预告的类别"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["（二级）", "本期扣非前归属于母公司的净利润"],
            "models": [
                {
                    "name": "partial_text",
                    "regs": SPECIAL_ATTR_PATTERNS["<金额单位>"],
                }
            ],
        },
        {
            "path": ["（二级）", "本期扣非后归属于母公司的净利润"],
            "models": [
                {
                    "name": "partial_text",
                    "regs": SPECIAL_ATTR_PATTERNS["<金额单位>"],
                }
            ],
        },
        {
            "path": ["（二级）", "本期营业收入"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["（二级）", "本期净资产"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["（二级）", "上年同期扣非前归属于母公司的净利润"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["（二级）", "上年同期扣非后归属于母公司的净利润"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["（二级）", "上年同期营业收入"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["（二级）", "上年同期净资产"],
            "models": [
                {
                    "name": "partial_text",
                }
            ],
        },
        {
            "path": ["（二级）", "本期业绩变化的原因"],
            "models": [
                {
                    "name": "syllabus_elt",
                }
            ],
        },
    ]
)

prophet_config = {
    "depends": {},
    # 'merge_schema_answers': True,
    "predictor_options": predictor_options,
}
