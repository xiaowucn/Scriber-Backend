from unittest import TestCase

from remarkable.converter.szse.cyb_conv import AnswerNodeCalculator


class TestAnswerNodeCalculator(TestCase):
    def test_calc(self):
        field = '资产总额'
        assert AnswerNodeCalculator.calc(['1000', '+', '20', '*', '30', '*', '40'], field) == '2.50万元'
        assert AnswerNodeCalculator.calc(['2', '*', '(', '3万', '+', '2万', ')'], field) == '100,000.00'
        assert AnswerNodeCalculator.calc(['2万', '+', '(', '3万', '+', '2万', ')'], field) == '7.00万元'

        assert AnswerNodeCalculator.calc('1+2*3*4') == '25.00'
        assert AnswerNodeCalculator.calc('(1+2)*4') == '12.00'
        assert AnswerNodeCalculator.calc('(1+2)+(4+3)*5') == '38.00'
        assert AnswerNodeCalculator.calc('1/(1+1)') == '50.00%'
        assert AnswerNodeCalculator.calc('2*(3+2)') == '10.00'
        assert AnswerNodeCalculator.calc(['2', '*', '(', '30000', '+', '20000', ')']) == '100,000.00'
        assert AnswerNodeCalculator.calc(['2', '*', '(', '3万', '+', '2万', ')']) == '100,000.00'
        assert AnswerNodeCalculator.calc('1/0') is None
        assert AnswerNodeCalculator.calc('1+0') == '1.00'
        assert AnswerNodeCalculator.calc('1*0') == '0.00'
