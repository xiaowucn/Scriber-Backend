"""
44: "08 申请破产清算公告"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors(exclude=("公司简称",))
predictor_options.extend(
    [
        {
            "path": ["公司简称"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(0, 3)),
                    "regs": [
                        r"(?<=股票简称[:：])(?P<dst>.*?)(?=\s?(公告|证券|股票|编[号码]|债券|\|))",
                        r"(?<=简称[:：])(?P<dst>.*?)(?=\s?(公告|证券|股票|编[号码]|债券|\|))",
                        r"简称[:：](?P<dst>.*)(?!\s+$)",
                    ],
                }
            ],
        },
        {
            "path": ["申请破产清算公司名称"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["住所地"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["组织机构代码"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["法定代表人"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["破产清算申请事由"],
            "models": [
                {"name": "partial_text", "multi": True, "multi_elements": True},
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["与上市公司关系"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["实际控制人或控股股东是否涉及破产清算"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["法院名称"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["裁定书编号"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["裁定时间"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["决定书编号"],
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
