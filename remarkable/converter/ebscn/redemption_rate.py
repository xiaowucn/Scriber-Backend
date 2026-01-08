import re
from dataclasses import dataclass

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt

# 本基金赎回费率为基金份额持有期小于365天的，赎回费率为1%，基金份额持有365天（含）以上的，不收取赎回费
# 本基金赎回费率为基金份额持有期小于365天的，赎回费率为2%，基金份额持有365天（含）至730天的，赎回费率为1%，基金份额持有730天（含）以上的，
# 赎回费率为0%。赎回费归募集机构所有，募集机构有权对投资者的赎回费进行减免。基金份额持有人红利再投资取得的基金份额不收取赎回费。


P_BASE = PatternCollection(
    [
        r"不收取赎回费用",
    ]
)

P_MULTI_PERIODS = PatternCollection(
    [
        r"持有期小于(?P<dst>\d+天)",
        r"持有(?P<dst>\d+天)（含）至(?P<dst1>\d+天)",
        r"持有(?P<dst>\d+天)（含）以上",
    ],
    re.I,
)

P_RATE = PatternCollection(
    [
        r"赎回费率为(?P<dst>\d+(\.\d+)?%)",
        r"(?P<dst>不收取赎回费)",
    ],
    re.I,
)

P_ALONE_RATE = PatternCollection(
    [
        r"(?P<dst>\d+%)",
    ]
)

P_SPLIT = re.compile(r"基金份额")


@dataclass
class RedemptionRate:
    period_type: str = ""
    rate: str = ""

    def to_text(self):
        if not self.period_type:
            return self.rate
        return f"{self.period_type}：{self.rate}"


def redemption_rate_convert(ebscn_answer):
    res = []
    origin_answer_text = ebscn_answer.answer_text
    answer_text = clean_txt(origin_answer_text)
    if P_BASE.nexts(answer_text):
        redemption_rate_ins = RedemptionRate(
            period_type="",
            rate="费率0",
        )
        res.append(redemption_rate_ins.to_text())
        return "\n".join(res)
    answer_texts = P_SPLIT.split(answer_text)
    redemption_rates = get_rates(answer_texts)
    res = [redemption_rate.to_text() for redemption_rate in redemption_rates]
    return "\n".join(res)


def get_rates(answer_texts: list[str]) -> list[RedemptionRate]:
    res = []
    for answer_text in answer_texts:
        period_text = ""
        rate_text = ""
        if matcher := P_MULTI_PERIODS.nexts(answer_text):
            if dst := matcher.groupdict().get("dst"):
                if "小于" in answer_text:
                    period_text = f"0-{dst}"
                elif "以上" in answer_text:
                    period_text = f"{dst}（含）以上"
            if dst1 := matcher.groupdict().get("dst1"):
                period_text = f"{dst}-{dst1}"
        if rate_matcher := P_RATE.nexts(answer_text):
            if rate_text := rate_matcher.groupdict().get("dst"):
                if "不收取赎回费" in rate_text or "0%" in rate_text:
                    rate_text = "费率0"
                else:
                    rate_text = f"费率{rate_text}"
        if not rate_text:
            if alone_rate_matcher := P_ALONE_RATE.nexts(answer_text):
                if rate_text := alone_rate_matcher.groupdict().get("dst"):
                    rate_text = f"费率{rate_text}"
        if rate_text:
            res.append(RedemptionRate(period_type=period_text, rate=rate_text))
    return res
