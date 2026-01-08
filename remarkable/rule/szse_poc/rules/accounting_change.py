from remarkable.common.constants import ComplianceStatus
from remarkable.pw_models.model import NewFileMeta
from remarkable.rule.rule import InspectItem
from remarkable.rule.ssepoc.rules import POChecker
from remarkable.rule.szse_poc.rules import RuleBakery


class AChange(RuleBakery):
    _attr_label_map = {
        "acc_change": "是否变更",
    }

    acc_change: InspectItem | None = None  # 是否变更

    def check(self, related_docs: list[NewFileMeta]):
        self.acc_change.result = ComplianceStatus.DIS_IN_TIME
        self.acc_change.detail["sub_cols"].append(
            InspectItem.new(second_rule=self.acc_change.second_rule, comment=self.acc_change.comment)
        )
        if not self.has_content(self.acc_change):
            return None
        if self.acc_change.comment == "否":
            # 合规
            return self.acc_change
        if not related_docs:
            self.acc_change.result = ComplianceStatus.DIS_NONE
            self.acc_change.detail["extra_cols"].append(InspectItem.new(second_rule="临时公告", comment="无"))
            return self.acc_change
        for item in related_docs:
            self.acc_change.detail["extra_cols"].append(
                InspectItem.new(second_rule="临时公告", comment=item.title, comment_pos={"file_id": item.file_id})
            )
        return self.acc_change


class AccountingChange(POChecker):
    name = "上市公司变更会计政策、会计估计，应当及时披露临时公告"
    description = """11.11.5【3】上市公司出现下列情形之一的，应当及时向本所报告并披露：
（三） 变更会计政策、会计估计；"""
    check_points = {
        "_": [
            {
                "key": "五-变更会计政策、会计估计",
                "attrs": [
                    {
                        "path": ["是否变更"],
                    },
                ],
            },
        ],
    }

    def __init__(self):
        super(AccountingChange, self).__init__(self.name)

    def organize_output(self, rows: list[InspectItem]) -> list[InspectItem]:
        summary_item = InspectItem.new(second_rule="AI判定", result=ComplianceStatus.COMPLIANCE)
        summary_item.detail["description"] = self.description
        ret = []
        if rows:
            item = AChange.new(rows[0].detail["sub_cols"]).check(self.meta.get("会计变更", []))
            if not item or item.comment == "否":
                summary_item.schema_cols = item.schema_cols if item else []
                return [summary_item]
            ret.append(item)
            if item.result != ComplianceStatus.DIS_IN_TIME:
                summary_item.result = ComplianceStatus.NONCOMPLIANCE
                summary_item.comment = ComplianceStatus.status_anno_map()[summary_item.result]
        return [summary_item] + ret
