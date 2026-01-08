"""
128: "0507 向关联人委托贷款"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors(exclude=("公司全称"))

predictor_options.extend(
    [
        {
            "path": ["公司全称"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(0, 5)),
                    "regs": [r"(?P<dst>.*?公司)"],
                }
            ],
        },
        {
            "path": ["（二级）", "标的情况"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["（二级）", "投资金额"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "审议程序（是否要上股东大会决议）"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "董事会审议否决及弃权情况"],
            "models": [{"name": "partial_text"}],
            "sub_primary_key": ["投票情况"],
            "share_column": True,
        },
        {
            "path": ["（二级）", "其他协议主体情况（除发行人之外的协议主体名称）"],
            "models": [
                {"name": "partial_text", "multi": True},
            ],
        },
        {
            "path": ["（二级）", "是否是关联交易"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "关联关系（如是关联交易）"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "关联交易的必要性及对上市公司的影响（如是关联交易）"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["（二级）", "是否是重大资产重组"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
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
