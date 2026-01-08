from unittest import TestCase

from remarkable.plugins.cgs.rules.calculator import ExprCalculator, ValueToken
from remarkable.plugins.cgs.schemas.suggestion import SuggestionManager


class TestRule(TestCase):
    def test_normal_true(self):
        exp = [
            {'value': "24", 'name': '冷静期'},
            '+',
            {'value': '12'},
            '-',
            {'value': '12'},
            '==',
            {'value': "24"},
            '且',
            {'value': "中国公司", 'name': '公司名称'},
            '包含',
            {'value': '中国'},
            '且',
            {'value': "一家公司", 'name': '公司名称'},
            '不包含',
            {'value': '中国'},
        ]
        self.assertTrue(ExprCalculator(exp).run().value)

    def test_normal_false(self):
        exp = [
            {'value': "24", 'name': '冷静期'},
            '+',
            {'value': '12'},
            '-',
            {'value': '12'},
            '==',
            {'value': "24"},
            '且',
            {'value': "中国公司", 'name': '公司名称'},
            '不包含',
            {'value': '中国'},
            '且',
            {'value': "一家公司", 'name': '公司名称'},
            '不包含',
            {'value': '中国'},
        ]
        self.assertFalse(ExprCalculator(exp).run().value)

    def test_bool_expr_true(self):
        exp = [
            {'value': "24", 'name': '冷静期'},
            '+',
            {'value': '12'},
            '-',
            {'value': '12'},
            '==',
            {'value': "24"},
            '>',
            {'value': '23'},
            '<',  # <
            {'value': '24'},
            '≠',
            {'value': '24.11'},
            '≥',
            {'value': '24.11'},
        ]
        self.assertTrue(ExprCalculator(exp).run().value)

    def test_bool_expr_false(self):
        exp = [
            {'value': "24", 'name': '冷静期'},
            '+',
            {'value': '12'},
            '-',
            {'value': '12'},
            '==',
            {'value': "24"},
            '>',
            {'value': '23'},
            '>',  # >
            {'value': '24'},
            '≠',
            {'value': '24.11'},
            '≥',
            {'value': '24.11'},
        ]
        self.assertFalse(ExprCalculator(exp).run().value)

    def test_reversed_text_normal_true(self):
        exp = [
            {'value': "24", 'name': '冷静期'},
            '+',
            {'value': '12'},
            '==',
            {'value': "24"},
        ]
        self.assertEqual(ExprCalculator(exp).reversed_expr_text, '冷静期 + 12 ≠ 24')

    def test_reversed_text_multi_true(self):
        exp = [
            {'value': "24", 'name': '冷静期'},
            '+',
            {'value': '12'},
            '>',
            {'value': "24"},
            '且',
            {'value': "24", 'name': '考察期'},
            '<',
            {'value': '12'},
        ]
        self.assertEqual(ExprCalculator(exp).reversed_expr_text, '冷静期 + 12 ≤ 24 或 考察期 ≥ 12')

    def test_special_rule(self):
        exp = [
            {'value': "123", 'name': '公司名称'},
            '且',
            {'value': "1"},
        ]
        self.assertTrue(ExprCalculator(exp).run().value)

        exp = [
            {'value': None, 'name': '公司名称'},
            '且',
            {'value': "1"},
        ]
        self.assertFalse(ExprCalculator(exp).run().value)

    def test_cn_rate(self):
        exp = [
            {'value': "百分之三十四", 'name': '业绩报酬提取比率'},
            '≥',
            {'value': "30%"},
        ]
        self.assertTrue(ExprCalculator(exp).run().value)

        exp = [
            {'value': "百分之三十四", 'name': '业绩报酬提取比率'},
            '<',
            {'value': "30%"},
        ]
        self.assertFalse(ExprCalculator(exp).run().value)

        exp = [
            {'value': "百分之三十四", 'name': '业绩报酬提取比率'},
            '>',
            {'value': "百分之三十"},
        ]
        self.assertTrue(ExprCalculator(exp).run().value)

    def test_cn_number(self):
        exp = [
            {'value': "三十四", 'name': '冷静期'},
            '-',
            {'value': "三十"},
            '==',
            {'value': "四小时"},
        ]
        self.assertTrue(ExprCalculator(exp).run().value)

        exp = [
            {'value': "四小时", 'name': '冷静期'},
            '+',
            {'value': "三十小时"},
            '==',
            {'value': "三十四"},
        ]
        self.assertTrue(ExprCalculator(exp).run().value)

    def test_option_unique_continuity(self):
        exp = [
            {'value': "中国公司测试", 'name': '公司名称'},
            '包含',
            {'value': '中国'},
            '或',
            {'value': "中国公司测试", 'name': '公司名称'},
            '包含',
            {'value': '公司'},
            '或',
            {'value': "中国公司测试", 'name': '公司名称'},
            '包含',
            {'value': '测试'},
        ]
        self.assertFalse(ExprCalculator(exp, {'unique': True}).run().value)

    def test_option_unique_detached(self):
        exp = [
            {'value': "中国公司测试", 'name': '公司名称'},
            '包含',
            {'value': '中国'},
            '或',
            {'value': "中国公司测试", 'name': '公司名称'},
            '包含',
            {'value': '公司'},
            '或',
            {'value': "中国", 'name': '公司名称2'},
            '包含',
            {'value': '测试'},
            '或',
            {'value': "中国公司", 'name': '公司名称'},
            '包含',
            {'value': '测试'},
        ]

        result = ExprCalculator(exp, {'unique': True}).run()
        self.assertFalse(result.value)

        message, reason = ExprCalculator.render_message_by_result(result, '1==1')
        self.assertEqual('请在“公司名称”内删除“中国或公司”\n\n请在“公司名称2”内补充“测试”\n\n请在“公司名称”内补充“测试”', message)
        self.assertEqual('1==1\n公司名称 未唯一包含 [中国, 公司]\n公司名称2 不包含 测试\n公司名称 不包含 测试', reason)

    def test_render_suggestion_include_not_include(self):
        exp = [
            {'value': "24", 'name': '冷静期'},
            '+',
            {'value': '12'},
            '-',
            {'value': '13'},
            '==',
            {'value': "24"},
            '或',
            {'value': "中国公司", 'name': '公司名称'},
            '不包含',
            {'value': '中国'},
            '或',
            {'value': "一家公司", 'name': '管理人名称'},
            '包含',
            {'value': '管理'},
        ]
        result = ExprCalculator(exp).run()
        self.assertFalse(result.value)
        message, reason = ExprCalculator.render_message_by_result(result)

        self.assertEqual('冷静期 + 12 - 13 == 24\n\n请在“公司名称”内删除“中国”\n\n请在“管理人名称”内补充“管理”', message)
        self.assertEqual('冷静期 + 12 - 13 ≠ 24\n公司名称 包含 中国\n管理人名称 不包含 管理', reason)

    def test_render_bad_expr_suggestion(self):
        exp = [
            {'value': "24", 'name': '冷静期'},
            '或',
            {'value': "一家公司", 'name': '管理人名称'},
        ]
        result = ExprCalculator(exp).run()
        self.assertTrue(bool(result.value))
        message, reason = ExprCalculator.render_message_by_result(result)

        self.assertEqual(None, message)
        self.assertEqual(None, reason)

    def test_convert_unit(self):
        self.assertAlmostEqual(1.0, ValueToken.convert_unit('60分钟'))
        self.assertAlmostEqual(2.0, ValueToken.convert_unit('120分'))
        self.assertAlmostEqual(1.0, ValueToken.convert_unit('3600秒'))
        self.assertAlmostEqual(3700, ValueToken.convert_unit('3,700元'))
        self.assertAlmostEqual(3700, ValueToken.convert_unit('三千七百元'))
        self.assertAlmostEqual(12.0, ValueToken.convert_unit('360日'))
        self.assertAlmostEqual(12.0, ValueToken.convert_unit('1年'))
        self.assertAlmostEqual(1.0, ValueToken.convert_unit('1月'))

    def test_convert_bad_unit(self):
        self.assertAlmostEqual(2.0, ValueToken.convert_unit('2个小时'))
        self.assertAlmostEqual(2.0, ValueToken.convert_unit('XXXX2小时XXX'))
        self.assertAlmostEqual(76000000.0, ValueToken.convert_unit('人民币七千六百万元总'))
        self.assertAlmostEqual(7060000.0, ValueToken.convert_unit('七百零六万'))
        self.assertAlmostEqual(ValueToken.convert_unit('一万元'), ValueToken.convert_unit('1万元'))
        self.assertAlmostEqual(ValueToken.convert_unit('总1,000,000,000,000.00元总'), ValueToken.convert_unit('总1万亿元'))

    def test_render_suggestion(self):
        self.assertEqual(
            '请补充封闭期，或填写为“无”；请补充基金管理人概况-名称、基金名称',
            SuggestionManager.get_suggestion_by_fields(['封闭期', '基金管理人概况-名称', '基金名称', '封闭期', '基金名称']),
        )

        self.assertEqual(
            '请补充基金管理人概况-名称、基金名称', SuggestionManager.get_suggestion_by_fields(['基金管理人概况-名称', '基金名称', '基金名称'])
        )

        self.assertEqual('请补充封闭期，或填写为“无”', SuggestionManager.get_suggestion_by_fields('封闭期'))
