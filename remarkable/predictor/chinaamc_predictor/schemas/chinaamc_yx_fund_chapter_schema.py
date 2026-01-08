"""华夏营销部-标注章节对比 基金合同V1"""

predictor_options = [
    {
        "path": ["001基金合同当事人及权利义务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__基金合同当事人及权利义务",
                ],
            },
        ],
    },
    {
        "path": ["002基金份额持有人大会"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["003基金的收益与分配"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__基金.?((收益|分配)[与和]?){2}",
                ],
            },
        ],
    },
    {
        "path": ["004基金费用与税收"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__基金.?((费用|税收)[与和]?){2}",
                ],
            },
        ],
    },
    {
        "path": ["005基金的投资"],
        "pick_answer_strategy": "all",
        "models": [
            {
                "name": "syllabus_elt_v2",
                "include_title": True,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__投资范围",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "include_title": True,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__投资限制",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "include_title": True,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__侧袋机制的?实施|投资运作安排",
                ],
            },
        ],
    },
    {
        "path": ["006基金的财产"],
        "pick_answer_strategy": "all",
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__基金的?[财资]产__regex__净值",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__基金的?信息披露__regex__信息__regex__净值",
                ],
            },
        ],
    },
    {
        "path": ["007基金合同的变更、终止与基金财产的清算"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__基金合同的?((变更|终止|修改)[、与和]?){1,2}与基金财产的?清算",
                ],
            },
        ],
    },
    {
        "path": ["008争议的处理和适用的法律"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["009基金合同的效力"],
        "models": [
            {
                "name": "para_match",
                "order_by_index": True,
                "syllabus_regs": [
                    r"基金合同的?效力",
                ],
                "paragraph_pattern": [
                    r".*一式[零〇ΟOo壹贰叁肆伍陆柒捌玖拾佰仟萬億\d两一二三四五六七八九十百千万亿]+份.*",
                    r".*供.*查阅.*",
                ],
                "multi_elements": True,
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
