from remarkable.common.constants import ComplianceStatus
from remarkable.pw_models.model import NewFileMeta
from remarkable.rule.rule import InspectItem
from remarkable.rule.szse_poc.rules.operating_result import OperatingResult, ProfitSum, RelatedDoc


class CorrectProfitSum(ProfitSum):
    def load_related_docs(self, related_docs: list[NewFileMeta]):
        docs = [d for d in related_docs if "修正" in d.title]
        if related_docs and not self.related_docs:
            self.related_docs = list(RelatedDoc.load(docs))


class CorrectOperatingResult(OperatingResult):
    name = "上市公司预计本期业绩与已披露的业绩预告差异较大的，应当及时披露业绩预告修正公告"

    def organize_output(self, rows: list[InspectItem]) -> list[InspectItem]:
        summary_item = InspectItem.new(second_rule="AI判定", result=ComplianceStatus.COMPLIANCE)
        summary_item.detail["description"] = self.description
        ret = []
        for row in rows:
            item = CorrectProfitSum.new(row.detail["sub_cols"]).check(self.meta.get("业绩预告", []))
            if not item:
                continue
            ret.append(item)
            if item.result != ComplianceStatus.DIS_IN_TIME:
                summary_item.result = ComplianceStatus.NONCOMPLIANCE
                summary_item.comment = ComplianceStatus.status_anno_map()[summary_item.result]
        if not ret:
            summary_item.detail["comment_annotation"] = "未发生该规则相关事项"
        return [summary_item] + ret
