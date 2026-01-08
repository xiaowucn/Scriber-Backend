"""
TODO: 将答案按照schema分开存储, 以方便后续获取部分数据
"""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Iterable, Literal, Protocol, Sequence, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from remarkable.answer.common import parse_path
from remarkable.answer.node import AnswerNode
from remarkable.common.constants import (
    AIStatus,
    ChinaAMCChapterDiffStatus,
    ChinaAmcCompareStatus,
    ChinaAmcFileStatus,
    ChinaAmcProjectStatus,
    PDFParseStatus,
)
from remarkable.common.diff import calliper_diff, fake_interdocs
from remarkable.common.util import clean_txt
from remarkable.converter import make_answer_node
from remarkable.db import pw_db
from remarkable.models.chinaamc_yx import CompareTask, FileAnswer, ProjectInfo
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import ADMIN
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.cgs.common.para_similarity import R_PUNCTUATION, ParagraphSimilarity
from remarkable.plugins.chinaamc_yx.schemas import I_SELF_CONFIG
from remarkable.pw_models.model import MoldWithFK, NewFileProject, NewMold
from remarkable.pw_models.question import NewQuestion, QuestionWithFK
from remarkable.service.compare import (
    P_SERIAL,
    AnswerGroup,
    CompareException,
    group_answer_by_label,
)
from remarkable.service.new_file_project import NewFileProjectService

logger = logging.getLogger(__name__)

P_EMPTY_DIFF = re.compile(r"<[su]>[\r\n]+</[su]>")
P_JUNK_DIFF = re.compile(rf"<[su]>([{R_PUNCTUATION}]+)[\r\n]</[su]>")
P_NO_CONTENT = re.compile("本页无(?:正文|内容)")


class ChinaamcProjectService(NewFileProjectService):
    @classmethod
    async def create(
        cls,
        name: str,
        default_molds=None,
        uid: int = ADMIN.id,
        rtree_id: int = 0,
        source: int = 0,
        dept_ids: list[str] = (),
        **kwargs,
    ) -> NewFileProject:
        project = await super().create(name, default_molds, uid, rtree_id, **kwargs)
        await pw_db.create(ProjectInfo, pid=project.id, source=source, dept_ids=dept_ids)
        return project


class MinimalFile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    pdf_parse_status: int
    ai_statuses: list[int] = Field(default_factory=list)
    compare_status: int = 0  # 只有显示单文件的状态时需要

    @cached_property
    def status(self) -> ChinaAmcFileStatus:
        if self.pdf_parse_status == PDFParseStatus.FAIL:
            return ChinaAmcFileStatus.PDF_FAILED
        if self.pdf_parse_status != PDFParseStatus.COMPLETE:
            return ChinaAmcFileStatus.PDF_PARSING
        if AIStatus.DISABLE in self.ai_statuses:
            return ChinaAmcFileStatus.AI_DISABLE
        if AIStatus.FAILED in self.ai_statuses:
            return ChinaAmcFileStatus.AI_FAILED
        if AIStatus.TODO in self.ai_statuses:
            return ChinaAmcFileStatus.AI_TODO
        if AIStatus.DOING in self.ai_statuses:
            return ChinaAmcFileStatus.AI_DOING
        if self.compare_status == ChinaAmcCompareStatus.FAILED:
            return ChinaAmcFileStatus.CMP_FAILED
        if self.compare_status == ChinaAmcCompareStatus.DOING:
            return ChinaAmcFileStatus.CMP_DOING
        if self.compare_status == ChinaAmcCompareStatus.DONE:
            return ChinaAmcFileStatus.CMP_FINISH
        return ChinaAmcFileStatus.AI_FINISH

    def with_ai_statuses(self, statuses: list[int]) -> "MinimalFile":
        self.ai_statuses = statuses
        return self


class MinimalTask(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started: bool
    status: int


@dataclass
class TaskStatusCalculator:
    task: MinimalTask
    files: list[MinimalFile] = field(default_factory=list)

    @cached_property
    def status(self):
        if self.task.status:
            return self.task.status
        if not (is_file_ready(self.files) and self.task.started):
            return ChinaAmcProjectStatus.TO_BE_UPLOADED

        if any(file.pdf_parse_status == PDFParseStatus.FAIL for file in self.files):
            return ChinaAmcProjectStatus.PARSE_FAILED
        if any(file.pdf_parse_status != PDFParseStatus.COMPLETE for file in self.files):
            return ChinaAmcProjectStatus.PARSING

        ai_status = {ai_status for file in self.files for ai_status in file.ai_statuses}
        if not ai_status:
            return ChinaAmcProjectStatus.PARSED

        # 文件都已解析完成,需进一步根据AI预测状态判断
        if AIStatus.DISABLE in ai_status:
            return ChinaAmcProjectStatus.AI_DISABLE
        if AIStatus.FAILED in ai_status:
            return ChinaAmcProjectStatus.AI_FAILED
        if {AIStatus.TODO, AIStatus.DOING}.intersection(ai_status):
            return ChinaAmcProjectStatus.AI_DOING
        return ChinaAmcProjectStatus.DIFF_DOING

    @property
    def retryable(self) -> bool:
        return self.status in (
            ChinaAmcProjectStatus.PARSE_FAILED,
            ChinaAmcProjectStatus.AI_FAILED,
            ChinaAmcProjectStatus.AI_DISABLE,
            ChinaAmcProjectStatus.DIFF_DONE,
            ChinaAmcProjectStatus.DIFF_FAILED,
        )

    @cached_property
    def status_by_fid(self) -> dict[int, int]:
        return {file.id: file.status for file in self.files}


@runtime_checkable
class FileLike(Protocol):
    id: int
    source: str


def is_file_ready(files: Sequence[FileLike]):
    """所有必传的文档都准备好，才进行比对"""

    exist_file_types = {file.source for file in files}
    return exist_file_types.issuperset(I_SELF_CONFIG.required_types)


async def is_ready_to_diff(files: Sequence[FileLike]):
    """所有文档都是预测成功且必传的文档都上传了，才进行一致性比对"""
    file_ids = [f.id for f in files]
    return not await pw_db.exists(
        NewQuestion.select(NewQuestion.ai_status).where(
            NewQuestion.fid.in_(file_ids), NewQuestion.ai_status != AIStatus.FINISH
        )
    )


async def compare_task_diff(task: CompareTask, files: Sequence[NewFile] = ()):
    files = files or await pw_db.execute(NewFile.select().where(NewFile.id.in_(task.fids)))
    if not is_file_ready(files):
        logger.info(f"task {task.id} required file missing")
        return
    if not await is_ready_to_diff(files):
        logger.info(f"task {task.id} is not ready to diff")
        return
    await pw_db.update(task, status=ChinaAmcProjectStatus.DIFF_DOING.value)
    async with pw_db.atomic():
        try:
            for file in files:
                # if file.id != 2361:
                #     continue
                await single_file_diff(task, file)
            await consistency_diff(task, files)
            await chapter_diff(task)  # 章节比对失败不影响比对任务的状态
            await pw_db.update(task, status=ChinaAmcProjectStatus.DIFF_DONE.value, started=False)
        except CompareException:
            await pw_db.update(task, status=ChinaAmcProjectStatus.DIFF_FAILED.value, started=False)


def merge_answer_by_label(base: AnswerGroup, *others: AnswerGroup) -> AnswerGroup:
    for other in others:
        for key in base:
            base[key].extend(other[key])
    return base


NO_CHAPTER_MOLD = ~NewMold.name.contains("章节")


def get_serial(text: str) -> int:
    if matched := P_SERIAL.search(text):
        return int(matched.group())
    return 0


def sort_diff_answer(answer: dict) -> tuple[int, int]:
    if not answer["data"]:
        return 0, get_serial(answer["schema"]["data"]["label"])
    if any(not diff["equal"] for diff in answer["diffs"]):
        return 1, get_serial(answer["schema"]["data"]["label"])
    return 2, get_serial(answer["schema"]["data"]["label"])


def merge_answer(ans: dict):
    if not ans["data"]:
        return
    ans_by_page = defaultdict(list)
    if "001基金名称" in ans["key"] and "承诺函" in ans["key"]:
        for item in ans["data"]:
            ans_by_page[item["boxes"][0]["page"]].append(item)

        ans["data"] = []
        for items in ans_by_page.values():
            head, *follows = items
            for follow in follows:
                head["boxes"].extend(follow["boxes"])
            ans["data"].append(head)
    else:
        head, *follows = ans["data"]
        ans["data"] = []
        for follow in follows:
            head["boxes"].extend(follow["boxes"])
        ans["data"].append(head)


def filter_invisible_answer(answer_groups: AnswerGroup):
    """
    当039基金名称存在时，
      039-050字段参与比对，比对页面显示比对结果，计算差异点，前端渲染比对结果

      051基金名称存在
        则051-064字段参与比对，比对页面显示比对结果，计算差异点，前端渲染比对结果
      051基金名称不存在
        则051-064字段不参与比对，前端页面不渲染提取为空的状态

    当039基金名称不存在时，则039-064字段不参与比对，前端页面不渲染提取为空的状态
    """
    exists_039 = exists_051 = False
    for key, answers in answer_groups.items():
        if key != "基金名称":
            continue
        for answer in answers:
            if "039基金名称" in answer["key"] and answer["data"]:
                exists_039 = True
            if "051基金名称" in answer["key"] and answer["data"]:
                exists_051 = True
    if exists_039 and exists_051:
        return

    # 标记要删除的答案
    answer_by_serial = {}
    for answers in answer_groups.values():
        for answer in answers:
            serial = get_serial(answer["schema"]["data"]["label"])
            answer_by_serial[serial] = answer
    if not exists_039:
        for serial, answer in answer_by_serial.items():
            if 39 <= serial <= 64:
                answer["to_del"] = True
    elif not exists_051:
        for serial, answer in answer_by_serial.items():
            if 51 <= serial <= 64:
                answer["to_del"] = True

    for key, answers in answer_groups.items():
        answer_groups[key] = [answer for answer in answers if not answer.get("to_del")]


def single_question_diff(question, file: NewFile):
    answer_groups = group_answer_by_label(question)
    if file.source == "招募说明书":
        filter_invisible_answer(answer_groups)
    answer_items = []
    reader = PdfinsightReader(file.pdfinsight_path(abs_path=True))
    for key, (base, *others) in answer_groups.items():
        for ans in (base, *others):
            merge_answer(ans)
        equal = len(others) > 0  # 字段只有一个提取答案时按照不一致处理

        # if key != "认购费率":
        #     continue

        interdoc_l = create_simple_interdoc_from_answer(reader, base["data"][:1])
        base["positions"] = interdoc_l["positions"]
        base["diffs"] = []
        for item in base["data"]:
            interdoc_r = create_simple_interdoc_from_answer(reader, [item])
            equal_, html_diff_content = simple_interdoc_diff(interdoc_l, interdoc_r)
            base["diffs"].append({"html_diff_content": html_diff_content, "equal": equal_})
        for other in others:
            if not other["data"]:
                equal = False
                continue

            other["diffs"] = []

            for item in other["data"]:
                interdoc_r = create_simple_interdoc_from_answer(reader, [item])
                other.setdefault("positions", interdoc_r["positions"])
                equal_, html_diff_content = simple_interdoc_diff(interdoc_l, interdoc_r)
                other["diffs"].append({"html_diff_content": html_diff_content, "equal": equal_})
                equal &= equal_
        answer_items.append({"key": key, "equal": equal, "items": [base, *sorted(others, key=sort_diff_answer)]})
    return answer_groups, answer_items


def create_simple_interdoc_from_answer(reader: PdfinsightReader, items: list[dict]) -> dict:
    interdoc = reader.create_interdoc_from_answer(items)
    last_page = int(max(reader.data["pages"], key=int))
    sign_page = None
    for para in reversed(reader.paragraphs):
        if para["page"] < last_page:
            break
        if P_NO_CONTENT.search(clean_txt(para["text"])):
            sign_page = last_page
            break
    elements = interdoc["orig_elements"]
    interdoc["positions"] = positions = []
    if any(element["page"] == 0 for element in elements):
        positions.append("封面")
    elif sign_page is not None and any(element["page"] == sign_page for element in elements):
        positions.append("落款页")
    elif any(element.get("class") == "PAGE_HEADER" for element in elements):
        positions.append("页眉")
    else:
        for element in elements[:1]:
            syllabuses = reader.find_syllabuses_by_index(element["index"])
            positions.extend(syl["title"] for syl in syllabuses)
    return interdoc


def merge_calliper_diff(diffs: list[dict]) -> str:
    texts = []
    for diff in diffs:
        if diff["type"] == "para_insert":
            texts.append(f"<u>{''.join(ele.element['text'] for ele in diff['item'].right_eles)}</u>")
        elif diff["type"] == "para_delete":
            texts.append(f"<s>{''.join(ele.element['text'] for ele in diff['item'].left_eles)}</s>")
        elif diff["type"] == "equal":
            texts.append("".join(ele.element["text"] for ele in diff["item"].right_eles))
        else:
            left_text = "\n".join(ele.element["text"] for ele in diff["item"].left_eles)
            right_text = "\n".join(ele.element["text"] for ele in diff["item"].right_eles)
            _, diff_text = simple_text_diff(left_text, right_text)
            diff_text = P_EMPTY_DIFF.sub("\n", diff_text)
            diff_text = P_JUNK_DIFF.sub(r"\1\n", diff_text)

            texts.append(diff_text)
    return "\n".join(texts)


async def consistency_diff(task: CompareTask, files: Sequence[NewFile]):
    """多文档一致性比对"""
    logger.info(f"start consistency diff for task {task.id}")

    await pw_db.update(task, consistency_status=ChinaAmcCompareStatus.DOING.value)
    try:
        questions = await pw_db.execute(
            NewQuestion.select(NewQuestion.fid, NewQuestion.answer, NewMold.data.alias("mold"))
            .join(NewMold, on=(NewQuestion.mold == NewMold.id))
            .where(NewQuestion.fid.in_([file.id for file in files]), NO_CHAPTER_MOLD)
            .namedtuples()
        )
        file_by_id: dict[int, NewFile] = {file.id: file for file in files}
        answer_by_source = {file_by_id[question.fid].source: group_answer_by_label(question) for question in questions}

        if answer_groups := answer_by_source.get("招募说明书"):
            filter_invisible_answer(answer_groups)

        merged_answer = merge_answer_by_label(answer_by_source.pop("基金合同"), *answer_by_source.values())
        diff_answer = []
        reader_by_fid = {file.id: PdfinsightReader(file.pdfinsight_path(abs_path=True)) for file in files}
        for key, (base, *others) in merged_answer.items():
            # if key != "管理人":
            #     continue
            for ans in (base, *others):
                merge_answer(ans)
            equal = len(others) > 0  # 字段只有一个提取答案时按照不一致处理
            base["diffs"] = [
                {
                    "html_diff_content": "".join(box["text"] for data in base["data"] for box in data["boxes"]),
                    "equal": True,
                }
            ]

            interdoc_l = create_simple_interdoc_from_answer(reader_by_fid[base["fid"]], base["data"][:1])
            base["positions"] = interdoc_l["positions"]
            # 标准答案有多组的时候, 都要和第一组比一下
            base["diffs"] = []
            for item in base["data"]:
                interdoc_r = create_simple_interdoc_from_answer(reader_by_fid[base["fid"]], [item])
                equal_, html_diff_content = simple_interdoc_diff(interdoc_l, interdoc_r)
                base["diffs"].append({"html_diff_content": html_diff_content, "equal": equal_})

            for other in others:
                if not other["data"]:
                    equal = False
                    continue

                other["diffs"] = []
                for item in other["data"]:
                    interdoc_r = create_simple_interdoc_from_answer(reader_by_fid[other["fid"]], [item])
                    other.setdefault("positions", interdoc_r["positions"])
                    equal_, html_diff_content = simple_interdoc_diff(interdoc_l, interdoc_r)
                    equal &= equal_

                    other["diffs"].append({"html_diff_content": html_diff_content, "equal": equal_})
                # 按照比对是否一致对答案排序
                sorted_records = sorted(enumerate(zip(other["data"], other["diffs"])), key=lambda x: x[1][-1]["equal"])
                other["diffs"] = [record[1][1] for record in sorted_records]
                other["data"] = [record[1][0] for record in sorted_records]

            diff_answer.append({"key": key, "equal": equal, "items": [base, *sorted(others, key=sort_diff_answer)]})
        await pw_db.update(task, consistency_status=ChinaAmcCompareStatus.DONE.value, consistency_answer=diff_answer)
    except Exception as e:
        logger.exception(e)
        await pw_db.update(task, consistency_status=ChinaAmcCompareStatus.FAILED.value)
        raise CompareException from e
    finally:
        logger.info(f"end consistency diff for task {task.id}")


def simple_text_diff(base: str, other: str) -> tuple[bool, str]:
    diff = ParagraphSimilarity.compare_two_text(base, other)
    equal_ = diff.ratio == 1.0
    html_diff_content = diff.html_diff_content
    return equal_, html_diff_content


def simple_interdoc_diff(interdoc_l, interdoc_r):
    base_text = "".join(para["text"] for para in interdoc_l["paragraphs"])
    other_text = "".join(para["text"] for para in interdoc_r["paragraphs"])
    try:
        diffs = calliper_diff(
            interdoc_l,
            interdoc_r,
            del_keys=(),
            param={
                "kaiti_bold": False,  # 是否包含楷体加粗差异
                "ignore_case": True,  # 是否忽略大小写
                "ignore_punctuations": True,  # 是否忽略标点差异
                "ignore_chapt_numbers": True,  # 是否忽略章节号差异
                "char_ignore_rule": "all",
                "detailed_diff_log": False,
                "debug_data_path": None,
                "fontname": "",
                "fontstyle": "",
                "cfg_include_equal": True,
                "include_equal": True,
                "iter_count": 1,
            },
        )

        if not diffs:
            raise ValueError("calliper diff can not find any diff, fallback to paragraph diff")
        equal_ = all(diff["type"] == "equal" for diff in diffs)
        html_diff_content = merge_calliper_diff(diffs)
    except ValueError:
        equal_, html_diff_content = simple_text_diff(base_text, other_text)
    except Exception as e:
        logger.exception(e)
        equal_, html_diff_content = simple_text_diff(base_text, other_text)
    html_diff_content = P_EMPTY_DIFF.sub("<s>\n</s>", html_diff_content)
    return equal_, html_diff_content


async def single_file_diff(task: CompareTask, file: NewFile):
    """单文档一致性比对, 取第一个答案和其他的答案进行比对"""
    logger.info(f"start single diff for task {task.id}, file {file.id}")
    question = await pw_db.first(
        NewQuestion.select(NewQuestion.fid, NewQuestion.answer, NewMold.data.alias("mold"))
        .join(NewMold, on=(NewQuestion.mold == NewMold.id))
        .where(NewQuestion.fid == file.id, NO_CHAPTER_MOLD)
        .namedtuples()
    )  # 暂无多schema
    await pw_db.execute(FileAnswer.delete().where(FileAnswer.task == task, FileAnswer.file == file))

    try:
        answer_groups, answer_items = single_question_diff(question, file)
        await pw_db.create(
            FileAnswer,
            task_id=task.id,
            fid=file.id,
            status=ChinaAmcCompareStatus.DONE.value,
            schema=list(answer_groups),
            answer=answer_items,
        )
    except Exception as e:
        logger.exception(e)
        await pw_db.create(FileAnswer, task_id=task.id, fid=file.id, status=ChinaAmcCompareStatus.FAILED.value)
        raise CompareException from e
    finally:
        logger.info(f"end single diff for task {task.id}, file {file.id}")


class ChapterMeta(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    answer_node: AnswerNode
    file: NewFile
    elements: dict[str, dict] = Field(default_factory=dict)
    answers: dict[str, dict] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        inter_doc = PdfinsightReader(self.file.pdfinsight_path(abs_path=True))
        self.answers = dict(self._items_iter())
        # 保存预测答案的元素块，用于比对
        self.elements = fake_interdocs(
            (data for _, data in self._items_iter()),
            inter_doc,
            need_table=True,
            key_dumps_func=self._conv_key,
        )

    @staticmethod
    def _conv_key(key: str):
        # '["基金合同V1:0","001基金名称:0"]' -> "001基金名称"
        return parse_path(key)[-1][0]

    def _items_iter(self) -> Iterable[tuple[str, dict]]:
        for (key, _), item in self.answer_node.items():
            if key in I_SELF_CONFIG.check_points_molds.get(self.answer_node.name, []):
                # 只取审核点涉及的答案
                yield key, item.data


class DiffItem(BaseModel):
    _essential_keys = {
        "id",
        "left_box",
        "right_box",
        "left_outline",
        "right_outline",
    }
    name: str
    left: dict | None
    right: dict | None
    diffs: list[dict]
    type: Literal["一致", "不一致", "不适用"] = Field(default="不一致")

    def model_post_init(self, __context: Any) -> None:
        for item in self.diffs:
            # 只保留关键信息，精简入库数据
            for key in item.copy():
                if key not in self._essential_keys:
                    item.pop(key)

        if not self.left or not self.right:
            self.type = "不适用"
            return
        if self.left and self.right and not self.diffs:
            self.type = "一致"
            return


class DiffResult(BaseModel):
    fund_contract: list[DiffItem] = Field(default_factory=list)
    custody_agreement: list[DiffItem] = Field(default_factory=list)

    @classmethod
    def conv_answer(cls, data: dict[str, list[DiffItem]]) -> dict[str, list[dict]]:
        diff_result = cls()
        for check_point in I_SELF_CONFIG.check_points:
            # 一般情况比对结果只有一个，但是有可能有多个
            diffs = data.get(check_point.name)
            if check_point.right_mold == "标注章节对比 基金合同V1":
                # 基金合同先进先出
                diff_result.fund_contract.append(diffs.pop(0))
            elif check_point.right_mold == "标注章节比对 托管协议V1":
                diff_result.custody_agreement.append(diffs.pop())
        return diff_result.model_dump()


async def chapter_diff(task: CompareTask):
    """章节比对"""
    logger.info(f"start chapter diff task: {task.id}")
    status = ChinaAMCChapterDiffStatus.DOING
    await pw_db.update(task, chapter_status=status)

    files = await pw_db.prefetch(
        NewFile.select().where(NewFile.id.in_(task.fids)),
        QuestionWithFK.select(),
        MoldWithFK.select(),
    )

    try:
        status = ChinaAMCChapterDiffStatus.DONE
        answers: dict[str, ChapterMeta] = {}
        for file in files:
            if len(answers) == len(I_SELF_CONFIG.check_points_molds):
                break
            for question in file.questions:
                if question.mold.name not in I_SELF_CONFIG.check_points_molds:
                    continue
                answer_node = make_answer_node(question.preset_answer)
                answers[question.mold.name] = (
                    ChapterMeta(answer_node=answer_node, file=file) if answer_node is not None else None
                )

        diffs = {}
        for check_point in I_SELF_CONFIG.check_points:
            if check_point.left_mold not in answers or check_point.right_mold not in answers:
                # 有一个文档没有预测结果，直接标记为失败比对
                logger.error(
                    f"empty answer detected, molds: {'; '.join(k for k in (check_point.left_mold, check_point.right_mold) if k not in answers)}"
                )
                status = ChinaAMCChapterDiffStatus.FAILED
                break

            if left_chapter := answers[check_point.left_mold]:
                left = left_chapter.elements.get(check_point.left_key)
                left_answer = left_chapter.answers.get(check_point.left_key)
            else:
                left = left_answer = None
            if right_chapter := answers[check_point.right_mold]:
                right = right_chapter.elements.get(check_point.right_key)
                right_answer = right_chapter.answers.get(check_point.right_key)
            else:
                right = right_answer = None
            diffs.setdefault(check_point.name, []).append(
                DiffItem(
                    name=check_point.name,
                    left=left_answer,
                    right=right_answer,
                    diffs=calliper_diff(left, right) if left and right else [],
                )
            )

        if status != ChinaAMCChapterDiffStatus.FAILED:
            status = ChinaAMCChapterDiffStatus.DONE
            await pw_db.update(task, chapter_answer=DiffResult.conv_answer(diffs))

    except Exception as e:
        status = ChinaAMCChapterDiffStatus.FAILED
        logger.exception(e)
    finally:
        await pw_db.update(task, chapter_status=status)
        logger.info(f"end chapter diff task: {task.id}")
