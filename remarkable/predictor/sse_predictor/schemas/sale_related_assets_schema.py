"""
89 : "0504 向关联人出售资产"
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
                        r"(?<=简称[:：])(?P<dst>.*?)(?=\s?(公告|证券|股票|编[号码]|债券|\|))",
                        r"简称[:：](?P<dst>.*)",
                    ],
                }
            ],
        },
        {
            "path": [
                "（二级）",
            ],
            "sub_primary_key": ["出售或购买的标的名称（key）"],
        },
        {
            "path": [
                "（二级）",
                "交易事项",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "（二级）",
                "出售或购买的标的名称（key）",
            ],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [
                        r"拟购买(?P<dst>.*?)[,，.。！]",
                        r"同意将(?P<dst>.*?)以评估价",
                        r"(拟将持有的|全资孙公司)(?P<dst>.*?公司)(?=.*股)",
                        r"拟将其(?P<dst>.*?)转让",
                        r"出售(?P<dst>.*?)(?=[。\s])",
                    ],
                },
                {
                    "name": "table_row",
                },
            ],
        },
        {
            "path": [
                "（二级）",
                "出售或购买的标的名称（补充）",
            ],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [
                        r"(拟将持有的|全资孙公司).*?公司(?P<dst>.*股权)",
                    ],
                },
            ],
        },
        {
            "path": [
                "（二级）",
                "出售或购买的标的类别",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "（二级）",
                "是否属于境外资产",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "（二级）",
                "交易金额",
            ],
            "sub_primary_key": [
                "交易金额",
                "金额",
            ],
        },
        {
            "path": [
                "（二级）",
                "交易金额",
                "金额",
            ],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [r"价格参照评估价.*?由.*?确定为(?P<dst>[\s\d,\.]*)万元"],
                },
            ],
        },
        {
            "path": [
                "（二级）",
                "交易金额",
                "单位",
            ],
            "models": [
                {
                    "name": "partial_text",
                    "regs": [r"价格参照评估价.*?由.*?确定为.*?(?P<dst>[万亿]?元)"],
                },
            ],
        },
        {
            "path": [
                "（二级）",
                "定价方式",
            ],
            "models": [
                {
                    "name": "syllabus_elt",
                    "include_title": True,
                },
                {
                    "name": "partial_text",
                },
            ],
            "multi": True,
            "share_column": True,
        },
        {
            "path": [
                "（二级）",
                "标的的账面价值",
                "金额",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "（二级）",
                "标的的账面价值",
                "单位",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "（二级）",
                "标的评估值",
                "金额",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "（二级）",
                "标的评估值",
                "单位",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
        },
        {
            "path": [
                "（二级）",
                "标的的增值率",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
                {
                    "name": "table_tuple",
                },
            ],
            "share_column": True,
        },
        {
            "path": [
                "（二级）",
                "交易对手方",
            ],
            "models": [
                {"name": "partial_text", "regs": [r"转让给公司控股股东(?P<dst>.*公司)"]},
            ],
            "share_column": True,
        },
        {
            "path": [
                "（二级）",
                "交易对手方与公司是否有关联关系",
            ],
            "models": [
                {
                    "name": "para_match",
                    "paragraph_pattern": r"[构购]成.*?关联交易",
                },
                {
                    "name": "partial_text",
                },
            ],
            "share_column": True,
        },
        {
            "path": [
                "（二级）",
                "关联关系",
            ],
            "models": [
                {
                    "name": "para_match",
                    # 'paragraph_pattern': r'(?P<content>构成.*?关联交易)',
                    "paragraph_pattern": r"(?P<content>(.*?持有.*?股[份权].*?股东|.*?持有.*股[份权]|.*?控股股东))",
                },
                {
                    "name": "partial_text",
                },
            ],
            "share_column": True,
        },
        {
            "path": [
                "（二级）",
                "关联交易的必要性及对上市公司的影响（如是关联交易）",
            ],
            "models": [
                {
                    "name": "syllabus_elt",
                    "include_title": True,
                },
                {
                    "name": "partial_text",
                },
            ],
            "share_column": True,
        },
        {
            "path": [
                "（二级）",
                "本次交易带来的影响",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
            "share_column": True,
        },
        {
            "path": [
                "（二级）",
                "资金来源",
            ],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
            "share_column": True,
        },
        {
            "path": ["（二级）", "董事会审议反对及弃权情况"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
            "sub_primary_key": ["投票情况"],
            "share_column": True,
        },
        {
            "path": ["（二级）", "董事会审议反对及弃权情况", "投票情况"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
            "share_column": True,
        },
        {
            "path": ["（二级）", "董事会审议反对及弃权情况", "姓名"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
            "share_column": True,
        },
        {
            "path": ["（二级）", "董事会审议反对及弃权情况", "理由"],
            "models": [
                {
                    "name": "partial_text",
                },
            ],
            "share_column": True,
        },
    ]
)

prophet_config = {
    "depends": {},
    # 'merge_schema_answers': True,
    "predictor_options": predictor_options,
}
