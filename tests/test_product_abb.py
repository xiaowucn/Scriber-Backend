import pytest

from remarkable.predictor.fullgoal_predictor.models.product_abb import ETFClassifier, clear_suffixes


@pytest.mark.parametrize(
    "text, expected",
    [
        ("证券投资基金", ""),
        ("市场基金", ""),
        ("招商交易型开放式指数证券投资基金", "招商ETF"),
        ("XXX证券投资基金", "XXX"),
        ("混合型", "混合"),
        ("债券型", "债券"),
        ("股票型", "股票"),
        ("指数型", "指数"),
        ("富国基金", "基金"),
        ("富国灵活配置股票", "股票"),
        ("富国发起式基金", "基金"),
        ('富国智投基金中基金(FOF)', "智投(FOF)"),

    ],
)
def test_clear_suffixes(text, expected):
    replace_pairs = (
        (r"基金中[的得]?基金(?=[(（]?FOF[)）]?)", ""),
        (r"(.*)(?:证券投资|市场)基金$", r"\1"),
        (r"交易型开放式指数", "ETF"),
        (r"(.*联接)基金$", r"\1"),
        (r"(.*(?:混合|债券|股票|指数))型", r"\1"),
        (r"^富国", ""),
        (r"灵活配置|发起式", ""),
    )
    assert clear_suffixes(text, replace_pairs) == expected


@pytest.mark.parametrize(
    "listing_place, full_name, expected",
    [
        ("上海证券交易所", "中证500ETF", "上交所跨市场"),
        ("上海证券交易所", "上证50ETF", "上交所单市场"),
        ("深圳证券交易所", "中证500ETF", "深交所跨市场"),
    ],
)
def test_classify(listing_place, full_name, expected):
    classifier = ETFClassifier(listing_place, full_name)
    assert classifier.classify() == expected
