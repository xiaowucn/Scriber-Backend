import re


class StringUtil:
    WHITESPACE_PATTERN = re.compile(r"[\s　]+", re.S)
    CN_PARENTHESE_PATTERN = re.compile(r"（.+）", re.S)
    NUMBER_PATTERN = re.compile(r"^(上升|下降|降低|\+)?[\d\-,.%()]+.{0,5}$", re.S)
    STRICT_NUMBER_PATTERN = re.compile(r"[\d\-+]+")
    P_NON_NUMBER = re.compile(r"^\d{2}\D{2,}\d{2}$|年以|\d+-\d+年")
    P_DIGIT = re.compile(r"\d")
    P_MONEY_PREFIX = re.compile(r"^(人民币|USD|EUR?|HKD|新?台币|孟加拉塔卡|美元)")
    P_INTEGER = re.compile(r"^[\d-]+([(（][a-zA-Z][)）])?$")
    P_STRICT_NUMBER_PATTERN = re.compile(r"^[\d.]+%?$")

    SPECIAL_NUMBERS = ["-", "--", "---", "/", "—", "——", "·", "–", "一"]
    SPECIAL_NUMBER_RATIO = re.compile(r"((-?\d+(\.\d+)?):)+(-?\d+(\.\d+)?)")
    ZERO_NUMBERS = ["0", "0.00"]
    SPECIAL_TEXT_NUMBERS = ["微小", "不适用", "<0.01"]
    SPECIAL_NUMBER_PATTERN = re.compile(r"^(" + r"|".join(SPECIAL_NUMBERS + SPECIAL_TEXT_NUMBERS) + r")$")
    P_SERIAL_NUMBER = re.compile(r"^[(（]?(\d+|[一二三四五六七八九十]+|[a-zA-Z])[）)、.]?$")
    P_DECIMAL = re.compile(r"^[\d,.]+$")

    BLANK_CELL_CHARS = ("", "-", "--", "---", "/", "—", "——", "–", "一")
    P_CN_TEXT = re.compile(r"[\u4e00-\u9fa5]+")

    @classmethod
    def delete_whitespace(cls, string):
        return cls.WHITESPACE_PATTERN.sub("", string)

    @classmethod
    def delete_cn_parenthese(cls, string):
        return cls.CN_PARENTHESE_PATTERN.sub("", cls.delete_whitespace(string))

    @classmethod
    def is_special_num(cls, text):
        text = text.strip()
        return cls.SPECIAL_NUMBER_PATTERN.search(text) is not None or cls.SPECIAL_NUMBER_RATIO.search(text) is not None

    @classmethod
    def is_num(cls, text):
        text = StringUtil.delete_whitespace(text)
        # return str != '' and str != '-' and num_pattern.search(str) != None
        return (
            cls.P_NON_NUMBER.search(text) is None
            and cls.NUMBER_PATTERN.search(text) is not None
            and cls.STRICT_NUMBER_PATTERN.search(text) is not None
        )

    @classmethod
    def is_money(cls, text):
        text = text.strip()
        text = cls.P_MONEY_PREFIX.sub("", text)
        return cls.is_num(text)

    @classmethod
    def non_numeric_parts_equal(cls, first, second, ignore_whitespace=False):
        if ignore_whitespace:
            first, second = cls.delete_whitespace(first), cls.delete_whitespace(second)
        return (
            first
            and second
            and cls.P_DIGIT.sub("#", first) == cls.P_DIGIT.sub("#", second)
            and cls.P_DIGIT.sub("!", first) == cls.P_DIGIT.sub("!", second)
        )
