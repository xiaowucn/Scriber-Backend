import re
from dataclasses import dataclass

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt

# 基金投资者可在本基金赎回开放日赎回本基金，本基金赎回开放日为自基金成立之日起（不含），6个月内不设赎回固定开放日，赎回固定开放日为6个月后的每自然月15日（如遇非工作日，则自动顺延至下一个工作日）
# 基金投资者可在本基金申购开放日申购本基金，本基金申购开放日为自基金成立之日起（不含）每自然周的最后一个交易日
# 固定开放日为每个交易日，固定开放日允许申购、允许赎回
# 本基金设置180天封闭期，封闭期间每个交易日可申购，不可赎回，封闭期届满后，每个交易日开放申购赎回。

# 本基金自基金成立之日起（不含），固定开放日为每自然周的周四（如遇非工作日，则自动顺延至下一个工作日）
# 本基金自基金成立之日起（不含），固定开放日为每自然周的周二、周五（如遇非工作日，则自动顺延至下一个工作日）,固定开放日允许申购、允许赎回。
# 本基金自基金成立之日起（不含），固定开放日为每自然月8日（如遇非工作日，则自动顺延至下一个工作日）
# "基金投资者可在本基金申购开放日申购本基金，本基金申购开放日为自基金成立之日起 (不含)每自然周的周三(如遇非工作日，则自动顺延至下一个工作日);
# 基金投资者可在本基金赎回开放日赎回本基金，本基金赎回开放日为自基金成立之日起 (不含) 3 个月后每自然周的周三(如遇非工作日，则自动顺延至下一个工作日)"

# 基金投资者可在本基金申购开放日申购本基金交易日;本基金不设置固定赎回开放日。
# '本基金自基金成立之日起（不含），3 个月内不设固定开放日，固定开放日为自基金成立之日起 3 个月后每个交易日，固定开放日允许申购、允许赎回。'

P_SKIP = PatternCollection(
    [
        r"^本基金不设置临时开放日",
    ]
)

P_MULTI_PERIODS = PatternCollection(
    [
        r"本基金设置(?P<dst>\d+)天封闭期.*?(?P<dst1>封闭期届满后)",
        # r'(?P<dst>\d+)个月内不设固定开放日.*?(?P<dst1>固定开放日为自基金成立之日起\d+个月)',
    ],
    re.I,
)

P_SINGLE_PERIODS = PatternCollection(
    [
        r"\d+个月内不设固定开放日.*?(?P<dst>固定开放日为自基金成立之日起(?P<month>\d+)个月后(?P<day>每个交易日))",
        r"自基金成立之日起.*?(?P<dst>(?P<month>\d+)个月后每自然周的(?P<day>周[一二三四五]))",
        r"固定开放日为.*?(?P<dst>(?P<month>\d+)个月后的每自然月(?P<day>\d+)日)",
        r"固定开放日为(?P<dst>每自然周的第[一二三四五]个交易日)",
        r"自基金成立之日起.*?(?P<dst>每自然周的周[一二三四五])",
        r"自基金成立之日起.*?(?P<dst>每自然[周月]的?最后一个交易日)",
        r"固定开放日为.*?(?P<dst>每自然月(?P<day>\d+)日)",
        r"(?P<dst>固定开放日为每个?交易日)",
        r"基金投资者可在本基金(?P<dst>申购开放日)申购",
        r"基金投资者可在本基金(?P<dst>赎回开放日)赎回",
    ],
    re.I,
)

P_OPEN_DAY = PatternCollection(
    [
        r"每自然周?的?(?P<dst>(周[一二三四五][、与和及]){1,4}周[一二三四五])",
        r"每自然周的?(?P<dst>周[一二三四五])",
        r"每自然周的?(?P<dst>第[一二三四五]个交易日)",
        r"每自然月的?(?P<dst>\d+日([、与和及]\d+日){0,})",
        r"(?P<dst>每个?交易日)",
        r"每自然[周月]的?(?P<dst>最后一个交易日)",
        r"基金投资者可在本基金(?P<dst>申购开放日)申购",  # 特殊情况 放到最后
    ],
    re.I,
)

P_ALL_DAY = PatternCollection(
    [
        r"每个?交易日",
        r"申购开放日",
    ]
)

P_OPEN_DAY_SUB = re.compile(r"[与和及]")

P_OPEN_TYPE = PatternCollection(
    [
        r"基金申购开放日(?P<purchase>申购)本基金",
        r"基金赎回开放日(?P<redemption>赎回)本基金",
        r"允许(?P<purchase>申购)、允许(?P<redemption>赎回)",
        r"每个交易日可(?P<purchase>申购)，不可赎回",
        r"每个交易日开放(?P<purchase>申购)(?P<redemption>赎回)",
        r"基金投资者可在本基金(?P<purchase>申购)开放日申购",
    ]
)

P_EVERY_WEEK = PatternCollection(
    [
        r"每自然周",
        r"每个?交易日",
        r"申购开放日",
    ]
)


@dataclass
class Period:
    period_type: str = ""
    text: str = ""


@dataclass
class OpenDay:
    open_types: list[str] | None = None
    period_type: str = ""
    open_day_type: str = "按交易日"
    open_days: list[str] | None = None
    open_status: str = ""
    is_special: bool = False

    def __post_init__(self):
        if self.open_types == ["申购", "赎回"]:
            self.open_status = "都开放"
        elif len(self.open_types) == 1 and not self.is_special:
            self.open_status = self.open_types[0]

    def to_text(self):
        return f"""开放类型：{"、".join(self.open_types)}
开放周期类型：{self.period_type}
开放日类型：{self.open_day_type}
开放日：{"、".join(self.open_days)}
开放状态：{self.open_status}
"""


SPECIAL_OPEN_DAY = {
    "本基金不设置固定赎回开放日": OpenDay(
        open_types=["赎回"], period_type="", open_day_type="", open_days=[], open_status="", is_special=True
    ),  # 基金投资者可在本基金申购开放日申购;本基金不设置固定赎回开放日。
}


def open_day_convert(ebscn_answer):
    origin_answer_text = ebscn_answer.answer_text
    answer_texts = origin_answer_text.split("\n")
    res = []
    for answer_text in answer_texts:
        answer_text = clean_txt(answer_text)
        if P_SKIP.nexts(answer_text):
            continue
        periods = get_periods(answer_text)
        for period in periods:
            open_types = get_open_types(period.text)
            open_days = get_open_days(period.text)
            open_day_ins = OpenDay(
                open_types=open_types,
                period_type=period.period_type,
                open_days=open_days,
            )
            res.append(open_day_ins.to_text())
    # 添加特例
    if special_opendays := get_special_opendays(origin_answer_text):
        res.append(special_opendays.to_text())
    return "\n".join(res)


def get_periods(answer_text: str) -> list[Period]:
    res = get_multi_periods(answer_text)
    if res:
        return res
    res = []
    if matcher := P_SINGLE_PERIODS.nexts(answer_text):
        period_texts = []
        period = matcher.groupdict()["dst"]
        month = matcher.groupdict().get("month")
        day = matcher.groupdict().get("day")
        if month and day:
            period_texts.append(f"成立日{month}个月-终止日")
        if "每自然月" in period:
            period_texts.append("每月")
        elif P_EVERY_WEEK.nexts(period):
            period_texts.append("每周")
        period = Period(period_type="、".join(period_texts), text=answer_text)
        res.append(period)
    return res


def get_multi_periods(answer_text: str) -> list[Period]:
    res = []
    origin_texts = []
    period_text_first = ""
    if matcher := P_MULTI_PERIODS.nexts(answer_text):
        if dst := matcher.groupdict().get("dst"):
            if "个月" in answer_text:
                period_text_first = f"成立日下一天-成立日+{dst}个月（含）"
            else:
                period_text_first = f"成立日下一天-成立日+{dst}天（含）"
        if dst1 := matcher.groupdict().get("dst1"):
            if "个月" in answer_text:
                period_text_second = f"成立日+{dst}个月（不含）-终止日"
            else:
                period_text_second = f"成立日+{dst}天（不含）-终止日"
            origin_texts = answer_text.split(dst1)
            first_period = Period(period_type="、".join([period_text_first]), text=origin_texts[0])
            second_period = Period(period_type="、".join([period_text_second]), text=origin_texts[1])
            res.append(first_period)
            res.append(second_period)
    return res


def get_open_types(answer_text):
    res = []
    if matcher := P_OPEN_TYPE.nexts(answer_text):
        if purchase := matcher.groupdict().get("purchase"):
            res.append(purchase)
        if redemption := matcher.groupdict().get("redemption"):
            res.append(redemption)

    return res


def get_open_days(answer_text):
    res = []
    if matcher := P_OPEN_DAY.nexts(answer_text):
        open_type = matcher.groupdict()["dst"]
        if P_ALL_DAY.nexts(open_type):
            res.extend(["周一", "周二", "周三", "周四", "周五"])
        elif P_OPEN_DAY_SUB.search(open_type):
            res.extend(P_OPEN_DAY_SUB.split(open_type))
        else:
            res.append(open_type)
    return res


def get_special_opendays(origin_answer_text):
    for pattern, open_day_ins in SPECIAL_OPEN_DAY.items():
        if PatternCollection(pattern).nexts(origin_answer_text):
            return open_day_ins
    return None
