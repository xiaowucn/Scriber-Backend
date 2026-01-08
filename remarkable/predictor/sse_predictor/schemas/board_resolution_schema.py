"""
schema id: 62
schema name: "19 董事会决议"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()

resolution_title_pattern = r"(?P<content>(关于)?[^《》]*的议案)"

predictor_options.extend(
    [
        {
            "path": ["应到人数"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": (0,),
                    "regs": [r"(?P<dst>\d+)"],
                    "anchor_regs": [r"(应|现有)[^,，.。]*[名人个]"],
                    "use_crude_answer": True,
                }
            ],
        },
        {
            "path": ["实到人数"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": (0,),
                    "regs": [r"(?P<dst>\d+)"],
                    "anchor_regs": [
                        r"实[^,，.。]*[名人个]",
                        r"\d+[名人个].*(?<=[全都])[^.。]*",
                    ],  # 实到11人  # 公司现有5名监事，全体监事参加会议
                    "use_crude_answer": True,
                }
            ],
        },
        {"path": ["（决议内容）"], "sub_primary_key": ["议案"]},
        {
            "path": ["（决议内容）", "议案"],
            "models": [
                {
                    "name": "para_match",
                    "paragraph_pattern": resolution_title_pattern,
                    "content_pattern": resolution_title_pattern,
                    "multi_elements": True,
                }
            ],
        },
        {
            "path": ["（决议内容）", "同意"],
            "models": [
                {
                    "name": "relation_entity",
                    "relation_pattern": [r"表决(结果|情况)：", "以.*?通过.*?议案"],
                    "entity_options": [
                        {
                            "schema_name": "同意",
                            "patterns": [r"(同意|赞成)票?(?P<entity>\s*\d\s*票)", r"(?P<entity>\s*\d\s*票)(同意|赞成)"],
                        },
                        {
                            "schema_name": "反对",
                            "patterns": [r"反对票?(?P<entity>\s*\d\s*票)", r"(?P<entity>\s*\d\s*票)反对"],
                        },
                        {
                            "schema_name": "弃权",
                            "patterns": [r"弃权票?(?P<entity>\s*\d\s*票)", r"(?P<entity>\s*\d\s*票)弃权"],
                        },
                    ],
                    "multi_elements": True,
                }
            ],
            "group": {"lookup_strategy": "lookahead"},
        },
    ]
)

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
