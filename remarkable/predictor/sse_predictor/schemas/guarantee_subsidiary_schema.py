from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()

"""
53: 0602 为控股子公司提供担保

todo：金额/数字
"""

predictor_options.extend(
    [
        {
            "path": ["（二级）", "被担保人名称"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "被担保人是否是关联方及关联关系"],
            "models": [
                {
                    "name": "enum_value",
                    "simple": "是",
                },
            ],
        },  # 只需要枚举值的情况
        {
            "path": ["（二级）", "担保金额"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "担保方式"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "担保类型"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "担保期限"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "是否有反担保"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "上市公司及其控股子公司对外担保总额",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["上市公司及其控股子公司对外担保总额占净资产比例"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["上市公司对控股子公司提供的担保总额"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["上市公司对控股子公司提供的担保总额占净资产比例"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["上市公司及其控股子公司逾期担保累计金额"],
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
