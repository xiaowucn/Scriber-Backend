"""
88 : "0503 向关联人购买资产"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()

predictor_options.extend(
    [
        {
            "path": ["（二级）"],
            "sub_primary_key": ["出售或购买的标的名称（key）"],
            "models": [{"name": "table_row", "multi": True}],
        },
        {
            "path": ["（二级）", "交易事项"],
            "models": [
                {
                    "name": "para_match",
                    "paragraph_pattern": r"向.*?(?P<content>购买资产).*?公告",
                    "content_pattern": r"向.*?(?P<content>购买资产).*?公告",
                }
            ],
            "share_column": True,
        },
        {
            "path": ["（二级）", "出售或购买的标的名称（key）"],
            "models": [
                {"name": "partial_text", "出售或购买的标的名称（key）": {"regs": ["拟购买(?P<dst>.*?)[,，.。！]"]}}
            ],
        },
        {"path": ["（二级）", "出售或购买的标的名称（补充）"], "models": [{"name": "partial_text"}]},
        {"path": ["（二级）", "出售或购买的标的类别"], "models": [{"name": "partial_text"}]},
        {"path": ["（二级）", "是否属于境外资产"], "models": [{"name": "partial_text"}]},
        {
            "path": ["（二级）", "交易金额"],
            "models": [
                {"name": "partial_text", "交易金额": {"regs": [r"价格参照评估价.*?由.*?确定为(?P<dst>[\s\d,\.]*)万元"]}}
            ],
        },
        {
            "path": ["（二级）", "定价方式"],
            "models": [{"name": "syllabus_elt"}, {"name": "partial_text"}],
            "multi": True,
            "share_column": True,
        },
        {"path": ["（二级）", "标的的账面价值"], "models": [{"name": "partial_text"}]},
        {"path": ["（二级）", "标的评估值"], "models": [{"name": "partial_text"}]},
        {"path": ["（二级）", "标的的增值率"], "models": [{"name": "partial_text"}]},
        {"path": ["（二级）", "交易对手方"], "models": [{"name": "partial_text"}], "share_column": True},
        {
            "path": ["（二级）", "交易对手方与公司是否有关联关系"],
            "models": [{"name": "para_match", "paragraph_pattern": r"构成.*?关联交易"}, {"name": "partial_text"}],
            "share_column": True,
        },
        {
            "path": ["（二级）", "关联关系"],
            "models": [
                {
                    "name": "para_match",
                    # 'paragraph_pattern': r'(?P<content>构成.*?关联交易)',
                    "paragraph_pattern": r"(?P<content>(.*?持有.*?股[份权].*?股东|.*?持有.*股[份权]|.*?控股股东))",
                },
                {"name": "partial_text"},
            ],
            "share_column": True,
        },
        {
            "path": ["（二级）", "关联交易的必要性及对上市公司的影响（如是关联交易）"],
            "models": [{"name": "partial_text"}, {"name": "syllabus_elt"}],
            "share_column": True,
        },
        {"path": ["（二级）", "本次交易带来的影响"], "models": [{"name": "partial_text"}], "share_column": True},
        {"path": ["（二级）", "资金来源"], "models": [{"name": "partial_text"}], "share_column": True},
        {
            "path": ["（二级）", "董事会审议反对及弃权情况"],
            "models": [{"name": "partial_text"}],
            "sub_primary_key": ["投票情况"],
            "share_column": True,
        },
        {
            "path": ["（二级）", "董事会审议反对及弃权情况", "投票情况"],
            "models": [{"name": "partial_text"}],
            "share_column": True,
        },
        {
            "path": ["（二级）", "董事会审议反对及弃权情况", "姓名"],
            "models": [{"name": "partial_text"}],
            "share_column": True,
        },
        {
            "path": ["（二级）", "董事会审议反对及弃权情况", "理由"],
            "models": [{"name": "partial_text"}],
            "share_column": True,
        },
    ]
)

prophet_config = {
    "depends": {"交易事项": ["出售或购买的标的名称（key）"]},
    # 'merge_schema_answers': True,
    "predictor_options": predictor_options,
}
