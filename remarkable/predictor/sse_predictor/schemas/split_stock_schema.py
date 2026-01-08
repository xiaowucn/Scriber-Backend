# -*- coding: utf-8 -*-

"""Mole name: 0902 董事会审议高送转"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()

meeting_pattern = r"董事会第(.*?)次会议(.*?)以\s*\d\s*(票|名)(同意|赞成|反对|弃权)(.*?)审议通过"

predictor_options.extend(
    [
        {
            "path": ["高送转议案的主要内容"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
            "need_syl": True,
        },
        {
            "path": ["是否有减持计划"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
            "need_syl": True,
        },
        {
            "path": ["利润分配或公积金转增股本的具体比例"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["高送转提议人"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["是否控股股东"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["持股比例"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["提议理由"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["减持计划的内容"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
        },
        {
            "path": ["审议程序"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["董事否决情况"],
            "models": [
                {
                    "name": "relation_entity",
                    "relation_pattern": r"董事会第(.*?)次会议(.*?)以\s*\d\s*(票|名)(同意|赞成|反对|弃权)(.*?)",
                    "entity_options": [
                        {
                            "schema_name": "董事否决情况",
                            "patterns": [r"(?P<entity>\s*\d\s*(票|名))反对"],
                        },
                        {
                            "schema_name": "董事弃权情况",
                            "patterns": [r"(?P<entity>\s*\d\s*(票|名))弃权"],
                        },
                    ],
                }
            ],
        },
    ]
)

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
