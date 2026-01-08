from collections import Counter
from unittest import TestCase


from remarkable.common.constants import Language
from remarkable.common.util import clean_txt, index_in_space_string, is_number_str
from remarkable.converter.csc_octopus import MoneyUnit, PeriodUnit, split_num_and_unit
from remarkable.plugins.ecitic.common import calc_similarity
from remarkable.plugins.predict.common import clean_syllabus_feature


def index(_text, _goal):
    _idx = _text.index(_goal)
    return _idx, _idx + len(_goal)


def test_normal_en():
    goal = "_F x N d_"
    clean_goal = "_F x N d_"

    for text in (
        f"---{goal}---",
        f"--  {goal}  --",
        f"   {goal}   ",
        f"abc{goal}abc",
    ):
        assert index_in_space_string(
            text, index(clean_txt(text, language=Language.EN_US.value), clean_goal), is_cn=False
        ) == index(text, goal)


def test_normal_cn():
    goal = "_F i N d_"
    clean_goal = "_FiNd_"

    for text in (
        f"---{goal}---",
        f"--  {goal}  --",
        f"   {goal}   ",
        f"abc{goal}abc",
    ):
        assert index_in_space_string(
            text, index(clean_txt(text, language=Language.ZH_CN.value), clean_goal), is_cn=True
        ) == index(text, goal)


class CommonUtilTestCase(TestCase):
    def test_clean_syllabus_feature(self):
        counter = Counter()
        counter.update({"财务信息|详 情": 2})
        counter.update({"财务 信息|详情:": 2})
        counter.update({"第一章 财务信息|详情": 2})
        counter.update({"__regex__会计 信息__regex__会议:": 2})
        counter.update({"__regex__(会计)信息__regex__会议": 5})
        counter.update({"输入输出": 2})

        cleaned_data = clean_syllabus_feature(counter)
        self.assertEqual(cleaned_data["__regex__会计 信息__regex__会议:"], 2)
        self.assertEqual(cleaned_data["__regex__(会计)信息__regex__会议"], 5)
        self.assertEqual(cleaned_data["财务信息|详情"], 6)
        self.assertEqual(cleaned_data["输入输出"], 2)

    def test_split_num_and_unit(self):
        sample = [
            {
                "text": "123,456.00亿元",
                "enum": MoneyUnit,
                "ret": ("123,456.00", MoneyUnit.HUNDRED_MILLION_YUAN.value),
            },
            {
                "text": "123456万元",
                "enum": MoneyUnit,
                "ret": ("12.3456", MoneyUnit.HUNDRED_MILLION_YUAN.value),
            },
            {
                "text": "123,456元",
                "enum": MoneyUnit,
                "ret": ("123,456", MoneyUnit.YUAN.value),
            },
            {
                "text": "123,456.00亿元",
                "enum": MoneyUnit,
                "ret": ("123,456.00", MoneyUnit.HUNDRED_MILLION_YUAN.value),
            },
            {
                "text": "10日",
                "enum": PeriodUnit,
                "ret": ("10", PeriodUnit.DAY.value),
            },
            {
                "text": "10天",
                "enum": PeriodUnit,
                "ret": ("10", PeriodUnit.DAY.value),
            },
            {
                "text": "3年",
                "enum": PeriodUnit,
                "ret": ("3", PeriodUnit.YEAR.value),
            },
        ]
        for item in sample:
            ret = split_num_and_unit(item["text"], item["enum"])
            self.assertEqual(ret, item["ret"])

    def test_is_number_str(self):
        sample = (
            ("1.00", True),
            ("1", True),
            ("1234", True),
            ("1.88", True),
            ("+1.00", True),
            ("-1.00", True),
            ("100.00", True),
            ("1.000.00", False),
            ("1,000.00", False),
        )
        for text, is_number in sample:
            self.assertEqual(is_number, is_number_str(text))

    def test_get_similarity(self):
        sample = (
            ("（一）思勰投资苏信1号私募证券投资基金", "思勰投资苏信1号私募证券投资基金。", 1.0),
            ("1.abc", "ab c", 1.0),
            ("1.1abc", "a bc.", 1.0),
            ("①投资基金", "③投资基金", 1.0),
            ("（一）投资基金", "①投资 基金", 1.0),
            ("（1）投资基金", "①投资 基金", 1.0),
            ("（1）投资(2)基金", "①投资 （一）基金", 1.0),
            ("投资基金", "投资基金AAA", 1.0),
            ("投资基金AAA+", "投资基金AAA", 1.0),
            ("投资基金AAA+1", "投资基金AAA", 1.0),
            ("投资基金AAA1-", "投资基金AAA", 1.0),
            ("投资基金AAA1", "投资基金AAA", 1.0),
            ("20个投资基金", "二十只投资基金", 1.0),
            ("投资基金3%", "二十只投资基金4.9％", 1.0),
        )

        for text1, text2, similarity in sample:
            self.assertEqual(calc_similarity(text1, text2), similarity)
