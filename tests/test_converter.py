
def test_number_convert():
    from remarkable.common.convert_number_util import NumberUtil, PercentageUtil

    assert str(NumberUtil.cn_number_2_digit("100.12")) == "100.12"
    assert str(NumberUtil.cn_number_2_digit("100,12.1")) == "10012.1"
    assert str(NumberUtil.cn_number_2_digit("100,12.1.2")) == "10012.1"
    assert str(NumberUtil.cn_number_2_digit("七十八")) == "78"
    assert str(NumberUtil.cn_number_2_digit("一百万零七十八.12")) == "12"
    assert str(PercentageUtil.convert_2_division_str("10.12%")) == "253/2500"
    assert str(PercentageUtil.convert_2_division_str("百分之二十一")) == "21/100"
    assert str(PercentageUtil.convert_2_division_str("千分之二十")) == "1/50"
