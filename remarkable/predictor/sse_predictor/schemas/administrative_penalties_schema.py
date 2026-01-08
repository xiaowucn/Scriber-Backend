"""
56  "15 临时公告-行政处罚"

"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()
predictor_options.extend(
    [
        {
            "path": ["处罚部门"],
            "models": [
                {"name": "partial_text"},
            ],
        },
        {
            "path": ["（二级）"],
            "models": [
                {
                    "name": "partial_text",
                    "multi": True,
                    "multi_elements": True,
                },
            ],
            "sub_primary_key": ["被处罚方"],
        },
        {
            "path": ["（二级）", "与上市公司关系"],
            "models": [
                {
                    "name": "partial_text",
                    "multi": True,
                    "multi_elements": True,
                },
            ],
            "group": {"lookup_strategy": "both", "range_num": 10},
        },
        {
            "path": ["（二级）", "处罚类型"],
            "models": [
                {
                    "name": "partial_text",
                    "multi": True,
                    "multi_elements": True,
                },
            ],
            "group": {"lookup_strategy": "lookahead", "range_num": 10},
        },
        {
            "path": ["（二级）", "处罚金额"],
            "models": [
                {
                    "name": "partial_text",
                    "multi": True,
                    "multi_elements": True,
                },
            ],
            "group": {"lookup_strategy": "lookahead", "range_num": 10},
        },
    ]
)

prophet_config = {
    "depends": {},
    # 'merge_schema_answers': True,
    "predictor_options": predictor_options,
}
