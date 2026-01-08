from copy import deepcopy
from functools import partial

from remarkable.common.constants import ComplianceStatus
from remarkable.pw_models.model import NewFileMeta
from remarkable.rule.rule import InspectItem
from remarkable.rule.ssepoc.rules import POChecker
from remarkable.rule.ssepoc.rules.shareholder import check_amount
from remarkable.rule.szse_poc.rules import RelatedDocBase, RuleBakery


class RelatedDoc(RelatedDocBase):
    group_key = "业绩预告"
    attr_path_map = {"limit_val_lower": "变动数值下限", "limit_val_upper": "变动数值上限", "change_dir": "变动方向"}
    display_attrs = [{"label": "预计变动方向", "attr": "change_dir"}]


class ProfitSum(RuleBakery):
    _case_map = {
        "case_1": "净利润为负值，上一年年度每股收益绝对值大于0.05元",
        "case_2": "净利润与上年同期相比上升或者下降50％以上，上一年年度每股收益绝对值大于0.05元",
        "case_3": "实现扭亏为盈，上一年年度每股收益绝对值大于0.05元",
    }
    _attr_label_map = {
        "last_year_profit": "上年净利润",
        "current_year_profit": "当年净利润",
        "earnings_per_share": "上一年年度每股收益",
    }

    related_docs: list[NewFileMeta] = []
    last_year_profit: InspectItem | None = None  # 上年净利润
    current_year_profit: InspectItem | None = None  # 当年净利润
    earnings_per_share: InspectItem | None = None  # 上一年年度每股收益

    @property
    def profit(self):
        profit = self.current_year_profit if self.has_content(self.current_year_profit) else self.last_year_profit
        profit.result = ComplianceStatus.DIS_IN_TIME
        return profit

    def load_related_docs(self, related_docs: list[NewFileMeta]):
        docs = [d for d in related_docs if "修正" not in d.title]
        if related_docs and not self.related_docs:
            self.related_docs = list(RelatedDoc.load(docs))

    def check(self, related_docs: list[NewFileMeta]):
        self.load_related_docs(related_docs)
        for case in self._case_map:
            result = getattr(self, f"check_{case}")()
            if result is not None:
                result.result, cols = self.gen_extra_cols(
                    [self.last_year_profit, self.current_year_profit, self.earnings_per_share]
                )
                result.detail["extra_cols"].extend(cols)
                return result
        return None

    def check_case_1(self):
        if (
            not self.has_content(self.current_year_profit)
            or not self.has_content(self.earnings_per_share)
            or self.current_year_profit.amount >= 0
            or abs(self.earnings_per_share.amount) <= 0.05
        ):
            return None

        item = deepcopy(self.profit)
        item.detail["sub_cols"].extend(
            [
                InspectItem.new(second_rule="满足标准", comment=self._case_map["case_1"]),
                self.current_year_profit,
                self.last_year_profit,
                self.earnings_per_share,
            ]
        )
        return item

    def check_case_2(self):
        if (
            not self.has_content(self.last_year_profit)
            or not self.has_content(self.current_year_profit)
            or not self.has_content(self.earnings_per_share)
            or abs((self.current_year_profit.amount - self.last_year_profit.amount) / self.last_year_profit.amount)
            <= 0.5
            or abs(self.earnings_per_share.amount) <= 0.05
        ):
            return None

        item = deepcopy(self.profit)
        item.detail["sub_cols"].extend(
            [
                InspectItem.new(second_rule="满足标准", comment=self._case_map["case_2"]),
                self.current_year_profit,
                self.last_year_profit,
                self.earnings_per_share,
            ]
        )
        return item

    def check_case_3(self):
        if (
            not self.has_content(self.current_year_profit)
            or not self.has_content(self.earnings_per_share)
            or self.last_year_profit.amount >= 0
            or self.current_year_profit.amount <= 0
            or abs(self.earnings_per_share.amount) <= 0.05
        ):
            return None

        item = deepcopy(self.profit)
        item.detail["sub_cols"].extend(
            [
                InspectItem.new(second_rule="满足标准", comment=self._case_map["case_3"]),
                self.current_year_profit,
                self.last_year_profit,
                self.earnings_per_share,
            ]
        )
        return item


class OperatingResult(POChecker):
    name = "上市公司预计全年度经营业绩将出现某些情形的，应当及时披露业绩预告公告"
    description = """11.3.1【1】上市公司预计全年度经营业绩将出现下列情形之一的，应当及时进行业绩预告：
（一）净利润为负值；
（二）净利润与上年同期相比上升或者下降50％以上；
（三）实现扭亏为盈。
11.3.2 以下比较基数较小的上市公司出现本规则第11.3.1 条第（二）项情形的，经本所同意可以豁免进行业绩预告：
上一年年度每股收益绝对值低于或者等于0.05元。"""
    check_points = {
        "_": [
            {
                "key": "十二-合并利润表",
                "attrs": [
                    {"path": ["当年净利润"], "check_func": partial(check_amount, "当年净利润")},
                    {"path": ["上年净利润"], "check_func": partial(check_amount, "上年净利润")},
                    {"path": ["上年基本每股收益"], "check_func": partial(check_amount, "上一年年度每股收益")},
                ],
            }
        ]
    }

    def __init__(self):
        super(OperatingResult, self).__init__(self.name)

    def organize_output(self, rows: list[InspectItem]) -> list[InspectItem]:
        summary_item = InspectItem.new(second_rule="AI判定", result=ComplianceStatus.COMPLIANCE)
        summary_item.detail["description"] = self.description
        ret = []
        for row in rows:
            item = ProfitSum.new(row.detail["sub_cols"]).check(self.meta.get("业绩预告", []))
            if not item:
                continue
            ret.append(item)
            if item.result != ComplianceStatus.DIS_IN_TIME:
                summary_item.result = ComplianceStatus.NONCOMPLIANCE
                summary_item.comment = ComplianceStatus.status_anno_map()[summary_item.result]
        if not ret:
            summary_item.detail["comment_annotation"] = "未发生该规则相关事项"
        return [summary_item] + ret
