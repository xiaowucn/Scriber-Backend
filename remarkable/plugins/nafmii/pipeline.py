"""
交易商协会交互的相关逻辑，包括数据转换，结果推送等等
"""

import json
import re
from _operator import attrgetter
from collections import defaultdict
from typing import Iterable

from pydantic import BaseModel, Field, Json, computed_field, field_validator

from remarkable.answer.node import AnswerItem
from remarkable.common.enums import NafmiiTaskType as TaskType
from remarkable.db import pw_db
from remarkable.models.nafmii import FileAnswer, NafmiiFileInfo
from remarkable.models.new_file import NewFile
from remarkable.plugins.nafmii import diff
from remarkable.plugins.nafmii.diff import logger
from remarkable.pw_models.model import NewMold
from remarkable.pw_models.question import NewQuestion
from remarkable.service.new_question import NewQuestionService

P_NUMBER_TAIL = re.compile(r"\d+$")

KEEP_PARENT_FIELDS = {
    "付息兑付安排公告": [
        "发行金额",
        "债项余额",
        "本期应偿付金额",
    ],
    "行权公告": [
        "发行金额",
        "债项余额",
        "发行人赎回债券金额",
        "本期利息支付总额",
        "本期利息递延支付金额",
        "下一支付日应付利息总额",
    ],
    "行权结果公告": [
        "发行金额",
        "债项余额",
        "本次回售金额",
        "未回售金额",
    ],
}


class _DiffItem(BaseModel):
    key: str
    texts: list[str] = Field(default_factory=list, exclude=True)

    @computed_field
    def value(self) -> str:
        if self.key.startswith("行权类别"):
            return ",".join(self.texts)
        else:
            return "".join(self.texts)

    @computed_field
    def alias(self) -> str:
        if self.key == "公告披露日期":
            return "落款日期"
        elif self.key == "发行人名称03":
            return "落款企业名称"
        elif self.key == "发行人名称04":
            return "落款红章"
        else:
            return ""

    @field_validator("key", mode="after")
    def convert_key(cls, value: str) -> str:
        return json.loads(value)[-1].split(":")[0]


class _DiffItemGroup(BaseModel):
    key: str
    equal: bool
    items: list[_DiffItem] = Field(default_factory=list)

    @computed_field
    def type(self) -> str:
        return "R001"

    @computed_field
    def value(self) -> str:
        if self.equal:
            for item in self.items:
                return item.value  # noqa
        return ""


class _Box(BaseModel):
    page: int
    text: str


class _GroupSubItem(BaseModel):
    keys: Json[list[str]] = Field(validation_alias="key", exclude=True)
    boxes: list[_Box] = Field(default_factory=list, validation_alias="data", exclude=True)
    plain_text: str = Field(exclude=True)

    @computed_field
    def key(self) -> str:
        mold_name = self.keys[0].split(":")[0]
        parent_filed = self.keys[1].split(":")[0]
        leaf_field = self.keys[-1].split(":")[0]
        if parent_filed in KEEP_PARENT_FIELDS.get(mold_name, []):
            return f"{parent_filed}-{leaf_field}"
        return leaf_field

    @computed_field
    def value(self) -> str:
        return self.plain_text

    @field_validator("boxes", mode="before")
    def convert_box(cls, value: list[dict]):
        return [box for item in value for box in item["boxes"]]


class _WordPosition(BaseModel):
    page: list[int]
    chapter: list[str]


class _WordItem(BaseModel):
    boxes: list[_Box] = Field(default_factory=list, validation_alias="data", exclude=True)
    chapters: list[str] = Field(default_factory=list, validation_alias="positions", exclude=True)

    @field_validator("boxes", mode="before")
    def convert_box(cls, value: list[dict]):
        return [box for item in value for box in item["boxes"]]

    @computed_field
    def text(self) -> str:
        return "".join(box.text for box in self.boxes)

    @computed_field
    def position(self) -> _WordPosition:
        return _WordPosition(page=[box.page for box in self.boxes], chapter=self.chapters)


class _KeywordItem(_WordItem):
    @computed_field
    def type(self) -> str:
        return "关键字"


class _SensitiveWordItem(_WordItem):
    @computed_field
    def type(self) -> str:
        return "敏感词"


class _GroupItem(BaseModel):
    """组合类型的字段"""

    key: str
    items: list[_GroupSubItem]

    @computed_field
    def type(self) -> str:
        return "R002"

    @field_validator("key", mode="after")
    def remove_suffix(cls, value):
        return value.split(":")[0]


def _group_item(items: Iterable[_GroupSubItem]):
    item_by_group = defaultdict(list)
    for item in items:
        item_by_group[item.keys[1]].append(item)

    for key, items in sorted(item_by_group.items()):
        yield {"key": key, "items": sorted(items, key=attrgetter("key"))}


async def prepare_nafmii_answer(file: NewFile):
    nafmii_answer = await pw_db.first(FileAnswer.select().where(FileAnswer.file == file))
    task_types = (
        await pw_db.scalar(NafmiiFileInfo.select(NafmiiFileInfo.task_types).where(NafmiiFileInfo.file == file)) or []
    )

    result = {"result_info": [], "check_points": [], "words_answers": []}
    if not file.file_info:
        logger.error(f"no file info for file {file.id}")
        return result
    file_info: NafmiiFileInfo = file.file_info[0]
    if TaskType.T001 in file_info.task_types:
        question = await pw_db.first(
            NewQuestion.select(NewQuestion.fid, NewQuestion.answer, NewMold.data.alias("mold"), NewMold.id.alias("mid"))
            .join(NewMold, on=(NewQuestion.mold == NewMold.id))
            .where(NewQuestion.fid == file.id)
            .namedtuples()
        )  # 暂无多schema
        mold = await NewMold.find_by_id(question.mid)
        NewQuestionService.fill_group_with_fixed_length(question.answer, mold, ignore_basic_type=False)
        answer = question.answer
        result["result_info"].extend(_DiffItemGroup.model_validate(ans).model_dump() for ans in nafmii_answer.diff)
        items = []
        for item in answer["userAnswer"]["items"]:
            answer_item = AnswerItem(**item)
            first_level_field = P_NUMBER_TAIL.sub("", answer_item.first_level_field)
            if first_level_field in diff.FIELDS:
                continue
            data = {"key": item["key"], "data": item["data"], "plain_text": answer_item.plain_text}
            items.append(_GroupSubItem.model_validate(data))
        items = _group_item(items)
        result["result_info"].extend(_GroupItem.model_validate(item).model_dump() for item in items)

    result["words_answers"].extend(
        _KeywordItem.model_validate(item).model_dump() for group in nafmii_answer.keyword for item in group["items"]
    )
    result["words_answers"].extend(
        _SensitiveWordItem.model_validate(item).model_dump()
        for group in nafmii_answer.sensitive_word
        for item in group["items"]
    )
    if TaskType.T002 in task_types:
        result["check_points"].append({"type": "关键字", "exists": bool(nafmii_answer.keyword)})
    if TaskType.T003 in task_types:
        result["check_points"].append({"type": "敏感词", "exists": bool(nafmii_answer.sensitive_word)})
    return result
