from __future__ import annotations

import logging
import tempfile
from collections import defaultdict
from typing import TYPE_CHECKING, TypedDict

from pdfparser.pdftools.pdf_annotation import AnnotColor, AnnotItem, AnnotType, PDFAnnot

from remarkable.answer.node import AnswerItem
from remarkable.common.enums import NafmiiTaskType
from remarkable.common.storage import localstorage
from remarkable.common.util import box_to_outline
from remarkable.config import get_config
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.cgs.services.comment import export_docx_comment, get_xpath_details
from remarkable.plugins.nafmii.enums import OperationType
from remarkable.predictor.mold_schema import MoldSchema

if TYPE_CHECKING:
    from remarkable.models.nafmii import FileAnswer


DEFAULT_USER = "AI"

logger = logging.getLogger(__name__)


class Box(TypedDict):
    box_top: float
    box_left: float
    box_right: float
    box_bottom: float


class BoxData(TypedDict):
    box: Box
    page: int
    text: str


class ItemData(TypedDict):
    text: str
    boxes: list[BoxData]
    handleType: str


class SchemaDataItem(TypedDict):
    label: str


class ItemSchema(TypedDict):
    data: SchemaDataItem


class UserAnswerItem(TypedDict):
    key: str
    data: list[ItemData]
    schema: ItemSchema
    texts: list[str]


class DocxAnnotation(TypedDict):
    xpath: str
    comment: str
    type: str
    start: int
    end: int


def get_comments_for_pdf(items: list[UserAnswerItem]) -> dict[int, list[AnnotItem]]:
    comment_by_page = defaultdict(list)
    for item in items:
        for item_data in item["data"]:
            for box_data in item_data["boxes"]:
                box = box_data["box"]
                comment_by_page[box_data["page"]].append(
                    AnnotItem(
                        [[box["box_left"], box["box_top"], box["box_right"], box["box_bottom"]]],
                        AnnotColor.BISQUE.value,
                        AnnotType.FPDF_ANNOT_HIGHLIGHT,
                        texts=item["texts"],
                        fontsize=20,
                    )
                )
    return comment_by_page


def get_comments_for_docx(reader: PdfinsightReader, items: list[UserAnswerItem]) -> list[DocxAnnotation]:
    from remarkable.plugins.cgs.common.utils import get_xpath_by_outlines

    annotation_json = []

    for item in items:
        outlines = defaultdict(list)
        answer_item = AnswerItem(**item)
        for item_data in item["data"]:
            for box_data in item_data["boxes"]:
                outlines[box_data["page"]].append(box_to_outline(box_data["box"]))
        xpath = get_xpath_by_outlines(reader, outlines)
        xpath, start, end = get_xpath_details(reader, xpath, outlines, answer_item.plain_text)
        if xpath:
            annotation_json.append(
                {
                    "xpath": xpath,
                    "comment": "".join(item["texts"]),
                    "type": "error",
                    "start": start,
                    "end": end,
                }
            )
    return annotation_json


def get_comment_content(
    task_types: list, mold_schema: MoldSchema, items: list[UserAnswerItem], file_answer: FileAnswer
):
    contents = []
    if NafmiiTaskType.T001 in task_types:
        for item in items:
            schema = mold_schema.find_schema_by_path(item["key"])
            if len(schema.path) == 2:
                label = schema.name
            else:
                label = f"{schema.parent.name}-{schema.name}"
            item["texts"] = [label]
            contents.append(item)

    if NafmiiTaskType.T002 in task_types:
        for word in file_answer.keyword:
            for item in word["items"]:
                if item["operation"] != OperationType.add:
                    continue
                item["texts"] = ["关键字"]
                contents.append(item)

    if NafmiiTaskType.T003 in task_types:
        for word in file_answer.sensitive_word:
            for item in word["items"]:
                if item["operation"] != OperationType.add:
                    continue
                item["texts"] = [f"敏感词:{word['key']}"]
                contents.append(item)
    return contents


def export_annotation_to_file(
    task_types: list, file: NewFile, mold_schema: MoldSchema, items: list[UserAnswerItem], file_answer: FileAnswer
) -> bytes:
    comment_contents = get_comment_content(task_types, mold_schema, items, file_answer)

    suffix = ".docx" if file.is_docx else ".pdf"
    with tempfile.NamedTemporaryFile(
        suffix=suffix,
        dir=get_config("web.tmp_dir"),
    ) as temp_file:
        temp_path = temp_file.name

        if file.is_docx:
            reader = PdfinsightReader(localstorage.mount(file.pdfinsight_path()))
            comments = get_comments_for_docx(reader, comment_contents)
            export_docx_comment(file, comments, temp_path)
        else:
            comments = get_comments_for_pdf(comment_contents)
            annot = PDFAnnot(localstorage.mount(file.pdf_path(abs_path=True)))
            annot.insert_batch(comments, temp_path)

        with open(temp_path, "rb") as f:
            binary_data = f.read()

        return binary_data
