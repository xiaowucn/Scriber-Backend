import re
from copy import deepcopy
from datetime import datetime

from remarkable.common.constants import ComplianceStatus
from remarkable.common.util import clean_txt
from remarkable.converter.utils import date_from_text
from remarkable.plugins.predict.answer import AnswerNode
from remarkable.pw_models.model import NewFileMeta
from remarkable.rule.rule import InspectItem, gen_answer_node, revise_answer


def get_date_range(report_year):
    # 临时文档查询时间范围当年1月1日至次年4月30日
    ranges = [
        datetime.strptime(str(report_year), "%Y"),
        datetime.strptime(f"{report_year + 1}0430", "%Y%m%d"),
    ]
    return [int(i.timestamp()) for i in ranges]


class RelatedDocBase:
    _date_format = "%Y年%m月%d日"
    common_key = "公告日期"
    group_key = ""
    primary_key = ""
    attr_path_map = {}
    display_attrs = []

    def __init__(self, doc: NewFileMeta):
        self.event_date: InspectItem | None = None
        self.primary_item: InspectItem | None = None
        self.meta = doc
        self._pos = {"file_id": doc.file_id}

    @property
    def pos(self):
        """从detail.data中取出文本框定位信息"""
        if not self._pos.get("data"):
            for _attr in self.attr_path_map:
                data = getattr(self, _attr, InspectItem.new()).detail.pop("data", None)
                if data and not self._pos.get("data"):
                    self._pos["data"] = data
                    self._pos["label"] = getattr(self, _attr).detail.pop("label")
        return self._pos

    @property
    def pub_date(self):
        return datetime.fromtimestamp(self.meta.publish_time).strftime(self._date_format)

    def matched_extra_cols(self, items, base_item):
        if not self.is_match(items, base_item):
            return ComplianceStatus.DIS_NONE, []
        ret = [
            InspectItem.new(second_rule="临时公告", comment=self.meta.title, comment_pos=self.pos),
        ]
        for attr_item in self.display_attrs:
            # 额外的显示项
            ret.append(
                InspectItem.new(second_rule=attr_item["label"], comment=getattr(self, attr_item["attr"]).comment)
            )
        # 公告披露日期取自深交所披露网站, 无定位信息
        pub_date_item = InspectItem.new(second_rule="公告披露日期", comment=self.pub_date)
        status = (
            ComplianceStatus.DIS_IN_TIME
            if self.less_than(self.event_date, pub_date_item)
            else ComplianceStatus.DIS_DELAY
        )
        ret.extend(
            [
                self.event_date,
                pub_date_item,
                InspectItem.new(
                    second_rule="公告披露日期 - 事项发生日期",
                    comment="≤30" if status == ComplianceStatus.DIS_IN_TIME else "＞30",
                ),
            ]
        )
        return status, ret

    def is_match(self, items: list[InspectItem], base_item: InspectItem):
        if base_item and self.primary_item and self.primary_item.comment != base_item.comment:
            return False
        return any(i.amount == getattr(self, _attr).amount for _attr in self.attr_path_map for i in items)

    @staticmethod
    def less_than(event_date: InspectItem, pub_date: InspectItem, days=30):
        """给定两inspect item日期差额是否低于指定天数"""
        return event_date.date and pub_date.date and abs((event_date.date - pub_date.date).days) <= days

    @classmethod
    def find_earliest_date(cls, answer_node: AnswerNode):
        """从xx发生日期、股东大会日期、董事会日期等xxx日期字段中找出最早的一个作为事项发生日期"""
        date_items = []
        for ans in [revise_answer(ans_node) for name, ans_node in answer_node.branches() if name.endswith("日期")]:
            if date_from_text(clean_txt(ans.data.plain_text)):
                date_items.append(ans)
        return min(date_items, key=lambda x: date_from_text(clean_txt(x.data.plain_text))) if date_items else None

    @classmethod
    def load(cls, files: list[NewFileMeta]):
        for file_meta in files:
            if not file_meta.questions:
                continue
            answer_node = gen_answer_node(file_meta.questions[0])  # Hardcode
            if not answer_node or cls.common_key not in answer_node or cls.group_key not in answer_node:
                # 标注不完全的字段需要跳过
                continue
            event_date = revise_answer(answer_node[cls.common_key])
            for node in [n for _, n in answer_node[cls.group_key].items() if not n.isleaf()]:
                instance = cls(file_meta)
                earliest_date = cls.find_earliest_date(node)
                if not earliest_date:
                    # 可能"xxx日期"字段都没有标注, 只能用"公告日期"替代
                    earliest_date = deepcopy(event_date)
                date = date_from_text(clean_txt(earliest_date.data.plain_text))
                instance.event_date = InspectItem.new(
                    schema_cols=earliest_date.fullpath.split("_"),
                    second_rule="事项发生日期",
                    comment=date.strftime(cls._date_format) if date else earliest_date.data.plain_text,
                    detail={"data": earliest_date.data.data, "label": "事项发生日期"},
                )
                for _attr, path in {**cls.attr_path_map, "primary_item": cls.primary_key}.items():
                    if path in node:
                        ans = revise_answer(node[path])
                        setattr(
                            instance,
                            _attr,
                            InspectItem.new(
                                schema_cols=ans.fullpath.split("_"),
                                second_rule=path,
                                comment="".join([t.split(":")[-1].strip() for t in ans.data.plain_text.split("|")]),
                                detail={"data": ans.data.data, "label": path},
                            ),
                        )
                    else:
                        # 有些属性并不一定会标注, 所以这里会取不到, 默认给配"未披露"
                        setattr(instance, _attr, InspectItem.new(second_rule=path, result=ComplianceStatus.DIS_NONE))
                yield instance


class RuleBakery:
    suffix_p = re.compile(r"_(金额|单位|币种)$")
    _case_map = {}
    _attr_label_map = {}
    related_docs = []

    @staticmethod
    def has_content(item: InspectItem | None):
        return item and item.result not in (ComplianceStatus.NONCONTAIN, ComplianceStatus.DIS_NONE) and item.comment

    @classmethod
    def _update_attr(cls, items: list[InspectItem], instance=None):
        if instance is None:
            instance = cls()
        for item in items:
            for _attr, label in cls._attr_label_map.items():
                if (
                    item.second_rule == label
                    or cls.path_str(item) == label
                    and item.result != ComplianceStatus.NONCONTAIN
                ):
                    item.second_rule = label
                    setattr(instance, _attr, item)
                    break
        return instance

    @classmethod
    def path_str(cls, item: InspectItem) -> str:
        # ['年报信息提取及合规判断POC-年报:0', '十二-合并资产负债表:0', '当年总资产:0', '金额:0'] -> '十二-合并资产负债表_当年总资产'
        return cls.suffix_p.sub("", "_".join([i.split(":")[0] for i in item.schema_cols[1:]]))

    @classmethod
    def new(cls, items: list[InspectItem]):
        return cls._update_attr(items)

    def gen_extra_cols(
        self, items: list[InspectItem], base_item: InspectItem | None = None
    ) -> tuple[ComplianceStatus, list[InspectItem]]:
        default = ComplianceStatus.DIS_NONE, [InspectItem.new(second_rule="临时公告", comment="无")]
        return next(
            filter(lambda x: x[-1], [doc.matched_extra_cols(items, base_item) for doc in self.related_docs]), default
        )

    def update(self, items: list[InspectItem]):
        self._update_attr(items, self)
        for _attr, label in self._attr_label_map.items():
            if getattr(self, _attr) is None:
                setattr(self, _attr, InspectItem.new(second_rule=label, result=ComplianceStatus.DIS_NONE))

    def check(self, related_docs: list[NewFileMeta]):
        raise NotImplementedError
