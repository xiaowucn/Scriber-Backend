from remarkable.converter.ebscn.performance_principle_rate import P_METHOD


def test_ebscn_rate():
    assert P_METHOD.nexts('Y2（R）= Y1（10%）+A×（R-10%）×30%×T/365')
    assert P_METHOD.nexts('Y1（R）=A×（R-35%）×30%×T/365')
    assert P_METHOD.nexts('Y1（R）=A×（R-3.8%）×20%×T/365')
    assert P_METHOD.nexts('Y=K×T1×（R-B-6%）×T/365×【30%】')
    assert P_METHOD.nexts('Y1（R）= MIN(A×（R-B）×20%, A×R)')
    assert not P_METHOD.nexts('Y=F×(R-P)xW')
    assert not P_METHOD.nexts('Y2（R）=A×R×18%')
