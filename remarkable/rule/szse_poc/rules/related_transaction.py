from copy import deepcopy
from functools import partial

from remarkable.common.constants import ComplianceStatus
from remarkable.pw_models.model import NewFileMeta
from remarkable.rule.rule import InspectItem
from remarkable.rule.ssepoc.rules import POChecker
from remarkable.rule.ssepoc.rules.shareholder import check_amount
from remarkable.rule.szse_poc.rules import RelatedDocBase, RuleBakery


class RelatedDoc(RelatedDocBase):
    primary_key = "交易对方"
    group_key = "与关联人的交易"
    attr_path_map = {
        "trade_amount": "交易金额",
        "guarantee_amount": "担保金额",
    }


class RelatedTrans(RuleBakery):
    _case_map = {
        "case_1": "上市公司与关联自然人发生的交易金额在三十万元以上的关联交易",
        "case_2": "上市公司与关联法人发生的交易金额在三百万元以上，且占上市公司最近一期经审计净资产绝对值0.5％以上的关联交易",
    }
    _attr_label_map = {
        "counterparty": "交易对方",
        "guaranteed_party": "被担保方",
        "guarantee_amount": "担保金额",
        "trade_amount": "交易金额",
        # 'guarantee_date': '担保发生日期',
        # 'trade_date': '交易日期',
        "related_party_type": "关联方类型",
        "total_asset": "当年总资产",
    }

    related_docs: list[NewFileMeta] = []
    counterparty: InspectItem | None = None  # 交易对方
    guaranteed_party: InspectItem | None = None  # 被担保方
    guarantee_amount: InspectItem | None = None  # 担保金额
    trade_amount: InspectItem | None = None  # 交易金额
    # guarantee_date: Optional[InspectItem] = None  # 担保发生日期
    # trade_date: Optional[InspectItem] = None  # 交易日期
    related_party_type: InspectItem | None = None  # 关联方类型
    total_asset: InspectItem | None = None  # 当年总资产

    @property
    def party(self):
        # 交易对方/被担保方
        item = self.guaranteed_party if self.has_content(self.guaranteed_party) else self.counterparty
        item.second_rule = "交易对方"
        item.result = ComplianceStatus.DIS_IN_TIME
        item.detail["sub_cols"].append(InspectItem.new(second_rule=item.second_rule, comment=item.comment))
        return item

    @property
    def amount(self):
        # 交易金额/担保金额
        item = self.guaranteed_party if self.has_content(self.guaranteed_party) else self.counterparty
        item.result = ComplianceStatus.DIS_IN_TIME
        return item

    def check(self, related_docs: list[NewFileMeta]):
        if related_docs and not self.related_docs:
            self.related_docs = list(RelatedDoc.load(related_docs))
        for case in self._case_map:
            result = getattr(self, f"check_{case}")()
            if result is not None:
                result.result, cols = self.gen_extra_cols([self.trade_amount], self.party)
                result.detail["extra_cols"].extend(cols)
                yield result

    def check_case_1(self):
        if not self.has_content(self.party) or not self.has_content(self.amount) or self.amount.amount <= 300000:
            return None

        item = deepcopy(self.party)
        item.detail["sub_cols"].extend(
            [
                InspectItem.new(second_rule="满足标准", comment=self._case_map["case_1"]),
                self.related_party_type,
                self.amount,
            ]
        )
        return item

    def check_case_2(self):
        if (
            not self.has_content(self.party)
            or not self.has_content(self.amount)
            or not self.has_content(self.total_asset)
            or self.amount.amount <= 3000000
            or abs(self.amount.amount / self.total_asset.amount) <= 0.005
        ):
            return None

        item = deepcopy(self.party)
        item.detail["sub_cols"].extend(
            [
                InspectItem.new(second_rule="满足标准", comment=self._case_map["case_2"]),
                self.related_party_type,
                self.amount,
                self.total_asset,
            ]
        )
        return item


class RelatedTransaction(POChecker):
    name = "上市公司与关联方发生交易达到一定标准的，应及时披露临时公告"
    description = """10.2.3【1】上市公司与关联自然人发生的交易金额在三十万元以上的关联交易，应当及时披露。
10.2.4【3】上市公司与关联法人发生的交易金额在三百万元以上，且占上市公司最近一期经审计净资产绝对值0.5％以上的关联交易，应当及时披露。
"""
    _case_map = {
        "case_1": "满足标准：上市公司与关联自然人发生的交易金额在三十万元以上的关联交易",
        "case_2": "满足标准：上市公司与关联法人发生的交易金额在三百万元以上，且占上市公司最近一期经审计净资产绝对值0.5％以上的关联交易",
    }
    check_points = {
        "multi": [
            {
                "key": "五-关联交易",
                "attrs": [
                    {
                        "path": ["被担保方"],
                    },
                    {
                        "path": ["交易对方"],
                    },
                    {
                        "path": ["交易对方"],
                    },
                    {"path": ["交易金额"], "check_func": partial(check_amount, "交易金额")},
                    {"path": ["担保金额"], "check_func": partial(check_amount, "交易金额")},
                ],
            },
        ],
        "single": [  # summary性质字段, 通常只有一组
            {
                "key": "十二-合并资产负债表",
                "attrs": [
                    {"path": ["当年总资产"], "check_func": partial(check_amount, "当年总资产")},
                ],
            },
        ],
    }

    def __init__(self):
        super(RelatedTransaction, self).__init__(self.name)

    def organize_output(self, rows: list[InspectItem]) -> list[InspectItem]:
        case_group = {k: [] for k in self.check_points}
        for row in rows:
            case_group[row.second_rule].append(row)
        ret = []
        transaction = RelatedTrans.new([r for i in case_group["single"] for r in i.detail["sub_cols"]])
        summary_item = InspectItem.new(second_rule="AI判定", result=ComplianceStatus.COMPLIANCE)
        summary_item.detail["description"] = self.description
        for row in case_group["multi"]:
            each_trans = deepcopy(transaction)
            each_trans.update(row.detail["sub_cols"])
            for item in each_trans.check(self.meta.get("关联交易", [])):
                ret.append(item)
                if item.result != ComplianceStatus.DIS_IN_TIME:
                    summary_item.result = ComplianceStatus.NONCOMPLIANCE
                    summary_item.comment = ComplianceStatus.status_anno_map()[summary_item.result]
        if not ret:
            summary_item.detail["comment_annotation"] = "未发生该规则相关事项"
        return [summary_item] + ret
