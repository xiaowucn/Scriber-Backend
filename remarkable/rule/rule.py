# CYC: skip-file
import decimal
import logging
import re
from collections import defaultdict
from copy import deepcopy
from datetime import datetime

import attr
from marshmallow import EXCLUDE, Schema, fields

from remarkable.answer.node import AnswerItem
from remarkable.common.constants import AuditStatusEnum, ComplianceStatus, SSEAuditStatus
from remarkable.common.util import clean_txt
from remarkable.converter.utils import date_from_text
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.predict.answer import AnswerNode, AnswerReader
from remarkable.predictor.base_prophet import find_item_elements
from remarkable.pw_models.model import NewFileMeta
from remarkable.pw_models.question import NewQuestion


@attr.s
class InspectItem:
    schema_cols: list[str] = attr.ib()  # NOTE: 用户答案与预测答案同时存在时, 据此定位会有问题, 考虑废弃
    result: int = attr.ib()
    audit_status: int = attr.ib()
    comment: str = attr.ib()
    comment_pos: dict = attr.ib()
    second_rule: str = attr.ib()
    detail: dict = attr.ib(converter=lambda x: {**{"sub_cols": [], "extra_cols": [], "position": {}}, **(x or {})})

    @result.validator
    def valid_res(self, _attribute, value):
        valid_res = ComplianceStatus.member_values() + SSEAuditStatus.member_values()
        if value not in valid_res:
            raise ValueError(f"Invalid result value, should be one of {valid_res}")

    @property
    def amount(self):
        # "人民币-10,076,190.80万元" -> "-100761908000.00"
        match = re.search(r"(?P<val>-?\d+(,\d+)*(\.\d+)?)(?P<unit>\D{0,4})$", clean_txt(self.comment))
        if not match:
            return decimal.Decimal("0")
        val = decimal.Decimal(match.group("val").replace(",", "") or "0")
        unit = match.group("unit")
        multipliers = {"十": 10, "拾": 10, "百": 100, "佰": 100, "千": 1000, "仟": 1000, "万": 10000, "亿": 100000000}
        multi = 1
        for word in unit:
            if word in multipliers:
                multi *= multipliers[word]
        return (val * multi).quantize(val, rounding=decimal.ROUND_HALF_UP)

    @property
    def date(self) -> datetime | None:
        """转换提取内容为日期格式"""
        return date_from_text(clean_txt(self.comment))

    @classmethod
    def new(cls, result: int | None = None, position: dict | None = None, **kwargs):
        if result is None:
            result = ComplianceStatus.IGNORE
        empty_instance = cls(
            [], result, AuditStatusEnum.UNAUDITED, ComplianceStatus.status_anno_map().get(result), {}, "", {}
        )
        instance = cls(**{**attr.asdict(empty_instance), **kwargs})
        if position:
            position.setdefault("label", instance.second_rule)
        instance.detail["position"].update(position or {})
        return instance


class AttrItemSchema(Schema):
    path = fields.List(fields.Str(), required=True)
    check_func = fields.Function(load_default=None)

    class Meta:
        unknown = EXCLUDE


class CheckPointItemSchema(Schema):
    key = fields.Str()
    group_by = fields.Str(load_default=None)
    group_value = fields.Str(load_default=None)
    check_func = fields.Function(load_default=None)
    attrs = fields.List(fields.Nested(AttrItemSchema))

    class Meta:
        unknown = EXCLUDE


class LegacyRule:
    def __init__(self, name):
        self.name = name

    def check(self, question, pdfinsight):
        """检查答案是否合规"""
        raise NotImplementedError()


class Rule:
    def __init__(self, name="", custom_config=None):
        self.name = name
        self.custom_config = custom_config

    def check_answers(
        self, answers: dict[str, AnswerNode], pdfinsight: PdfinsightReader, meta: defaultdict[str, list[NewFileMeta]]
    ):
        # NOTE: 如有新的合规检查类, 需要重写此方法
        answer_nodes = list(answers.values())
        return self.check(answer_nodes[0], pdfinsight, meta) if answer_nodes else []

    def check(
        self, answer: AnswerNode, pdfinsight: PdfinsightReader, meta: defaultdict[str, list[NewFileMeta]]
    ) -> list[InspectItem]:
        """检查答案是否合规"""
        raise NotImplementedError()

    async def prepare(self, doc: NewFile):
        """准备一些额外的数据"""
        logging.warning(f"File id: {doc.id} -> No need to prepare extra info for rule: {self.name}.")


class EmptyRule(Rule):
    def check(
        self, answer: AnswerNode, pdfinsight: PdfinsightReader, meta: defaultdict[str, list[NewFileMeta]]
    ) -> list[InspectItem]:
        return []


def flatten_node(node: AnswerNode):
    if node.isleaf():
        return node
    w_table = {"币种": 0, "金额": 1, "数值": 1, "单位": 2}
    # 保证输出顺序, 币种: xxx|金额: yyy|单位: zzz
    first, *others = sorted(deepcopy(node).descendants(only_leaf=True), key=lambda x: w_table.get(x.name, 3))
    if not first.isleaf():
        return flatten_node(first)
    plain_text = f"{first.name}: {first.data.plain_text.strip()}"
    for item in others:
        prefix = "\n" if item.name == first.name else "|"
        plain_text += f"{prefix}{item.name}: {item.data.plain_text.strip()}"
        # 优先选"金额"的定位信息
        if item.name in ("金额", "数值"):
            first = deepcopy(item)
    first.data.plain_text = plain_text
    return first


def revise_answer(answers: dict[int, AnswerNode] | None) -> AnswerNode:
    """整合当前节点的所有子节点标注文本内容到本节点, 其他信息以第一个子节点首项为准(不同子节点间用|隔开;多组子节点间用\n隔开)
    exp: 新增股东-法人 -> 注册资本 -> [数值, 单位, 币种] => 新增股东-法人 -> 注册资本: "数值: 132,400.00|单位: 万元|币种: 人民币"
    """
    if not answers:
        empty_node = AnswerNode([])
        empty_node.data = AnswerItem()
        answers = {0: empty_node}
    first, *others = answers.values()
    first = flatten_node(first)
    # 币种金额单位这类, 标多组的只取第一组(多半是标注错误)
    if first.name not in ("币种", "金额", "单位", "数值"):
        for item in others:
            first.data.plain_text += "\n" + flatten_node(item).data.plain_text
    return first


def gen_answer_node(question: NewQuestion, pdfinsight: PdfinsightReader | None = None) -> AnswerNode | None:
    answer_reader = AnswerReader(question.answer)
    if answer_reader.is_empty:
        # logging.warning(f'Empty answer detected: qid: {question.id}')
        return None
    root_node = answer_reader._tree
    if root_node.isleaf():
        # logging.warning(f"Can't find valid answer for question: {question.id}")
        return None
    if pdfinsight:
        for leaf_node in root_node.descendants(only_leaf=True):
            find_item_elements(pdfinsight, leaf_node.data)
    # Skip top root layer
    return root_node[answer_reader.main_schema["name"]][0]
