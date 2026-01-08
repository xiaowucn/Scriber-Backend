import json
import re
from collections import defaultdict
from enum import IntEnum
from typing import NamedTuple, TypeAlias

from remarkable.answer.common import EmptyAnswer
from remarkable.answer.reader import AnswerReader
from remarkable.common.constants import EnumMixin
from remarkable.common.util import compact_dumps
from remarkable.plugins.cgs.common.para_similarity import ParagraphSimilarity
from remarkable.predictor.mold_schema import MoldSchema

P_EMPTY_DIFF = re.compile(r"<s>[\r\n]+</s>")
P_NON_NUMERIC = re.compile(r"\D+")
P_SERIAL = re.compile(r"\d+")
P_DIFF_TAG = re.compile(r"<s>.+?</s>")


class CompareException(Exception):
    pass


class CompareStatus(EnumMixin, IntEnum):
    DEFAULT = 0  # 比对未开始
    FAILED = -2  # 文档对比失败
    DOING = 1  # 文档对比中
    DONE = 2  # 文档对比成功


AnswerGroup: TypeAlias = dict[str, list[dict]]


class MinimalQuestion(NamedTuple):
    fid: int
    answer: dict
    mold: dict


def get_serial(text: str) -> int:
    if matched := P_SERIAL.search(text):
        return int(matched.group())
    return 0


def group_answer_by_label(question: MinimalQuestion) -> AnswerGroup:
    answer_by_label = defaultdict(list)
    default_by_label = {
        item["schema"]["data"]["label"]: item for item in EmptyAnswer(question.mold).answer["userAnswer"]["items"]
    }
    answer_reader = AnswerReader(question.answer)
    item_by_default = {item["schema"]["data"]["label"]: item for item in answer_reader.items}
    # 只比对basic type的字段
    labels = sorted(MoldSchema(question.mold).basic_schema_labels, key=get_serial)
    for label in labels:
        item = item_by_default.get(label) or default_by_label[label]
        item["key"] = compact_dumps(json.loads(item["key"]))
        label = item["schema"]["data"]["label"]
        key = P_NON_NUMERIC.search(label).group()
        item["fid"] = question.fid
        answer_by_label[key].append(item)
    return answer_by_label


def single_question_diff(question):
    answer_groups = group_answer_by_label(question)
    answer_items = []
    for key, (base, *others) in answer_groups.items():
        equal = len(others) > 0  # 字段只有一个提取答案时按照不一致处理
        for other in others:
            if not other["data"]:
                equal = False
                continue
            diff = ParagraphSimilarity.compare_two_text(
                "".join(box["text"] for data in base["data"] for box in data["boxes"]),
                "".join(box["text"] for data in other["data"] for box in data["boxes"]),
            )
            equal &= diff.ratio == 1.0
        answer_items.append({"key": key, "equal": equal, "items": [base, *others]})
    return answer_groups, answer_items
