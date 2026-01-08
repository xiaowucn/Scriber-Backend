import decimal
from collections import defaultdict
from copy import deepcopy
from functools import partial

from remarkable.common.constants import ComplianceStatus
from remarkable.pw_models.model import NewFileMeta
from remarkable.rule.rule import InspectItem
from remarkable.rule.ssepoc.rules import POChecker
from remarkable.rule.ssepoc.rules.shareholder import check_amount
from remarkable.rule.szse_poc.rules import RelatedDocBase, RuleBakery


def revise_amount(second_rule: str, answer, pdfinsight, root_node, parent_node) -> InspectItem:
    """
    四-重大资产和股权出售
        标的经营情况
            报告期
            标的营业收入
            标的营业收入单位
            标的营业收入币种
            标的净利润
            标的净利润币种
            标的净利润币种
    """
    res_item = InspectItem.new(second_rule=second_rule)
    text = answer.data.plain_text
    if text:
        kv_map = defaultdict(str)
        for i in text.split("\n")[0].split("|"):
            k, v = i.split(":")
            kv_map[k.strip()] = v.strip()
        # 标的营业收入: 126,209,549.35|标的营业收入单位: 元 -> 126,209,549.35元
        # 标的净利润: 126,209,549.35|标的净利润单位: 元 -> 126,209,549.35元
        res_item.comment = kv_map[f"{second_rule}币种"] + kv_map[second_rule] + kv_map[f"{second_rule}单位"]
        res_item.schema_cols = answer.fullpath.split("_")
        res_item.result = ComplianceStatus.COMPLIANCE if res_item.comment else ComplianceStatus.NONCONTAIN
    else:
        res_item.result = ComplianceStatus.NONCONTAIN
        res_item.comment = ComplianceStatus.status_anno_map()[res_item.result]
    return res_item


class RelatedDoc(RelatedDocBase):
    primary_key = "交易对方"
    group_key = "交易是否及时披露"
    attr_path_map = {
        "trade_amount": "交易金额",
    }


class Transaction(RuleBakery):
    _case_map = {
        "case_1": "交易涉及的资产总额占上市公司最近一期经审计总资产的10%以上，该交易涉及的资产总额同时存在账面值和评估值的，以较高者作为计算数据",
        "case_2": "交易标的(如股权)在最近一个会计年度相关的净利润占上市公司最近一个会计年度经审计净利润的10％以上，且绝对金额超过一百万元",
        "case_3": "交易标的(如股权)在最近一个会计年度相关的营业收入占上市公司最近一个会计年度经审计营业收入的10％以上，且绝对金额超过一千万元",
        "case_4": "交易的成交金额（含承担债务和费用）占上市公司最近一期经审计净资产的10％以上，且绝对金额超过一千万元",
        "case_5": "交易产生的利润占上市公司最近一个会计年度经审计净利润的10％以上，且绝对金额超过一百万元",
    }
    _attr_label_map = {
        "counterparty": "交易对方",
        "guaranteed_party": "被担保方",
        "book_value": "账面值",
        "assessed_value": "评估值",
        "trade_amount": "交易金额",
        "guarantee_amount": "担保金额",
        "target_net_asset": "标的净利润",
        "trade_profit": "交易产生的利润",
        "target_operating_income": "标的营业收入",
        "trade_date": "交易日期",
        "guarantee_date": "担保发生日期",
        "pub_date": "披露日期",
        "total_asset": "上市公司当年总资产",
        "net_asset": "上市公司当年净资产",
        "net_profit": "上市公司当年净利润",
        "operating_income": "上市公司当年营业收入",
    }
    related_docs: list[NewFileMeta] = []
    counterparty: InspectItem | None = None  # 交易对方
    guaranteed_party: InspectItem | None = None  # 被担保方
    book_value: InspectItem | None = None  # 账面值
    assessed_value: InspectItem | None = None  # 评估值
    trade_amount: InspectItem | None = None  # 交易金额
    guarantee_amount: InspectItem | None = None  # 担保金额
    target_net_asset: InspectItem | None = None  # 标的净利润
    trade_profit: InspectItem | None = None  # 交易产生的利润
    target_operating_income: InspectItem | None = None  # 标的营业收入
    trade_date: InspectItem | None = None  # 交易日期
    guarantee_date: InspectItem | None = None  # 担保发生日期
    pub_date: InspectItem | None = None  # 披露日期
    total_asset: InspectItem | None = None  # 上市公司当年总资产
    net_asset: InspectItem | None = None  # 上市公司当年净资产
    net_profit: InspectItem | None = None  # 上市公司当年净利润
    operating_income: InspectItem | None = None  # 上市公司当年营业收入
    _party: InspectItem | None = None  # 交易对方/被担保方

    @property
    def party(self):
        if not self._party:
            # 交易对方/被担保方至少会出现一个
            item = deepcopy(self.guaranteed_party if self.has_content(self.guaranteed_party) else self.counterparty)
            item.second_rule = "交易对象"
            item.result = ComplianceStatus.DIS_IN_TIME
            item.detail["sub_cols"].append(InspectItem.new(second_rule=item.second_rule, comment=item.comment))
            self._party = item
        return self._party

    @property
    def max_amount(self) -> decimal.Decimal:
        return max(self.book_value.amount, self.assessed_value.amount, self.trade_amount.amount)

    def check(self, related_docs: list[NewFileMeta]):
        if related_docs and not self.related_docs:
            self.related_docs = list(RelatedDoc.load(related_docs))
        for case in self._case_map:
            result = getattr(self, f"check_{case}")()
            if result is not None:
                yield result

    def check_case_1(self):
        if (
            not self.has_content(self.trade_amount)
            or not self.has_content(self.total_asset)
            or not self.has_content(self.book_value)
            or not self.has_content(self.assessed_value)
            or abs(self.max_amount / self.total_asset.amount) <= 0.1
        ):
            return None

        item = deepcopy(self.party)
        item.detail["sub_cols"].extend(
            [
                InspectItem.new(second_rule="满足标准", comment=self._case_map["case_1"]),
                self.trade_amount,
                self.total_asset,
                self.book_value,
                self.assessed_value,
            ]
        )
        item.result, cols = self.gen_extra_cols([self.trade_amount, self.book_value, self.assessed_value], self.party)
        item.detail["extra_cols"].extend(cols)
        return item

    def check_case_2(self):
        if (
            not self.has_content(self.target_net_asset)
            or not self.has_content(self.net_profit)
            or abs(self.target_net_asset.amount / self.net_profit.amount <= 0.1)
            or abs(self.target_net_asset.amount) <= 1000000
        ):
            return None

        item = deepcopy(self.party)
        item.detail["sub_cols"].extend(
            [
                InspectItem.new(second_rule="满足标准", comment=self._case_map["case_2"]),
                self.target_net_asset,
                self.net_profit,
            ]
        )
        item.result, cols = self.gen_extra_cols([self.target_net_asset], self.party)
        item.detail["extra_cols"].extend(cols)
        return item

    def check_case_3(self):
        if (
            not self.has_content(self.target_operating_income)
            or not self.has_content(self.operating_income)
            or abs(self.target_operating_income.amount / self.operating_income.amount) <= 0.1
            or abs(self.target_operating_income.amount) <= 10000000
        ):
            return None

        item = deepcopy(self.party)
        item.detail["sub_cols"].extend(
            [
                InspectItem.new(second_rule="满足标准", comment=self._case_map["case_3"]),
                self.target_operating_income,
                self.operating_income,
            ]
        )
        item.result, cols = self.gen_extra_cols([self.target_operating_income], self.party)
        item.detail["extra_cols"].extend(cols)
        return item

    def check_case_4(self):
        if (
            not self.has_content(self.trade_amount)
            or not self.has_content(self.net_asset)
            or abs(self.trade_amount.amount / self.net_asset.amount) <= 0.1
            or abs(self.trade_amount.amount) <= 10000000
        ):
            return None

        item = deepcopy(self.party)
        item.detail["sub_cols"].extend(
            [
                InspectItem.new(second_rule="满足标准", comment=self._case_map["case_4"]),
                self.trade_amount,
                self.net_asset,
            ]
        )
        item.result, cols = self.gen_extra_cols([self.trade_amount], self.party)
        item.detail["extra_cols"].extend(cols)
        return item

    def check_case_5(self) -> InspectItem | None:
        if (
            not self.has_content(self.trade_profit)
            or not self.has_content(self.net_profit)
            or abs(self.trade_profit.amount / self.net_profit.amount) <= 0.1
            or abs(self.trade_profit.amount) <= 1000000
        ):
            return None

        item = deepcopy(self.party)
        item.detail["sub_cols"].extend(
            [
                InspectItem.new(second_rule="满足标准", comment=self._case_map["case_5"]),
                self.trade_profit,
                self.net_profit,
            ]
        )
        item.result, cols = self.gen_extra_cols([self.trade_profit], self.party)
        item.detail["extra_cols"].extend(cols)
        return item


class TransactionStandard(POChecker):
    description = """9.2【5】上市公司发生的交易达到下列标准之一的，应当及时披露：
（一） 交易涉及的资产总额占上市公司最近一期经审计总资产的10%以上，该交易涉及的资产总额同时存在账面值和评估值的，以较高者作为计算数据；
（二） 交易标的(如股权)在最近一个会计年度相关的营业收入占上市公司最近一个会计年度经审计营业收入的10％以上，且绝对金额超过一千万元；
（三） 交易标的(如股权)在最近一个会计年度相关的净利润占上市公司最近一个会计年度经审计净利润的10％以上，且绝对金额超过一百万元；
（四） 交易的成交金额（含承担债务和费用）占上市公司最近一期经审计净资产的10％以上，且绝对金额超过一千万元；
（五） 交易产生的利润占上市公司最近一个会计年度经审计净利润的10％以上，且绝对金额超过一百万元。"""
    name = "上市公司交易满足一定标准的，应及时披露临时公告"
    check_points = {
        "multi": [  # 多组交易对象
            {
                "key": "四-重大资产和股权出售",
                "attrs": [
                    {
                        "path": ["交易对方"],
                    },
                    {"path": ["账面值"], "check_func": partial(check_amount, "账面值")},
                    {"path": ["评估值"], "check_func": partial(check_amount, "评估值")},
                    {"path": ["交易金额"], "check_func": partial(check_amount, "交易金额")},
                    {"path": ["标的经营情况"], "check_func": partial(revise_amount, "标的净利润")},  # TODO: 同级组合
                    {"path": ["标的经营情况"], "check_func": partial(revise_amount, "标的营业收入")},  # TODO: 同级组合
                    {
                        "path": ["交易日期"],
                    },
                    {
                        "path": ["披露日期"],
                    },
                ],
            },
            {
                "key": "五-关联交易",
                "attrs": [
                    {
                        "path": ["交易对方"],
                    },
                    {"path": ["账面值"], "check_func": partial(check_amount, "账面值")},
                    {"path": ["评估值"], "check_func": partial(check_amount, "评估值")},
                    {"path": ["交易金额"], "check_func": partial(check_amount, "交易金额")},
                    {
                        "path": ["交易产生的利润"],
                    },
                    {
                        "path": ["被担保方"],
                    },
                    {"path": ["担保金额"], "check_func": partial(check_amount, "担保金额")},
                    {
                        "path": ["担保发生日期"],
                    },
                    {
                        "path": ["交易日期"],
                    },
                    {
                        "path": ["披露日期"],
                    },
                ],
            },
            {
                "key": "五-重大合同",
                "attrs": [
                    {
                        "path": ["被担保方"],
                    },
                    {"path": ["担保金额"], "check_func": partial(check_amount, "担保金额")},
                    {
                        "path": ["担保发生日期"],
                    },
                    {
                        "path": ["披露日期"],
                    },
                ],
            },
        ],
        "single": [  # summary性质字段, 通常只有一组
            {
                "key": "十二-合并资产负债表",
                "attrs": [
                    {"path": ["当年总资产"], "check_func": partial(check_amount, "上市公司当年总资产")},
                    {"path": ["当年所有者权益"], "check_func": partial(check_amount, "上市公司当年净资产")},
                ],
            },
            {
                "key": "十二-合并利润表",
                "attrs": [
                    {"path": ["当年净利润"], "check_func": partial(check_amount, "上市公司当年净利润")},
                    {"path": ["当年营业收入"], "check_func": partial(check_amount, "上市公司当年营业收入")},
                ],
            },
        ],
    }

    def __init__(self):
        super(TransactionStandard, self).__init__(self.name)

    def organize_output(self, rows: list[InspectItem]) -> list[InspectItem]:
        case_group = {k: [] for k in self.check_points}
        for row in rows:
            case_group[row.second_rule].append(row)
        ret = []
        transaction = Transaction.new([r for i in case_group["single"] for r in i.detail["sub_cols"]])
        summary_item = InspectItem.new(second_rule="AI判定", result=ComplianceStatus.COMPLIANCE)
        summary_item.detail["description"] = self.description
        for row in case_group["multi"]:
            each_trans = deepcopy(transaction)
            each_trans.update(row.detail["sub_cols"])
            for item in each_trans.check(self.meta.get("重大交易", [])):
                ret.append(item)
                if item.result != ComplianceStatus.DIS_IN_TIME:
                    summary_item.result = ComplianceStatus.NONCOMPLIANCE
                    summary_item.comment = ComplianceStatus.status_anno_map()[summary_item.result]
        if not ret:
            summary_item.detail["comment_annotation"] = "未发生该规则相关事项"
        return [summary_item] + ret
