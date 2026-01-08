from remarkable.common.constants import ComplianceStatus
from remarkable.rule.rule import InspectItem
from remarkable.rule.ssepoc.rules import POChecker


class CoreStaffChange(POChecker):
    check_points = {
        "披露核心技术人员认定情况": [
            {
                "key": "董监高核（核心技术人员情况）",
                "attrs": [
                    {
                        "path": ["核心技术人员认定情况"],
                    },
                ],
            },
            {
                "key": "董监高核（业务与技术）",
                "attrs": [
                    {
                        "path": ["核心技术人员认定情况"],
                    },
                ],
            },
        ],
        "披露核心技术人员认定依据": [
            {
                "key": "董监高核（核心技术人员情况）",
                "attrs": [
                    {
                        "path": ["核心技术人员认定依据"],
                    },
                ],
            },
            {
                "key": "董监高核（业务与技术）",
                "attrs": [
                    {
                        "path": ["核心技术人员认定依据"],
                    },
                ],
            },
        ],
    }

    def organize_output(self, rows: list[InspectItem]) -> list[InspectItem]:
        ret = []
        groups = {key: [] for key in self.check_points}
        for row in rows:
            groups[row.second_rule].append(row)

        for key, items in groups.items():
            items = [i for i in items if i.result == ComplianceStatus.COMPLIANCE]
            new_item = InspectItem.new(schema_cols=items[0].schema_cols if items else [], second_rule=key, comment="")
            if key.endswith("情况"):
                if items:
                    new_item.comment = "是"
                else:
                    new_item.result = ComplianceStatus.NONCOMPLIANCE
            else:
                if items:
                    new_item.result = ComplianceStatus.COMPLIANCE
                else:
                    new_item.result = ComplianceStatus.NONCOMPLIANCE
            ret.append(new_item)
        return ret
