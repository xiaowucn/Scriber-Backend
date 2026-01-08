"""
schema id: 41
schema name: "04 监事会决议公告"
"""

from remarkable.predictor.sse_predictor.predictor_config import SPECIAL_ATTR_PATTERNS, filter_predictors

predictor_options = filter_predictors(exclude=("公告编号", "公告时间"))

resolution_title_pattern = r"(?P<content>关于.*的议案)"

predictor_options.extend(
    [
        {
            "path": ["公告时间"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(-10, 0))[::-1],
                    "regs": SPECIAL_ATTR_PATTERNS["anno_time"],
                }
            ],
        },
        {
            "path": ["公告编号"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": list(range(0, 3)),
                    "regs": [r"(公告)?编号[:：](?P<dst>临?[\d\-\s－—【】]*)"],
                }
            ],
        },
        {
            "path": ["会议名称"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["监事会召开日期"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": (0,),
                    "regs": SPECIAL_ATTR_PATTERNS["date"],
                    "anchor_regs": [r"[在于][^,，.。]*在[^,，.。]*开", r"[在于][^,，.。]*开"],
                    "use_crude_answer": True,
                }
            ],
        },
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
                        r"实[^,，.。]*[名人个](?!别及连带责任)",
                        r"\d+[名人个].*(?<=[全都])[^.。]*",
                    ],  # 实到11人  # 公司现有5名监事，全体监事参加会议
                    "use_crude_answer": True,
                }
            ],
        },
        {"path": ["（二级）"], "sub_primary_key": ["议案名称"]},
        {
            "path": ["（二级）", "议案名称"],
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
            "path": ["（二级）", "是否通过"],
            "models": [
                {
                    "name": "partial_text",
                    "multi": True,
                    "multi_elements": True,
                }
            ],
            "group": {"lookup_strategy": "lookahead"},
        },
        {
            "path": ["（二级）", "同意"],
            "models": [
                {
                    "name": "relation_entity",
                    "relation_pattern": r"表决(结果|情况)：",
                    "entity_options": [
                        {
                            "schema_name": "同意",
                            "patterns": [r"(同意|赞成)(?P<entity>\s*\d\s*票)", r"(?P<entity>\s*\d\s*票)(同意|赞成)"],
                        },
                        {
                            "schema_name": "反对",
                            "patterns": [r"反对(?P<entity>\s*\d\s*票)", r"(?P<entity>\s*\d\s*票)反对"],
                        },
                        {
                            "schema_name": "弃权",
                            "patterns": [r"弃权(?P<entity>\s*\d\s*票)", r"(?P<entity>\s*\d\s*票)弃权"],
                        },
                        {
                            "schema_name": "是否通过",
                            "patterns": [r"(?P<entity>(同意|赞成)?\s*\d\s*票(同意|赞成)?.*反?对?(\s*\d\s*票)?)"],
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
