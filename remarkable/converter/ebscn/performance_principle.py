import re
from dataclasses import dataclass

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt

# 固定时点提取是在每自然年度12月的最后一个交易日
# 收益分配、份额赎回和基金终止
# '固定时点提取是在每个季度末月最后一个周五'
# 固定时点提取是在每自然季度3月、6月、9月、12月的28日（遇节假日顺延至下个工作日），以固定时点的基金份额净值与基金累计净值作为计提日份额（累计）净值计提基准。
#
P_MONTH = PatternCollection(
    [
        r"每自然年度(?P<dst>\d+)月",
        r"(每自然[年季]度|、).*?(?P<dst>\d+)月",
        r"为(?P<dst>\d+)、",
        r"、.*?(?P<dst>\d+)(月|、)",
        r"、(?P<dst>\d+)、\d\d",
        r"(?P<dst>每个季度末月)",
    ],
    re.I,
)

P_DAY = PatternCollection(
    [
        r"每自然年度\d+月的(?P<dst>最后一个交易日)",
        r"\d+月的?(?P<dst>第[一二三四]自然周的周[一二三四五])",
        r"\d+月的?(?P<dst>\d\d?)日",
        r"(?P<dst>最后一个周[一二三四五])",
    ],
    re.I,
)

P_NO_FIXED_TIME = PatternCollection(
    [
        r"^收益分配、份额赎回和基金终止$",
    ]
)


@dataclass
class PerformancePrinciple:
    fund_type: str = ""
    period_type: str = "每年N月M日"
    months: list[str] | None = None
    day: str = ""
    day_type: str = "按交易日"
    desc: str = ""

    def to_text(self):
        if self.desc:
            if self.fund_type == "母基金":
                return f"{self.desc}"
            return f"""基金类型：{self.fund_type}
业绩报酬提取原则：{self.desc}
"""
        return f"""基金类型：{self.fund_type}
统一业绩报酬规则周期类型：{self.period_type}
每年N月：{"、".join(self.months)}
处理日：{self.day}
处理日类型：{self.day_type}
"""

    # "基金类型：母基金
    # 统一业绩报酬规则周期类型：“每年N月M日”
    # 每年N月：“12”
    # 处理日：“0”
    # 处理日类型：“按交易日”"


def performance_principle_convert(ebscn_answer):
    res = []
    for item in ebscn_answer.answer_data:
        fund_type = clean_txt(item["基金类型"])
        principle_text = clean_txt(item["业绩报酬提取原则"])
        if P_NO_FIXED_TIME.nexts(principle_text):
            performance_principle = PerformancePrinciple(
                fund_type=fund_type,
                desc="无固定时点",
            )
        elif "不收取业绩报酬" in principle_text:
            performance_principle = PerformancePrinciple(
                fund_type=fund_type,
                months=[],
                day="",
                desc="不收取业绩报酬",
            )
        else:
            months = get_months(principle_text)
            day = get_day(principle_text)
            performance_principle = PerformancePrinciple(
                fund_type=fund_type,
                months=months,
                day=day,
            )
        res.append(performance_principle.to_text())
    return "\n".join(res)


def get_months(text):
    res = set()
    for matcher in P_MONTH.finditer(clean_txt(text)):
        if not matcher:
            continue
        month = matcher.groupdict()["dst"]
        if month == "每个季度末月":
            res.update({"3", "6", "9", "12"})
        else:
            res.add(month)
    return sorted(res, key=int)


def get_day(text):
    res = set()
    for matcher in P_DAY.finditer(text):
        if not matcher:
            continue
        day = matcher.groupdict()["dst"]
        if day == "最后一个交易日":
            res.add("0")
        else:
            res.add(day)
    return list(res)[0] if res else ""
