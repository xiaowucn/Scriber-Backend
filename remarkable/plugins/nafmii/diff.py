import logging
from dataclasses import dataclass
from functools import cached_property, total_ordering

from opencc import OpenCC

from remarkable.answer.node import AnswerItem
from remarkable.common.util import P_WHITE
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.pw_models.model import NewMold
from remarkable.pw_models.question import NewQuestion
from remarkable.service.compare import (
    P_SERIAL,
    CompareException,
    MinimalQuestion,
    group_answer_by_label,
)

logger = logging.getLogger(__name__)
CONVERTER = OpenCC("t2s")

FIELDS = (
    "发行人名称",
    "债项简称",
    "债项全称",
    "债项代码",
    "存续期管理机构",
    "受托管理人",
    "登记托管机构",
    "行权类别",
    "偿还类别",
)


def single_text_diff(question: MinimalQuestion, file: NewFile):
    reader = PdfinsightReader(file.pdfinsight_path(abs_path=True))
    answer_groups = group_answer_by_label(question)
    diff_answer = []
    for key, (base, *others) in answer_groups.items():
        if key not in FIELDS:
            continue
        base["equal"] = equal = True
        base["texts"], base["positions"] = [], []

        text_l = CONVERTER.convert(P_WHITE.sub("", AnswerItem(base["data"]).plain_text))
        _fill_text_and_position(base, reader)
        base["texts"] = base["texts"] or [text_l]
        others = list(filter(lambda x: x["data"], others))
        for other in others:
            other["texts"], other["positions"] = [], []
            _fill_text_and_position(other, reader)
            text_r = CONVERTER.convert(P_WHITE.sub("", AnswerItem(other["data"]).plain_text))
            other["texts"] = other["texts"] or [text_r]
            other["equal"] = text_l == text_r
            equal &= other["equal"]
        if key == "偿还类别":
            equal = diff_by_rule(base, *others)
        diff_answer.append({"key": key, "equal": equal, "items": [base, *others]})
    diff_answer.sort(key=lambda x: FIELDS.index(x["key"]))
    return diff_answer


def _fill_text_and_position(answer_item, reader):
    for item in answer_item["data"]:
        interdoc = reader.create_interdoc_from_answer([item])
        if paras := interdoc["paragraphs"]:
            answer_item["texts"].append("".join(para["text"] for para in paras))
        if answer_item["positions"]:
            continue
        answer_item["positions"].extend(_get_chapter(reader, interdoc))


def _get_chapter(reader: PdfinsightReader, interdoc: dict):
    """字段答案多个框的时候只取第一个框所在的章节"""
    for element in interdoc["orig_elements"]:
        syllabuses = reader.find_syllabuses_by_index(element["index"])
        for sy in syllabuses:
            yield sy["title"]
        break


@dataclass
@total_ordering
class AnswerForDiff:
    answer: dict

    def __bool__(self):
        return bool(self.answer["data"])

    def __eq__(self, other):
        return self.serial == other.serial

    def __lt__(self, other):
        return self.serial < other.serial

    @cached_property
    def serial(self) -> int:
        if matched := P_SERIAL.search(self.answer["schema"]["data"]["label"]):
            return int(matched.group())
        return 0

    @cached_property
    def text(self) -> str:
        return CONVERTER.convert(
            "".join(P_WHITE.sub("", box["text"]) for data in self.answer["data"] for box in data["boxes"])
        )


def diff_by_rule(base, *others) -> bool:
    base = AnswerForDiff(base)
    others = [AnswerForDiff(other) for other in others]
    equal = True
    for other in others:
        equal_ = True
        if base.text in ("利息支付", "付息"):
            if other.serial in (2, 3, 6, 7, 8, 9, 10):
                equal_ &= "付息" in other.text
            elif other.serial == 4:
                equal_ &= other.text == "利息兑付日"
            elif other.serial == 5:
                equal_ &= "本期应偿付利息" in other.text
        elif base.text in ("本金支付", "本金兑付"):
            if other.serial in (2, 3, 6, 7, 8, 9, 10):
                equal_ &= other.text == "兑付"
            elif other.serial == 4:
                equal_ &= other.text == "本金兑付日"
            elif other.serial == 5:
                equal_ &= "本期应偿付本金" in other.text
        else:
            if other.serial in (2, 3, 6, 7, 8, 9, 10):
                equal_ = other.text == "兑付"
            elif other.serial == 4:
                equal_ = other.text == "本息兑付日"
            elif other.serial == 5:
                equal_ = "本期应偿付本息" in other.text
        other.answer["equal"] = equal_
        equal &= equal_
    base.answer["equal"] = equal
    return equal


async def single_file_diff(file: NewFile):
    """单文档一致性比对, 取第一个答案和其他的答案进行比对"""
    logger.info(f"start single diff for file {file.id}")
    question = await pw_db.first(
        NewQuestion.select(NewQuestion.fid, NewQuestion.answer, NewMold.data.alias("mold"))
        .join(NewMold, on=(NewQuestion.mold == NewMold.id))
        .where(NewQuestion.fid == file.id)
        .namedtuples()
    )  # 暂无多schema

    try:
        return single_text_diff(question, file)
    except Exception as e:
        raise CompareException from e
    finally:
        logger.info(f"end single diff for file {file.id}")
