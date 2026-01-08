from copy import deepcopy

from remarkable.common.constants import ComplianceStatus
from remarkable.pw_models.model import NewFileMeta
from remarkable.rule.rule import InspectItem
from remarkable.rule.ssepoc.rules import POChecker
from remarkable.rule.szse_poc.rules import RelatedDocBase, RuleBakery


class RelatedDoc(RelatedDocBase):
    group_key = "会计师事务所变更"
    attr_path_map = {"meeting_date": "董事会日期"}

    def is_match(self, items: list[InspectItem], base_item: InspectItem):
        """只要有公告就算匹配"""
        return True


class FirmChange(RuleBakery):
    _attr_label_map = {
        "current_change": "当期是否改聘会计师事务所",
        "audit_change": "是否在审计期间改聘会计师事务所",
    }

    related_docs: list[NewFileMeta] = []
    current_change: InspectItem | None = None  # 当期是否改聘会计师事务所
    audit_change: InspectItem | None = None  # 是否在审计期间改聘会计师事务所

    @property
    def change(self):
        item = self.audit_change if self.has_content(self.audit_change) else self.current_change
        item.result = ComplianceStatus.DIS_IN_TIME
        return item

    def check(self, related_docs: list[NewFileMeta]):
        item = deepcopy(self.change)
        if related_docs and not self.related_docs:
            self.related_docs = list(RelatedDoc.load(related_docs))
        if not self.has_content(item):
            return None
        if item.comment == "否":
            # 合规
            item.detail["extra_cols"].append(InspectItem.new(second_rule="临时公告", comment="无"))
            return item

        item.result, cols = self.gen_extra_cols([item])
        item.detail["extra_cols"].extend(cols)
        return item


class AccountingFirmChange(POChecker):
    name = "聘任、解聘为公司审计的会计师事务所，应当及时披露临时公告"
    description = """11.11.5【3】上市公司出现下列情形之一的，应当及时向本所报告并披露：
（十一）聘任、解聘为公司审计的会计师事务所"""
    check_points = {
        "_": [
            {
                "key": "五-聘任、解聘会计师事务所情况",
                "attrs": [
                    {
                        "path": ["当期是否改聘会计师事务所"],
                    },
                    {
                        "path": ["是否在审计期间改聘会计师事务所"],
                    },
                ],
            },
        ],
    }

    def __init__(self):
        super(AccountingFirmChange, self).__init__(self.name)

    def organize_output(self, rows: list[InspectItem]) -> list[InspectItem]:
        summary_item = InspectItem.new(second_rule="AI判定", result=ComplianceStatus.COMPLIANCE)
        summary_item.detail["description"] = self.description
        if rows:
            # 只会有一条描述或者没有
            item = FirmChange.new(rows[0].detail["sub_cols"]).check(self.meta.get("会计事务所变更", []))
            if not item:
                return [summary_item]
            if item.result != ComplianceStatus.DIS_IN_TIME:
                summary_item.result = ComplianceStatus.NONCOMPLIANCE
                summary_item.comment = ComplianceStatus.status_anno_map()[summary_item.result]
            summary_item.schema_cols = item.schema_cols
            summary_item.detail = {**summary_item.detail, **item.detail}
        return [summary_item]
