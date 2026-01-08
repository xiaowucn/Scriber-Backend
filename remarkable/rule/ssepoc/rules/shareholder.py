from functools import partial

from remarkable.common.constants import ComplianceStatus
from remarkable.common.util import clean_txt
from remarkable.rule.rule import InspectItem

from . import POChecker


def check_amount(second_rule: str, answer, pdfinsight, root_node, parent_node):
    res_item = InspectItem.new(second_rule=second_rule)
    text = answer.data.plain_text
    if text:
        res_item.result = ComplianceStatus.COMPLIANCE
        # 数值: 10,000.00|单位: 万元 -> 10,000.00万元
        res_item.comment = "".join([t.split(":")[-1].strip() for t in text.split("|")])
        res_item.schema_cols = answer.fullpath.split("_")
    else:
        res_item.result = ComplianceStatus.NONCONTAIN
        res_item.comment = ComplianceStatus.status_anno_map()[res_item.result]
    return res_item


class NewAddShareholder(POChecker):
    check_points = {
        "法人": [
            {
                "key": "新增股东",
                "group_by": "股东类型",
                "attrs": [
                    {
                        "path": ["名称"],
                    },
                    {
                        "path": ["成立时间（非自然人）"],
                    },
                    {
                        "path": ["注册资本（法人）"],
                        "check_func": partial(check_amount, "注册资本（法人）"),
                    },
                    {
                        "path": ["实收资本（法人）"],
                        "check_func": partial(check_amount, "实收资本（法人）"),
                    },
                    {
                        "path": ["注册地（法人）"],
                    },
                    {
                        "path": ["主要生产经营地（法人）"],
                    },
                    {
                        "path": ["股东构成（法人）"],
                    },
                    {
                        "path": ["实际控制人（法人）"],
                    },
                ],
            },
        ],
        "自然人": [
            {
                "key": "新增股东",
                "group_by": "股东类型",
                "attrs": [
                    {
                        "path": ["名称"],
                    },
                    {
                        "path": ["国籍（自然人）"],
                    },
                    {
                        "path": ["是否拥有永久境外居留权（自然人）"],
                    },
                    {
                        "path": ["身份证号码（自然人）"],
                    },
                ],
            },
        ],
        "合伙企业": [
            {
                "key": "新增股东",
                "group_by": "股东类型",
                "attrs": [
                    {
                        "path": ["名称"],
                    },
                    {
                        "path": ["成立时间（非自然人）"],
                    },
                    {
                        "path": ["经营场所（合伙企业）"],
                    },
                    {
                        "path": ["出资人构成（合伙企业）"],
                    },
                ],
            }
        ],
    }

    def organize_output(self, rows: list[InspectItem]) -> list[InspectItem]:
        # 只要有"不存在新增股东"的描述即可认为没有新增股东
        empty_item = InspectItem.new(comment="否", second_rule="新增股东")
        if not rows:
            return [empty_item]
        not_exists = [i for i in rows if "不存在新增股东" in clean_txt(i.comment)]
        if not_exists:
            # 确切有"不存在新增股东"的描述, 需要增加定位信息
            empty_item.schema_cols = not_exists[0].schema_cols
            return [empty_item]

        empty_item.comment = "是"
        adds = [
            empty_item,
            InspectItem.new(comment=f"{len(rows)}", second_rule="新增股东个数"),
        ]

        return adds + rows
