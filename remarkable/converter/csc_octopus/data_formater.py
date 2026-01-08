import logging
import re
import time
from collections import OrderedDict
from decimal import Decimal
from enum import Enum, IntEnum

from remarkable.common.util import clean_txt

p_money_unit = re.compile(r"(?P<amount>\d[\d,]*(\.\d+)?)(?P<unit>[亿万]?元)")
p_period_unit = re.compile(r"(?P<amount>\d+)(?P<unit>[年月日天])")
thousands_pattern = re.compile(r",")


class InterestPaymentWay(IntEnum):
    """付息方式，对应客户字典表，匹配不到的字典客户接受传None"""

    MONTH = 1
    SEASON = 2
    YEAR = 3
    HALF_YEAR = 4
    DEADLINE = 5
    OTHER = 6


class BiddingWay(IntEnum):
    """招标方式，对应客户字典表，匹配不到的字典客户接受传None"""

    NETHERLANDS_MODE = 1
    MIX_MOD = 3


class TextEnum(Enum):
    def __init__(self, value, text):
        self._value_ = value
        self.text = text

    @classmethod
    def get_enum(cls, text):
        for item in cls:
            if clean_txt(text) in item.text:
                return item
        return None


class MoneyUnit(TextEnum):
    """总发行规模单位，对应客户字典表，匹配不到的字典客户接受转None"""

    HUNDRED_MILLION_YUAN = (1, ("亿元", "亿"))
    YUAN = (2, ("元",))
    TEN_THOUSAND_YUAN = (3, ("万元", "万"))  # 客户当前没有此枚举，返回给客户的值需要换算成“亿元”


class PeriodUnit(TextEnum):
    """债券发行期限单位，对应客户字典表，匹配不到的字典客户接受转None"""

    YEAR = (1, ("年",))
    DAY = (2, ("日",))


PATTERNS_DICT = {
    # 付息方式
    r"按月(付息|支付)": InterestPaymentWay.MONTH,
    r"按季(付息|支付)": InterestPaymentWay.SEASON,
    r"按年(付息|支付)": InterestPaymentWay.YEAR,
    r"半年(付息|支付)": InterestPaymentWay.HALF_YEAR,
    r"到期偿还": InterestPaymentWay.DEADLINE,
    r"其他(方式)?(付息|支付)": InterestPaymentWay.OTHER,
    # 招标方式
    r"单一价格招标": BiddingWay.NETHERLANDS_MODE,  # 荷兰式
    r"多重价格招标": BiddingWay.MIX_MOD,  # 混合式
}

PATTERNS_DATE = OrderedDict(
    {
        # 此处需要注意正则顺序，越严格的正则放在越靠前的位置
        r"\d{4}年\d{1,2}月\d{1,2}日": "%Y年%m月%d日",
        r"\d{4}-\d{1,2}-\d{1,2}": "%Y-%m-%d",
        r"\d{4}/\d{1,2}/\d{1,2}": "%Y/%m/%d",
        r"(?<![年\d])\d{1,2}月\d{1,2}日": "%m月%d日",
    }
)


def transfer_to_number(text):
    for reg, num in PATTERNS_DICT.items():
        if re.search(reg, text):
            return num
    logging.warning(f'no pattern matched, text="{text}"')
    return 0


def date_format(text, out_format):
    for reg, fmt in PATTERNS_DATE.items():
        result = re.search(reg, clean_txt(text))
        if result:
            return time.strftime(out_format, time.strptime(result.group(0), fmt))
    logging.warning(f'no date format matched, text="{text}"')
    return ""


def data_format(label, text):
    """将AI预测答案转换成八爪鱼接口约定的数据格式"""
    if not text:
        return ""
    if label in ["招标日期", "缴款日期"]:
        format_result = date_format(text, "%Y-%m-%d")
    elif label in ["起息日（具体日期）", "上市日期"]:
        format_result = date_format(text, "%m-%d")
    elif label == "起息日（年份）":
        format_result = clean_txt(text)[:4]
    elif label in ["招标方式", "付息方式"]:
        format_result = transfer_to_number(text)
    elif label in ["公告手续费", "票面利率"]:
        format_result = clean_txt(text).replace("%", "")
    else:
        format_result = text
    return format_result or ""


def split_num_and_unit(text, enum):
    if enum is MoneyUnit:
        result = p_money_unit.search(clean_txt(text))
    elif enum is PeriodUnit:
        result = p_period_unit.search(clean_txt(text))
    else:
        logging.error(f"Unsupported enum: {enum.__name__ if enum else None}")
        return None, None
    if not result:
        return None, None

    amount = result.groupdict()["amount"]
    unit = result.groupdict()["unit"].replace("天", "日")  # “日”和"天"是同一个含义，处理一下
    enum_type = enum.get_enum(unit)
    if enum_type is MoneyUnit.TEN_THOUSAND_YUAN:
        # 客户需要将单位"万元"换算成"亿元"
        amount = str(Decimal(amount) / Decimal(10_000))
        enum_type = MoneyUnit.HUNDRED_MILLION_YUAN
    return amount, enum_type.value if enum_type else None


if __name__ == "__main__":
    # split_num_and_unit(" 25.20 0.85 亿元 000 ", MoneyUnit)
    print(date_format("24年5月20日", "%Y-%m-%d"))
