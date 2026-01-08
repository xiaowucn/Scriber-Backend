from remarkable.converter.ccxi import CCXIContractConverter


def test_convert_func():
    samples = {
        '2020年1月1日': '2020-01-01',
        '2020年10月1日': '2020-10-01',
        '2020年10月1': '2020-10-01',
        '2020-01-1': '2020-01-01',
        '2020-11-1': '2020-11-01',
        '2020/1/10': '2020-01-10',
        '2020/11/1': '2020-11-01',
    }
    for text, text_date in samples.items():
        assert CCXIContractConverter.get_date_in_text(text).strftime('%Y-%m-%d') == text_date
