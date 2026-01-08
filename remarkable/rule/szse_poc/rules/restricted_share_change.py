import re
from copy import deepcopy
from decimal import Decimal
from functools import partial

from remarkable.common.constants import ComplianceStatus
from remarkable.common.util import clean_txt
from remarkable.pw_models.model import NewFileMeta
from remarkable.rule.rule import InspectItem
from remarkable.rule.ssepoc.rules import POChecker
from remarkable.rule.ssepoc.rules.shareholder import check_amount
from remarkable.rule.szse_poc.rules import RuleBakery

from .entrusted_finance_management import RelatedDoc as RelatedDoc_


class RelatedDoc(RelatedDoc_):
    primary_key = "股东名称"
    group_key = "股权变动"
    attr_path_map = {
        "shareholder": "股东名称",
    }


class RestrictedShare(RuleBakery):
    _attr_label_map = {
        "total_equity": "总股本",
        "shareholder": "股东名称",
        "old_share_no": "期初股数",
        "new_share_no": "期末股数",
    }

    related_docs: dict[str, RelatedDoc] = {}
    total_equity: InspectItem | None = None  # 总股本
    shareholder: InspectItem | None = None  # 股东名称
    old_share_no: InspectItem | None = None  # 期初股数
    new_share_no: InspectItem | None = None  # 期末股数

    @staticmethod
    def to_string(val: Decimal):
        return round(val * 100, 2).to_eng_string() + "%"

    @property
    def shareholding_ratio(self):
        return self.old_share_no.amount / self.total_equity.amount

    @property
    def change_ratio(self):
        return (self.new_share_no.amount - self.old_share_no.amount) / self.old_share_no.amount

    def check(self, related_docs: list[NewFileMeta]):
        if related_docs and not self.related_docs:
            self.related_docs = {
                clean_txt(i.shareholder.comment): i
                for i in RelatedDoc.load(related_docs)
                if i.shareholder.result != ComplianceStatus.DIS_NONE
            }

        # 略过标注/提取不全或持股比例不足5%的情况
        if (
            not all(
                self.has_content(i) for i in (self.total_equity, self.shareholder, self.old_share_no, self.new_share_no)
            )
            or self.shareholding_ratio < 0.05
        ):
            return None

        shareholder_info = deepcopy(self.shareholder)
        shareholder_info.result = ComplianceStatus.DIS_IN_TIME
        shareholder_info.detail["sub_cols"].extend(
            [
                self.shareholder,
                self.old_share_no,
                self.total_equity,
                InspectItem.new(second_rule="持股比例", comment=self.to_string(self.shareholding_ratio)),
                self.new_share_no,
                InspectItem.new(second_rule="变动比例", comment=self.to_string(self.change_ratio)),
            ]
        )
        # NOTE: 需要模糊匹配么?
        related_doc = self.related_docs.get(clean_txt(shareholder_info.comment))
        if related_doc:
            shareholder_info.detail["extra_cols"].extend(
                [
                    InspectItem.new(
                        second_rule="临时公告", comment=related_doc.meta.title, comment_pos=related_doc.pos
                    ),
                    related_doc.shareholder,
                ]
            )
        else:
            shareholder_info.detail["extra_cols"].append(
                InspectItem.new(second_rule="临时公告", comment="无"),
            )
            shareholder_info.result = ComplianceStatus.DIS_NONE
        return shareholder_info


class RestrictedShareChange(POChecker):
    name = "持有公司5%以上股份的股东或者实际控制人持股情况或者控制公司的情况发生或者发生较大变化，应当及时披露临时公告"
    check_points = {
        "multi": [
            {
                "key": "六-限售股份变动情况",
                "attrs": [
                    {"path": ["股东名称"]},
                    {"path": ["期初限售股数"], "check_func": partial(check_amount, "期初股数")},
                    {"path": ["期末限售股数"], "check_func": partial(check_amount, "期末股数")},
                ],
            },
            {
                "key": "六-无限售股份变动情况",
                "attrs": [
                    {"path": ["股东名称"]},
                    {"path": ["期初股数"], "check_func": partial(check_amount, "期初股数")},
                    {"path": ["期末股数"], "check_func": partial(check_amount, "期末股数")},
                ],
            },
        ],
        "single": [  # summary性质字段, 通常只有一组
            {
                "key": "六-总股数",
                "attrs": [
                    {"path": ["变动前总股本"], "check_func": partial(check_amount, "总股本")},
                ],
            },
        ],
    }

    def __init__(self):
        super(RestrictedShareChange, self).__init__(self.name)

    def organize_output(self, rows: list[InspectItem]) -> list[InspectItem]:
        case_group = {k: [] for k in self.check_points}
        for row in rows:
            case_group[row.second_rule].append(row)
        ret = []
        restricted_share = RestrictedShare.new([r for i in case_group["single"] for r in i.detail["sub_cols"]])
        summary_item = InspectItem.new(second_rule="AI判定", result=ComplianceStatus.COMPLIANCE)
        for row in case_group["multi"]:
            if re.search(r"[总合共小]计$", clean_txt(row.comment)):
                # 标注/提取到总计条目, 跳过
                continue
            each = deepcopy(restricted_share)
            each.update(row.detail["sub_cols"])
            shareholder_info = each.check(self.meta.get("股权变动", []))
            if not shareholder_info:
                continue
            ret.append(shareholder_info)
            if shareholder_info.result != ComplianceStatus.DIS_IN_TIME:
                summary_item.result = ComplianceStatus.NONCOMPLIANCE
                summary_item.comment = ComplianceStatus.status_anno_map()[summary_item.result]
        if not ret:
            summary_item.detail["comment_annotation"] = "未发生该规则相关事项"
        return [summary_item] + ret
