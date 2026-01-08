from remarkable.converter.utils import date_from_text
from remarkable.pdfinsight.text_util import clear_syl_title


def test_date_from_text():
    date = date_from_text("2019年5月30日")
    assert date is not None and date.year == 2019 and date.month == 5 and date.day == 30


def test_clear_syl_title():
    samples = [
        ("(一) 一般风险", "一般风险"),
        ("(1) 一般风险", "一般风险"),
        ("第一部分 abc", "abc"),
        ("第一章 abc", "abc"),
        ("第一节 abc", "abc"),
        ("1.我是目录", "我是目录"),
        ("16、应急处置预案的风险", "应急处置预案的风险"),
        ("第二部分、释义", "释义"),
        ("5、一年内到期的非流动资产和长期应收款", "一年内到期的非流动资产和长期应收款"),

    ]

    for syl, cleaned_syl in samples:
        assert clear_syl_title(syl) == cleaned_syl
