from functools import partial

from remarkable.common.constants import ComplianceStatus
from remarkable.pw_models.model import NewFileMeta
from remarkable.rule.rule import InspectItem
from remarkable.rule.ssepoc.rules import POChecker
from remarkable.rule.ssepoc.rules.shareholder import check_amount
from remarkable.rule.szse_poc.rules import RelatedDocBase, RuleBakery


class RelatedDoc(RelatedDocBase):
    primary_key = "被担保方"
    group_key = "提供担保"
    attr_path_map = {
        "guarantee_amount": "担保金额",
    }


class ProTrans(RuleBakery):
    _attr_label_map = {
        "guaranteed_party": "被担保方",
        "guarantee_amount": "担保金额",
        "guarantee_date": "担保发生日期",
        "announce_date": "披露日期",
    }

    related_docs: list[NewFileMeta] = []
    guaranteed_party: InspectItem | None = None  # 被担保方
    guarantee_amount: InspectItem | None = None  # 担保金额
    guarantee_date: InspectItem | None = None  # 担保发生日期
    announce_date: InspectItem | None = None  # 披露日期

    @property
    def event_date(self):
        return self.announce_date if self.has_content(self.announce_date) else self.guarantee_date

    def check(self, related_docs: list[NewFileMeta]):
        if related_docs and not self.related_docs:
            self.related_docs = list(RelatedDoc.load(related_docs))
        if not self.has_content(self.guaranteed_party) or not self.has_content(self.guarantee_amount):
            return None

        # issues/419#note_98006: 过滤掉 19 年以前的事项, 不做审核点的检查依据
        if self.event_date.date and self.event_date.date.year < 2019:
            return None

        self.guaranteed_party.result = ComplianceStatus.DIS_IN_TIME
        self.guaranteed_party.detail["sub_cols"].append(
            InspectItem.new(second_rule=self.guaranteed_party.second_rule, comment=self.guaranteed_party.comment),
        )
        if self.guarantee_amount.amount:
            # 金额不空才展示
            self.guaranteed_party.detail["sub_cols"].append(self.guarantee_amount)
        self.guaranteed_party.result, cols = self.gen_extra_cols([self.guarantee_amount], self.guaranteed_party)
        self.guaranteed_party.detail["extra_cols"].extend(cols)
        return self.guaranteed_party


class ProvideGuarantee(POChecker):
    name = "上市公司发生“提供担保”事项时，应当经董事会审议后及时对外披露临时公告"
    description = """9.11【2】上市公司发生规定的“提供担保”事项时，应当经董事会审议后及时对外披露。"""
    check_points = {
        "_": [
            {
                "key": "五-关联交易",
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
    }

    def __init__(self):
        super(ProvideGuarantee, self).__init__(self.name)

    def organize_output(self, rows: list[InspectItem]) -> list[InspectItem]:
        summary_item = InspectItem.new(second_rule="AI判定", result=ComplianceStatus.COMPLIANCE)
        summary_item.detail["description"] = self.description
        ret = []
        for row in rows:
            item = ProTrans.new(row.detail["sub_cols"]).check(self.meta.get("担保", []))
            if not item:
                continue
            ret.append(item)
            if item.result != ComplianceStatus.DIS_IN_TIME:
                summary_item.result = ComplianceStatus.NONCOMPLIANCE
                summary_item.comment = ComplianceStatus.status_anno_map()[summary_item.result]
        if not ret:
            summary_item.detail["comment_annotation"] = "未发生该规则相关事项"
        return [summary_item] + ret
