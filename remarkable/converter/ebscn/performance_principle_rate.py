import re
from dataclasses import dataclass

import pandas as pd

from remarkable.common.pattern import PatternCollection

P_METHOD = PatternCollection([r"R[-—–]((\d+(\.?\d+)?)|[A-Z])+.*?%"], re.I)


@dataclass
class PerformancePrincipleRate:
    fund_type: str = ""
    accrual_ratio: str = ""
    calc_formula: str = ""
    processing_method: str = ""
    ratio_formulas: list[str] | None = None

    def to_text(self):
        if self.ratio_formulas:
            ratio_formulas = "\n".join(self.ratio_formulas)
            return f"""基金类型：{self.fund_type}
业绩报酬计提比例及公式：\n{ratio_formulas}
业绩报酬多区间处理方式：{self.processing_method}
"""
        return f"""基金类型：{self.fund_type}
计提比例：{self.accrual_ratio}
计算公式：{self.calc_formula}
业绩报酬多区间处理方式：{self.processing_method}
"""


#     "基金类型：母基金
# 业绩报酬计提比例及公式：
# 年化收益率：R≤0%，计提比例：0:，计提公式：Y=0。
#
# ……
#
#
# 业绩报酬多区间处理方式：分段累退"


def performance_principle_ratio_convert(ebscn_answer):
    res = []
    for item in ebscn_answer.answer_data:
        fund_type = item["基金类型"]
        accrual_ratio = item.get("计提比例", "")
        calc_formula = item.get("计提公式", "")
        ratio_formulas_answer = item.get("计提比例及公式", [])
        if ratio_formulas_answer:
            data_frame = pd.DataFrame(ratio_formulas_answer[1:], columns=ratio_formulas_answer[0])
            ratio_formulas = list(
                data_frame.apply(
                    lambda row: f"年化收益率：{row.iloc[0]} ，计提比例：{row.iloc[1]}，计提公式：{row.iloc[2]}", axis=1
                )
            )
            processing_method = "分段累退 " if any(P_METHOD.nexts(text) for text in ratio_formulas) else "不累退"
            performance_principle_rate = PerformancePrincipleRate(
                fund_type=fund_type,
                ratio_formulas=ratio_formulas,
                processing_method=processing_method,
            )
            res.append(performance_principle_rate.to_text())

        else:
            performance_principle_rate = PerformancePrincipleRate(
                fund_type=fund_type,
                accrual_ratio=accrual_ratio,
                calc_formula=calc_formula,
                processing_method="不累退",
            )
            res.append(performance_principle_rate.to_text())
    return "\n".join(res)
