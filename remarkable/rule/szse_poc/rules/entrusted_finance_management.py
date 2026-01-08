from copy import deepcopy
from functools import partial

from remarkable.common.constants import ComplianceStatus
from remarkable.pw_models.model import NewFileMeta
from remarkable.rule.rule import InspectItem, gen_answer_node, revise_answer
from remarkable.rule.ssepoc.rules import POChecker
from remarkable.rule.ssepoc.rules.shareholder import check_amount
from remarkable.rule.szse_poc.rules import RelatedDocBase, RuleBakery


class RelatedDoc(RelatedDocBase):
    primary_key = "委托理财金额"
    group_key = "委托理财"
    attr_path_map = {
        "entrusted_finance": "委托理财金额",
    }

    def matched_extra_cols(self, items, base_item):
        ret = [
            InspectItem.new(second_rule="临时公告", comment=self.meta.title, comment_pos=self.pos),
            self.entrusted_finance,
        ]
        return ComplianceStatus.DIS_IN_TIME, ret

    @classmethod
    def load(cls, files: list[NewFileMeta]):
        for file_meta in files:
            if not file_meta.questions:
                continue
            answer_node = gen_answer_node(file_meta.questions[0])  # Hardcode
            if not answer_node or cls.group_key not in answer_node:
                # 标注不完全的字段需要跳过
                continue
            for node in [n for _, n in answer_node[cls.group_key].items() if not n.isleaf()]:
                instance = cls(file_meta)
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


class EntrustedFinance(RuleBakery):
    _case_map = {
        "case_1": "累计金额占上市公司最近一期经审计净资产的10％以上，且绝对金额超过一千万元",
        "case_2": "累计金额占上市公司最近一期经审计总资产的10%以上",
    }
    _attr_label_map = {
        "total_entrusted_finance": "委托理财发生额合计",
        "total_asset": "上市公司当年总资产",
        "net_asset": "上市公司当年净资产",
    }

    related_docs: list[RelatedDoc] = []
    total_entrusted_finance: InspectItem | None = None  # 委托理财发生额合计
    total_asset: InspectItem | None = None  # 上市公司当年总资产
    net_asset: InspectItem | None = None  # 上市公司当年净资产
    _total_pub_amount = 0

    @property
    def is_equal(self):
        return self.total_pub_amount == self.total_entrusted_finance.amount

    @property
    def total_pub_amount(self):
        if not self._total_pub_amount:
            for doc in self.related_docs:
                self._total_pub_amount += doc.primary_item.amount
        return self._total_pub_amount

    def check(self, related_docs: list[NewFileMeta]):
        if related_docs and not self.related_docs:
            self.related_docs = list(RelatedDoc.load(related_docs))
        for case in self._case_map:
            result = getattr(self, f"check_{case}")()
            if result is not None:
                result.result, cols = self.gen_extra_cols([self.total_entrusted_finance])
                result.detail["extra_cols"].extend(cols)
                yield result

    def check_case_1(self):
        if (
            not self.has_content(self.total_entrusted_finance)
            or not self.has_content(self.net_asset)
            or self.total_entrusted_finance.amount <= 10000000
            or abs(self.total_entrusted_finance.amount / self.net_asset.amount) <= 0.1
        ):
            return None

        item = deepcopy(self.total_entrusted_finance)
        item.detail["sub_cols"].extend(
            [
                InspectItem.new(second_rule="满足标准", comment=self._case_map["case_1"]),
                self.total_entrusted_finance,
                self.net_asset,
            ]
        )
        return item

    def check_case_2(self):
        if (
            not self.has_content(self.total_entrusted_finance)
            or not self.has_content(self.total_asset)
            or abs(self.total_entrusted_finance.amount / self.total_asset.amount) <= 0.1
        ):
            return None

        item = deepcopy(self.total_entrusted_finance)
        item.detail["sub_cols"].extend(
            [
                InspectItem.new(second_rule="满足标准", comment=self._case_map["case_2"]),
                self.total_entrusted_finance,
                self.total_asset,
            ]
        )
        return item


class EntrustedFinanceManagement(POChecker):
    name = "上市公司发生委托理财事项满足一定交易标准的，应当及时披露临时公告"
    description = """（一）累计金额占上市公司最近一期经审计总资产的10%以上
（四）累计金额占上市公司最近一期经审计净资产的10％以上，且绝对金额超过一千万元；
"""
    check_points = {
        "multi": [
            {
                "key": "五-重大合同-委托理财",
                "attrs": [
                    {"path": ["委托理财发生额合计"], "check_func": partial(check_amount, "委托理财发生额合计")},
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
        ],
    }

    def __init__(self):
        super(EntrustedFinanceManagement, self).__init__(self.name)

    def organize_output(self, rows: list[InspectItem]) -> list[InspectItem]:
        case_group = {k: [] for k in self.check_points}
        for row in rows:
            case_group[row.second_rule].append(row)
        ret = []
        entrusted_finance = EntrustedFinance.new([r for i in case_group["single"] for r in i.detail["sub_cols"]])
        summary_item = InspectItem.new(second_rule="AI判定", result=ComplianceStatus.COMPLIANCE)
        summary_item.detail["description"] = self.description
        for row in case_group["multi"]:
            each_entrusted_finance = deepcopy(entrusted_finance)
            each_entrusted_finance.update(row.detail["sub_cols"])
            for item in each_entrusted_finance.check(self.meta.get("委托理财", [])):
                ret.append(item)
                if item.result != ComplianceStatus.DIS_IN_TIME or not each_entrusted_finance.is_equal:
                    # 未披露或公告数额之和不等于年报披露数额, 不合规
                    summary_item.result = ComplianceStatus.NONCOMPLIANCE
                    summary_item.comment = ComplianceStatus.status_anno_map()[summary_item.result]
                if len(case_group["multi"]) == 1 and not each_entrusted_finance.is_equal:
                    # 年报仅披露一个事项且与公告披露金额不等, 需要额外增加展示信息
                    for sub_item in item.detail["sub_cols"]:
                        if sub_item.second_rule == "委托理财发生额合计":
                            sub_item.detail["comment_annotation"] = "金额不相符"
                    summary_item.detail["comment_annotation"] = "委托理财金额不相符"
        if not ret:
            summary_item.detail["comment_annotation"] = "未发生该规则相关事项"
        return [summary_item] + ret
