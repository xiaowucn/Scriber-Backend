# -*- coding: utf8 -*-
import fractions
import re
from decimal import Decimal

from remarkable.common.util import clean_txt


class NumberUtil:
    NUMBER_MAPPING = {
        "〇": 0,
        "Ο": 0,
        "O": 0,
        "o": 0,
        "零": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    NUMBER_UNITS = {"十": 10, "百": 100, "千": 1000}
    CARDINAL_NUMBERS = {"万": 10000, "亿": 10**8}
    CAPITALS_NUM_MAPPING = {
        "壹": "一",
        "幺": "一",
        "贰": "二",
        "叁": "三",
        "肆": "四",
        "伍": "五",
        "陆": "六",
        "柒": "七",
        "捌": "八",
        "玖": "九",
        "拾": "十",
        "佰": "百",
        "仟": "千",
        "萬": "万",
        "億": "亿",
    }
    R_DOT = r"\.．"
    R_PERCENT_UNIT = r"[%％‰]"
    R_CN_NUMBER = r"零〇ΟOo壹贰叁肆伍陆柒捌玖拾佰仟萬億\d两一二三四五六七八九十百千万亿"
    R_FLOAT_NUMBER = rf"(?:[{R_CN_NUMBER}]+[,，]?)+(?:[{R_DOT}][{R_CN_NUMBER}]+)?"

    P_NUMBER = re.compile(rf"(?P<number>{R_FLOAT_NUMBER})")
    P_ARABIC_NUMBER = re.compile(r"[(（]?(?P<digit>\d+(?:,\d{3})*(?:[\.．]\d*)?)")
    P_NUMBER_IGNORE_CHAR = re.compile(r"([,，【】\[\]]|人民币|RMB)")
    P_DOT = re.compile(rf"[{R_DOT}]")

    @classmethod
    def cn_number_2_digit(cls, text):
        text = clean_txt(text)
        text = cls.P_NUMBER_IGNORE_CHAR.sub("", text)
        if not (res := cls.P_NUMBER.search(text)):
            return Decimal(0)
        text = res.group("number")
        text = cls.P_DOT.sub(".", text)
        l_pos = text.find(".")
        if l_pos > -1:
            text = text.replace(".", "")
            text = f"{text[:l_pos]}.{text[l_pos:]}"

        for key, value in cls.CAPITALS_NUM_MAPPING.items():
            text = text.replace(key, value)
        searched = cls.P_ARABIC_NUMBER.search(text)
        if searched:
            number = cls.format_number(searched.groupdict()["digit"])
            text = text[searched.end("digit") :]
        else:
            number = 0
        temp_num = temp = 0
        if len(text) == 1:
            if text in cls.NUMBER_MAPPING:
                return cls.format_number(cls.NUMBER_MAPPING[text])
            if text in cls.NUMBER_UNITS:
                return (
                    cls.format_number(cls.NUMBER_UNITS[text] * number)
                    if number
                    else cls.format_number(cls.NUMBER_UNITS[text])
                )
            return (
                cls.format_number(cls.CARDINAL_NUMBERS[text] * number)
                if number
                else cls.format_number(cls.CARDINAL_NUMBERS[text])
            )
        for current_value in text:
            if current_value == "零":
                continue
            if current_value in cls.NUMBER_MAPPING:
                temp_num = cls.NUMBER_MAPPING[current_value]
            elif current_value in cls.NUMBER_UNITS:
                if temp_num == 0:
                    temp += cls.NUMBER_UNITS[current_value]
                else:
                    temp += temp_num * cls.NUMBER_UNITS[current_value]
                temp_num = 0
            elif current_value == "亿":
                temp += temp_num
                number += temp
                number *= cls.CARDINAL_NUMBERS[current_value]
                temp = 0
                temp_num = 0
            elif current_value == "万":
                # 六亿五千万
                temp += temp_num
                if temp == 0:
                    if number != 0:
                        # 十万万
                        number *= cls.CARDINAL_NUMBERS[current_value]
                    else:
                        # 万元
                        number += 1 * cls.CARDINAL_NUMBERS[current_value]
                else:
                    number += temp * cls.CARDINAL_NUMBERS[current_value]
                temp = 0
                temp_num = 0
        number += temp + temp_num
        return cls.format_number(number)

    @classmethod
    def format_number(cls, number) -> Decimal:
        number = str(number)
        if number.isalnum():
            return Decimal(number)

        if number.find("."):
            decimal = number.split(".", maxsplit=1)[-1]
            if int(decimal) != 0:
                return Decimal(number)
        return Decimal(number.split(".", maxsplit=1)[0])

    @classmethod
    def is_increment(cls, numbers: list):
        # 是否为递增列表
        if not numbers or len(numbers) == 1:
            return False
        if any(not cls.P_NUMBER.search(str(val)) for val in numbers):
            return False
        return not any(int(numbers[i + 1]) - int(numbers[i]) != 1 for i in range(len(numbers) - 1))


class DateUtil:
    DIGIT_MAP = {
        "零": "0",
        "〇": "0",
        "Ο": "0",
        "O": "0",
        "o": "0",
        "一": "1",
        "两": "2",
        "二": "2",
        "三": "3",
        "四": "4",
        "五": "5",
        "六": "6",
        "七": "7",
        "八": "8",
        "九": "9",
        "十": "10",
        "十一": "11",
        "十二": "12",
    }

    CN_NUM = "|".join(sorted(DIGIT_MAP.keys(), key=lambda x: -len(x)))

    P_DATE_NORMALIZE = re.compile(CN_NUM)

    P_DATE_WITH_YEAR = re.compile(rf"(?P<date>[{CN_NUM}\d]{4}年(?:[{CN_NUM}\d]{1, 2}月)?(?:[{CN_NUM}\d]{1, 2}日)?)")

    @classmethod
    def convert_2_human_date(cls, text):
        if not text:
            return ""
        return cls.P_DATE_NORMALIZE.sub(lambda x: cls.DIGIT_MAP[x.group()], text)

    @classmethod
    def is_date(cls, text):
        return cls.P_DATE_WITH_YEAR.search(text) is not None


class PercentageUtil:
    P_PERCENTAGE = re.compile(rf"(?P<ratio>{NumberUtil.R_FLOAT_NUMBER})(?P<symbol>{NumberUtil.R_PERCENT_UNIT})")
    P_CN_PERCENTAGE = re.compile(
        rf"(?P<denominator>[{NumberUtil.R_CN_NUMBER}]+)分之(?P<numerator>[{NumberUtil.R_CN_NUMBER}]+)"
    )
    P_DIVISION_PERCENTAGE = re.compile(r"\d+/\d+")

    @classmethod
    def convert_2_division_str(cls, origin_text) -> str:
        if result := cls.convert_2_division(origin_text):
            return str(result)
        return origin_text

    @classmethod
    def convert_2_division(cls, origin_text):
        if cls.P_DIVISION_PERCENTAGE.search(origin_text):
            numerator, denominator = origin_text.split("/", maxsplit=1)
            numerator = NumberUtil.cn_number_2_digit(numerator)
            denominator = NumberUtil.cn_number_2_digit(denominator)
            return fractions.Fraction(numerator / denominator)
        if res := cls.P_PERCENTAGE.search(origin_text):
            numerator = NumberUtil.cn_number_2_digit(res.group("ratio"))
            denominator = Decimal(1000) if res.group("symbol") == "‰" else Decimal(100)
            return fractions.Fraction(numerator / denominator)
        if res := cls.P_CN_PERCENTAGE.search(origin_text):
            denominator = NumberUtil.cn_number_2_digit(res.group("denominator"))
            numerator = NumberUtil.cn_number_2_digit(res.group("numerator"))
            if not denominator:
                return None
            return fractions.Fraction(numerator / denominator)
        return None


if __name__ == "__main__":
    print(NumberUtil.cn_number_2_digit("十七"))
    print(DateUtil.convert_2_human_date("二O一二年1月"))
