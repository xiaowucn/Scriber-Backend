import pytest

from remarkable.converter.csc_octopus.data_formater import (
    MoneyUnit,
    PeriodUnit,
    date_format,
    split_num_and_unit,
    transfer_to_number,
)

@pytest.fixture
def mock_env(monkeypatch):
    prefix = "SCRIBER_CONFIG_"
    monkeypatch.setenv(f"{prefix}CLIENT_CONTENT_LANGUAGE", "zh_CN")


def test_date_format(mock_env):
    cases = [
        {"text": "2012/08/2", "fmt": "%Y年%m月%d日", "result": "2012年08月02日"},
        {"text": "2012-08-2", "fmt": "%Y年%m月%d日", "result": "2012年08月02日"},
        {"text": "2012年8月12日", "fmt": "%Y年%m月%d日", "result": "2012年08月12日"},
        {"text": "2012年8月12日", "fmt": "%Y-%m-%d", "result": "2012-08-12"},
        {"text": "2012年8月12日", "fmt": "%m-%d", "result": "08-12"},
        {"text": "8月12日", "fmt": "%m-%d", "result": "08-12"},
        {"text": "8月12日", "fmt": "%Y-%m-%d", "result": "1900-08-12"},
        {"text": "20 12年 8月1 2日  ", "fmt": "%Y-%m-%d", "result": "2012-08-12"},
        {"text": "    201 2年8月12日", "fmt": "%m-%d", "result": "08-12"},
        {"text": "8月1    2日", "fmt": "%m-%d", "result": "08-12"},
        {"text": "    8月    12日", "fmt": "%Y-%m-%d", "result": "1900-08-12"},
        {"text": "招标时间:2012年8月12日", "fmt": "%Y-%m-%d", "result": "2012-08-12"},
        {"text": "招标日期: 2012年8月 12日", "fmt": "%Y-%m-%d", "result": "2012-08-12"},
        {"text": "招标日期:  8月 12日", "fmt": "%m-%d", "result": "08-12"},
    ]
    for case in cases:
        assert date_format(case["text"], case["fmt"]) == case["result"]


def test_transfer_to_number(mock_env):
    cases = [
        {"text": "本次采用按月付息方式支付利息", "num": 1},
        {"text": "付息方式：按季付息，", "num": 2},
        {"text": "。按年付息，每年固定时间", "num": 3},
        {"text": "利息到期偿还", "num": 5},
        {"text": "利息每半年付息", "num": 4},
        {"text": "付息方式：其他付息", "num": 6},
        {"text": "采用其他方式付息", "num": 6},
        {"text": "采用修正的多重价格招标方式", "num": 3},
        {"text": "招标方式。采用单一价格招标方式，标的为利率。", "num": 1},
    ]
    for case in cases:
        assert transfer_to_number(case["text"]) == case["num"]


def test_split_num_and_unit(mock_env):
    cases = [
        {"text": "160亿元", "enum": MoneyUnit, "num": "160", "unit": MoneyUnit.HUNDRED_MILLION_YUAN.value},
        {"text": "  1  60 亿 元 000 ", "enum": MoneyUnit, "num": "160", "unit": MoneyUnit.HUNDRED_MILLION_YUAN.value},
        {"text": "  1  60 元 000 ", "enum": MoneyUnit, "num": "160", "unit": MoneyUnit.YUAN.value},
        {"text": "  1  60 万元", "enum": MoneyUnit, "num": "0.016", "unit": MoneyUnit.HUNDRED_MILLION_YUAN.value},
        {"text": "  25.5 亿 元 000 ", "enum": MoneyUnit, "num": "25.5", "unit": MoneyUnit.HUNDRED_MILLION_YUAN.value},
        {"text": "  0.85 亿元 000 ", "enum": MoneyUnit, "num": "0.85", "unit": MoneyUnit.HUNDRED_MILLION_YUAN.value},
        {
            "text": " 25.20 0.85 亿元 000 ",
            "enum": MoneyUnit,
            "num": "200.85",
            "unit": MoneyUnit.HUNDRED_MILLION_YUAN.value,
        },
        {"text": "  1  60 元 36 月", "enum": MoneyUnit, "num": "160", "unit": MoneyUnit.YUAN.value},
        {"text": "  1  60 元 36 月", "enum": PeriodUnit, "num": "36", "unit": None},
        {"text": "  1  60 元 5 年", "enum": PeriodUnit, "num": "5", "unit": PeriodUnit.YEAR.value},
        {"text": " 100 日", "enum": PeriodUnit, "num": "100", "unit": PeriodUnit.DAY.value},
        {"text": " 100 天", "enum": PeriodUnit, "num": "100", "unit": PeriodUnit.DAY.value},
        {"text": " 5 年", "enum": PeriodUnit, "num": "5", "unit": PeriodUnit.YEAR.value},
        {"text": " 36 月", "enum": PeriodUnit, "num": "36", "unit": None},
    ]
    for case in cases:
        num, unit = split_num_and_unit(case["text"], case["enum"])
        assert num == case["num"] and unit == case["unit"]
