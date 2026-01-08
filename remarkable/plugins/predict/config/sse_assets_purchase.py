from remarkable.plugins.predict.predictor import AIAnswerPredictor

predictors = [
    {
        "path": ["公司全称"],
        "model": "fixed_position",
        "positions": list(range(0, 5)),
        "regs": [
            r"(?P<dst>.*公司)",
        ],
    },
    {
        "path": ["公司简称"],
        "model": "fixed_position",
        "positions": list(range(0, 3)),
        "regs": [
            r"(?<=简称[:：])(?P<dst>.*?)(?=\s?(公告|证券|股票|编[号码]|上市))",
        ],
    },
    {
        "path": ["公司代码"],
        "model": "fixed_position",
        "positions": list(range(0, 3)),
        "regs": [
            r"(?<=代码[:：])(?P<dst>\d{6})",
        ],
    },
    # todo：公告时间、公告编号
    {
        "path": ["（二级）", "出售或购买的标的名称（key）"],
        "model": "partial_text",
        "regs": [
            r"(?:(?:通过|以).*?方式)?"
            r"(?:向.*?(?:非?公开发行股[份权票]))?"
            r"(?:购买|收购|置入|采购|[获取]得|对价受让|标的(?:公司|资产)?[为是]?|[及和与、](?!(?:支付|发行)))的?"
            r"(?:(?:[^。；、]*?)?其?所?(?:合计)?持有?的?)?\s*"
            r"(?:(?:.*?)评估的)?"
            r"(?:(?:标的)?(?:公司|资产)?[为是]?)?"
            r"(([^，。、；]{2,20}?)(?:（.*）)?的?(?:[合总]计)?的?\s*(?:[\d,]+(?:\.\d*)?%?\s*(?:的?\s*(?:股(?:普通股)?)?股[权份])"
            r"|(?:全部)?股[权份]中?的\s*[\d,]+(?:\.\d*)?%))",
        ],
    },
]


class AssetsPurchase(AIAnswerPredictor):
    """
    22：0401 购买资产
    """

    def __init__(self, *args, **kwargs):
        kwargs["predictors"] = predictors
        # kwargs["default_model"] = "partial_text"
        super(AssetsPurchase, self).__init__(*args, **kwargs)
