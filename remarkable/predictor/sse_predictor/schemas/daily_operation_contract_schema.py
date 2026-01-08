"""
70: "0419 签订日常经营合同"
    todo:
    董事会审议否决及弃权情况
    "投票情况",
    "姓名",
    "理由"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()

predictor_options.extend(
    [
        {
            "path": ["（二级）", "合同类型"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "合同金额", "金额"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "合同金额", "单位"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "合同生效条件"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "支付方式"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "合同履行期限"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "合同标的情况", "名称"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "合同标的情况", "数量-金额"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "合同标的情况", "数量-单位"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "合同标的情况", "质量"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "合同标的情况", "价格-金额"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "合同标的情况", "价格-单位"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "合同对方名称"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "合同对方是否为关联方"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "关联关系"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "合同履行对上市公司的影响"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
            "need_syl": True,
        },
        {
            "path": ["（二级）", "审议程序情况（是否要上股东大会决议）"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": ["（二级）", "合同履行对上市公司的影响"],
            "models": [
                {
                    "name": "syllabus_elt",
                },
            ],
            "need_syl": True,
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
