from unittest import TestCase

from remarkable.plugins.cgs.common.utils import number2chinese


class Number2ChineseTestCase(TestCase):
    def test_normal(self):
        self.assertEqual(number2chinese(6), '六')

    def test_value_gt_10(self):
        self.assertEqual(number2chinese(13), '十三')

    def test_value_gt_100(self):
        self.assertEqual(number2chinese(113), '一百一十三')

    def test_value_gt_1000(self):
        self.assertEqual(number2chinese(1013), '一千〇一十三')

    def test_large_value(self):
        self.assertEqual(number2chinese(100232003444), '一千〇二亿三千二百万三千四百四十四')

    def test_zero(self):
        self.assertEqual(number2chinese(0), '〇')
