"""
54: "14 年报-排污"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

anchor_regs = r"属于环境保护部门公布的重点排污单位的公司及其重要子公司的环保情况说明|重点排污单位之外的公司的环保情况说明|排污信息"
paragraph_pattern = r"√不?适用|排[污放]信息"

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
            "path": ["是否排污"],
            "models": [
                {
                    "name": "para_match",
                    "paragraph_pattern": paragraph_pattern,
                    "anchor_regs": anchor_regs,
                    "multi": True,
                    "multi_elements": True,
                    "include_anchor": True,
                    "enum_from_multi_element": True,
                },
                {
                    "name": "syllabus_elt",
                },
            ],
        },
    ]
)

prophet_config = {
    "depends": {},
    # 'merge_schema_answers': True,
    "predictor_options": predictor_options,
}
