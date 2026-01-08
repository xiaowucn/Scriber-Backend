from remarkable.common.constants import ComplianceStatus
from remarkable.rule.rule import InspectItem
from remarkable.rule.ssepoc.rules import POChecker


class Completeness(POChecker):
    """完备性检查"""

    check_points = {
        "年报披露完备性-公司应当简要介绍报告期内公司主要资产发生的重大变化": [
            {
                "key": "三-主要资产发生的重大变化",
                "attrs": [
                    {
                        "path": ["主要资产发生的重大变化"],
                    }
                ],
            },
        ],
        "年报披露完备性-公司应当简要介绍报告期内公司从事的主要业务": [
            {
                "key": "三-从事的主要业务",
                "attrs": [
                    {
                        "path": ["从事的主要业务"],
                    }
                ],
            },
        ],
        "年报披露完备性-公司应当介绍报告期内重大资产和股权出售情况": [
            {
                "key": "四-重大资产和股权出售2",
                "attrs": [
                    {
                        "path": ["是否有重大资产和股权出售"],
                    }
                ],
            },
        ],
        "年报披露完备性-公司应当披露公司主要控股参股公司分析": [
            {
                "key": "四-主要控股参股公司分析",
                "attrs": [
                    {
                        "path": ["是否分析了主要控股参股公司"],
                    }
                ],
            },
        ],
        "年报披露完备性-公司应当披露报告期内重大诉讼、仲裁事项": [
            {
                "key": "五-重大诉讼、仲裁事项",
                "attrs": [
                    {
                        "path": ["重大诉讼、仲裁事项"],
                    }
                ],
            },
        ],
        "年报披露完备性-公司应当披露“归属于上市公司股东的扣除非经常性损益后的净利润”": [
            {
                "key": "二-非经常性损益",
                "attrs": [
                    {
                        "path": ["非经常性损益表"],
                    }
                ],
            },
        ],
        "年报披露完备性-公司应当披露报告期内核心竞争力的重要变化及对公司所产生的影响": [
            {
                "key": "三-核心竞争力分析",
                "attrs": [
                    {
                        "path": ["核心竞争力分析"],
                    }
                ],
            },
        ],
        "年报披露完备性-公司应当披露未来发展展望": [
            {
                "key": "四-公司未来发展展望",
                "attrs": [
                    {
                        "path": ["公司未来发展展望"],
                    }
                ],
            },
        ],
        "年报披露完备性-公司发生控股股东及其关联方非经营性占用资金情况的，应当进行披露": [
            {
                "key": "五-控股股东及其关联方非经营性占用资金情况及专项审核意见",
                "attrs": [
                    {
                        "path": ["控股股东及其关联方非经营性占用资金情况章节"],
                    }
                ],
            },
        ],
        "年报披露完备性-公司应当披露报告期内公司及其控股股东、实际控制人的诚信状况": [
            {
                "key": "五-控股股东、实际控制人的诚信状况章节",
                "attrs": [
                    {
                        "path": ["控股股东、实际控制人的诚信状况章节"],
                    }
                ],
            },
        ],
    }

    def __init__(self, name):
        assert name, "Valid rule name required"
        self.check_points = {k: v for k, v in self.check_points.items() if k == name}
        super(Completeness, self).__init__(name)

    def organize_output(self, rows: list[InspectItem]) -> list[InspectItem]:
        ret = []
        groups = {key: [] for key in self.check_points}
        for row in rows:
            groups[row.second_rule].append(row)

        for items in groups.values():
            items = [i for i in items if i.result == ComplianceStatus.COMPLIANCE]
            new_item = InspectItem.new(
                schema_cols=items[0].schema_cols if items else [], second_rule="AI判定", comment=""
            )
            new_item.result = ComplianceStatus.COMPLIANCE if items else ComplianceStatus.NONCOMPLIANCE
            new_item.comment = ComplianceStatus.status_anno_map()[new_item.result]
            ret.append(new_item)
        return ret
