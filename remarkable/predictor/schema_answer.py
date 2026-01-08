# -*- coding: utf-8 -*-
import json
import logging
from collections import defaultdict
from copy import deepcopy
from itertools import groupby

from remarkable.common.box_util import get_bound_box
from remarkable.common.util import compact_dumps, outline_to_box
from remarkable.predictor.mold_schema import MoldSchema
from remarkable.predictor.predict import get_tbl_text, split_chars


class AnswerResult:
    def __init__(self, text=None):
        self._text = text

    def to_answer(self):
        raise NotImplementedError

    @property
    def text(self):
        return self._text or ""

    @text.setter
    def text(self, value):
        self._text = value

    @staticmethod
    def create_box(page, line_box, text):
        return {
            "page": page,
            "box": outline_to_box(line_box) if line_box else {},
            "text": text,
        }

    def __str__(self):
        return self.text


class OutlineResult(AnswerResult):
    """
    通过已知的外框生成答案
    """

    def __init__(self, page_box, text=None, element=None, origin_elements=None):
        if text is None:
            text = "\n".join(i["text"] for i in page_box)
        super().__init__(text=text)
        self.page_box = page_box
        self.element = element
        self.origin_elements = origin_elements

    def to_answer(self):
        answer = {"boxes": [], "handleType": "wireframe"}
        for index, page_data in enumerate(self.page_box):
            text = page_data.get("text")
            text = "\n" + text if (index != 0 and text and text[0] != "\n") else text
            if len(self.page_box) == 1 and self.text and text != self.text:
                # box拼接的内容可能跟实际内容不一致，这里做一次校正，以实际传入内容为准（如果有的话）
                text = self.text
            answer["boxes"].append(self.create_box(page_data["page"], page_data["outline"], text))
        return answer


class ElementResult(AnswerResult):
    def __init__(self, element, text=None):
        super().__init__(text=text)
        self.element = element

    def to_answer(self):
        raise NotImplementedError


class TextResult(ElementResult):
    def __init__(self, element, chars):
        super().__init__(element)
        self.chars = chars

    @property
    def text(self):
        return "".join(i.get("text", "") for i in self.chars)

    def to_answer(self):
        raise NotImplementedError

    def __repr__(self):
        return self.text


class NoBoxResult(TextResult):
    def __init__(self, text):
        super().__init__(element={}, chars=[])
        self._text = text

    @property
    def text(self):
        return self._text

    def to_answer(self):
        return {"boxes": [], "handleType": "wireframe"}


class CharResult(TextResult):
    def __init__(self, element, chars, display_text=None):
        super().__init__(element, chars)
        self.display_text = display_text

    @property
    def text(self):
        if self.display_text:
            return self.display_text
        return "".join(i.get("text", "") for i in self.chars)

    def to_answer(self):
        answer = {"boxes": [], "handleType": "wireframe"}
        page_chars = {}
        for char in self.chars:
            page_chars.setdefault(int(char["page"]), []).append(char)

        for page in sorted(page_chars):
            lines = split_chars(page_chars[page])
            been_using_special_text = False
            for chars in lines:
                line_box = get_bound_box([char["box"] for char in chars])  # (左，上，右，下)
                if self.display_text:
                    if not been_using_special_text:
                        comp_text = self.display_text
                        been_using_special_text = True
                    else:
                        comp_text = ""
                else:
                    comp_text = "".join([char["text"] for char in chars])
                answer["boxes"].append(self.create_box(page, line_box, comp_text))
        if not answer["boxes"] and self.display_text:
            answer["boxes"].append(self.create_box(0, [], self.display_text))

        return answer


class ParagraphResult(TextResult):
    def to_answer(self):
        answer = {"boxes": [], "handleType": "wireframe"}
        chars = defaultdict(list)
        for char in self.chars:
            # 按页分组
            chars[int(char["page"])].append(char)
        for page, chs in chars.items():
            lines = split_chars(chs)
            line_boxes = [get_bound_box(char["box"] for char in line) for line in lines]
            box_data = get_bound_box(line_boxes)
            answer["boxes"].append(self.create_box(page, box_data, text="".join(i["text"] for i in chs)))
        # if para_res.confirm:
        #     res['confirm'] = True
        return answer


class TableResult(ElementResult):
    def __init__(self, element, cells: list["ParsedTableCell"], text=None):  # noqa
        super().__init__(element, text=text)
        self.parsed_cells = cells

    @property
    def cells(self) -> list[str]:
        if not self.parsed_cells:
            return []
        return [cell.raw_cell["index"] for cell in self.parsed_cells]

    @property
    def text(self) -> str:
        answer = self.to_answer()
        return "|".join([box["text"] for box in answer.get("boxes", []) if box.get("text")])

    def to_answer(self):
        answer = {"boxes": [], "handleType": "wireframe", "elements": [self.element["index"]]}

        page = self.element["page"]
        if self.cells:
            chars = []
            for cell_id in self.cells:
                cell = self.element["cells"].get(cell_id, {})
                cell_chars = cell.get("chars", [])
                if cell_chars:
                    chars.extend(cell_chars)
                elif self.is_empty_cell(cell):
                    chars.append(cell)
                else:
                    continue
            if chars:
                page = chars[0]["page"]
            lines = split_chars(chars, interval=1000000)  # 表格内默认画一个框
        else:
            if self.element["continued"]:
                chars_group_by_page = defaultdict(list)
                for cell in self.element["cells"].values():
                    for char in cell.get("chars", []):
                        chars_group_by_page[char["page"]].append(char)
                lines = chars_group_by_page.values()
            else:
                lines = [
                    [
                        {
                            "box": self.element.get("outline"),
                            "text": get_tbl_text(self.element),
                            "page": self.element["page"],
                        }
                    ]
                ]

        if not lines:
            logging.warning("TableResult can not parse lines.")
            return answer

        for chars in lines:
            line_box = get_bound_box([char["box"] for char in chars])
            comp_text = "".join([char["text"] for char in chars])
            line_page = chars[0]["page"]
            # if comp_text and re.sub(r'\s+', '', comp_text):  # 过滤空行
            #     answer['boxes'].append(self.create_box(page, line_box, comp_text))
            answer["boxes"].append(self.create_box(line_page or page, line_box, comp_text))
        # if tbl_res.confirm:
        #     answer['confirm'] = True
        return answer

    @staticmethod
    def is_empty_cell(cell):
        cell_chars = cell.get("chars", [])
        if cell_chars:
            return False

        cell_box = cell.get("box", [])
        return cell_box and cell.get("page")


class LLMTableResult(ElementResult):
    """仅用于大模型提取的表格, 不需要内容只需要外框"""

    def to_answer(self):
        answer = {"boxes": [], "handleType": "wireframe", "elements": [self.element["index"]], "text": self.text}
        if self.element["continued"]:
            chars_group_by_page = defaultdict(list)
            for cell in self.element["cells"].values():
                for char in cell.get("chars", []):
                    chars_group_by_page[char["page"]].append(char)
            lines = chars_group_by_page.values()
        else:
            lines = [
                [
                    {
                        "box": self.element.get("outline"),
                        "text": "",
                        "page": self.element["page"],
                    }
                ]
            ]
        if not lines:
            logging.warning("TableResult can not parse lines.")
            return answer

        for chars in lines:
            line_box = get_bound_box([char["box"] for char in chars])
            answer["boxes"].append(self.create_box(chars[0]["page"] or self.element["page"], line_box, ""))
        return answer


class TableCellsResult(TableResult):
    def __init__(self, element, cells: list["ParsedTableCell"], merge_cells=False):  # noqa
        super().__init__(element, cells)
        self.merge_cells = merge_cells

    def to_answer(self):
        answer = {"boxes": [], "handleType": "wireframe"}

        table_cells = [self.element["cells"][cell_id] for cell_id in self.cells]
        table_cells = [cell for cell in table_cells if cell["chars"]]
        grouped_cells = self.group_cells_by_page(table_cells)

        for page, cells in grouped_cells.items():
            if not self.merge_cells:
                for cell in cells:
                    grouped_chars_by_page = self.group_cell_by_page(cell)
                    for _page, chars in grouped_chars_by_page.items():
                        cell_box = get_bound_box([char["box"] for char in chars])
                        answer["boxes"].append(
                            {
                                "page": _page,
                                "box": outline_to_box(cell_box),
                                "text": "".join([char["text"] for char in chars]),
                            }
                        )
            else:
                sections = self.group_col_cells(cells)

                for section in sections:
                    section_cells = section["cells"]
                    section_cells.sort(key=lambda x: x["box"][1])
                    section_box = get_bound_box([char["box"] for cell in section_cells for char in cell["chars"]])
                    section_text = " ".join(cell["text"] for cell in section_cells)
                    section_text += "  "
                    answer["boxes"].append(self.create_box(page, section_box, section_text))

        return answer

    @staticmethod
    def group_cell_by_page(cell):
        grouped_cell = defaultdict(list)
        for char in cell["chars"]:
            page = int(char["page"])
            grouped_cell[page].append(char)

        return grouped_cell

    @staticmethod
    def group_cells_by_page(cells):
        grouped_cells = defaultdict(list)
        for cell in cells:
            page = int(cell["page"])
            grouped_cells[page].append(cell)

        return grouped_cells

    @staticmethod
    def group_col_cells(cells):
        grouped_cells = defaultdict(list)
        for col, col_cells in groupby(cells, key=lambda x: x["index"].split("_")[1]):
            for cell in col_cells:
                grouped_cells[col].append(cell)

        sections = []
        for group_cells in grouped_cells.values():
            rows = [int(i["index"].split("_")[0]) for i in group_cells]
            row_start = min(rows)
            row_end = max(rows) + 1
            is_separator = False
            for row in range(row_start, row_end):
                if row not in rows:
                    is_separator = True
                    continue
                if is_separator or not sections:
                    section = {"name": f"section{len(sections)}", "cells": []}
                    sections.append(section)
                index = rows.index(row)
                sections[-1]["cells"].append(group_cells[index])
                is_separator = False

        return sections


class CellCharResult(CharResult):
    def __init__(self, element, chars, cells: list["ParsedTableCell"]):  # noqa
        super().__init__(element, chars)
        self.parsed_cells = cells

    @property
    def cells(self) -> list[str]:
        if not self.parsed_cells:
            return []
        return [cell["index"] if isinstance(cell, dict) else cell.raw_cell["index"] for cell in self.parsed_cells]


def build_element_result(element, ignore_cells=True):
    if element["class"] in ["PARAGRAPH", "PAGE_FOOTER", "PAGE_HEADER", "FOOTNOTE"]:
        return ParagraphResult(element, element["chars"])
    if element["class"] == "TABLE":
        cells = None if ignore_cells else element["cells"]
        return TableResult(element, cells)
    raise RuntimeError(f"Not supported element class: {element['class']}")


class PredictorResult:
    def __init__(
        self,
        element_results: list[ElementResult],
        value: str = None,
        text: str = None,
        primary_key: list[str] = None,
        schema: MoldSchema = None,
        score: int = None,
        meta: dict = None,
    ):
        self.element_results = element_results
        self.answer_value = value
        self.primary_key = primary_key
        self.schema = schema
        self._text = text
        self.score = score
        self.group_indexes = []
        self.meta = meta

    @property
    def key_path(self):
        return self.schema.path

    @property
    def text(self):
        return self._text or "\n".join(i.text for i in self.element_results)

    @text.setter
    def text(self, value):
        self._text = value

    @property
    def key_path_str(self):
        return json.dumps(self.key_path, ensure_ascii=False)

    @property
    def relative_elements(self):
        return [res.element for res in self.element_results]

    @property
    def answer(self):
        return self.build_answer_data()

    def push_group_index(self, idx):
        self.group_indexes.append(idx)

    def build_answer_path_key(self):
        """
        schema path:    0 1 2 3
        group index: -1 0 1 2
        注：group index 的第一个实际是 root 的所属分组，并且最后一个叶子节点尚未添加，所以是错位的
        """
        if len(self.key_path) != len(self.group_indexes):
            raise ValueError("length of indexes is not match with schema path")
        path_with_index = [f"{name}:{idx}" for name, idx in zip(self.schema.path, self.group_indexes[1:] + [0])]
        return json.dumps(path_with_index, ensure_ascii=False)

    def build_answer_data(self):
        return {
            "key": self.build_answer_path_key(),
            "schema": self.schema.to_answer_data(),
            "score": self.confidence_score(),
            "data": [i.to_answer() for i in self.element_results],
            "value": self.answer_value,
            "meta": self.meta,
            "md5": compact_dumps(self.schema.uuid_path),
        }

    def confidence_score(self):
        score = self.score
        if score is None:
            element_result = next((i for i in self.element_results), None)
            element = getattr(element_result, "element", None) or {}
            score = element.get("score", -1)
        return "%.4f" % float(score)

    def update_answer_value(self, value):
        self.answer_value = value

    def merge(self, other):
        self.element_results.extend(other.element_results)
        if self.answer_value and other.answer_value:
            answer = []
            if isinstance(self.answer_value, str):
                answer.append(self.answer_value)
            elif isinstance(self.answer_value, list):
                answer.extend(self.answer_value)
            if isinstance(other.answer_value, str):
                answer.append(other.answer_value)
            elif isinstance(other.answer_value, list):
                answer.extend(other.answer_value)
            self.answer_value = list(set(answer))
        else:
            self.answer_value = self.answer_value or other.answer_value

    def clone(self):
        return PredictorResult(
            self.element_results, value=self.answer_value, primary_key=self.primary_key, schema=self.schema
        )

    def __str__(self):
        return self.text or ""


class PredictorResultGroup(PredictorResult):
    """封装 predictor.predict_groups() 输出的多组答案，作为父级节点的一个答案，以参与父级的分组
    NOTE:
    - 子节点 sub_predictor.predict_groups() 输出的是 {"sub_primary_key_str": sub_group, ...}
    - 父节点 predictor.predict_answer_from_models() 会将其封装为 [{"parent_column": [PredictorResultGroup([sub_group])]}, ...]
    - 父节点 通过 primary_model 和 guess_primary_key 为每一组添加父级 primary key，并进行父级分组
    - 最终输出时，revise_group_answer 会把同组同path的答案合并，变为
        {"primary_key_str": [PredictorResultGroup([sub_group1, sub_group2, ...]), PredictorResult(其他字段), ...]}
    - 注：group 结构为 List[PredictorResult]
    """

    def __init__(
        self,
        groups: list[list[PredictorResult]],
        primary_key: list[str] = None,
        schema: MoldSchema = None,
        element_results: list[ElementResult] = None,
    ):
        PredictorResult.__init__(
            self,
            element_results=element_results or [],
            text=self.gen_group_text(groups),
            primary_key=primary_key,
            schema=schema,
        )
        self.groups = groups

    @classmethod
    def gen_group_text(cls, groups):
        return "|".join([item.text or "" for group in groups for item in group])

    @property
    def relative_elements(self):
        return [ele for group in self.groups for item in group for ele in item.relative_elements]

    def push_group_index(self, idx):
        PredictorResult.push_group_index(self, idx)
        for group in self.groups:
            for item in group:
                item.push_group_index(idx)

    def build_answer_data(self):
        # NOTE: non-leaf node won't have an answer item in final output
        return None

    def update_answer_value(self, value):
        raise TypeError("unsupported this method")

    def merge(self, other: "PredictorResultGroup"):
        if not isinstance(other, PredictorResultGroup):
            raise ValueError("can't merge PredictorResultGroup with %s" % type(other).__name__)
        self.groups.extend(other.groups)

    def clone(self):
        return deepcopy(self)


class CmfChinaOutlineResult(OutlineResult):
    def to_answer(self):
        answer = super().to_answer()
        answer.update({"text": self.text})
        return answer


class CmfExcelResult(AnswerResult):
    def __init__(self, cell, sheet_name, text=None):
        super().__init__(text=text)
        self.cell = cell
        self.sheet_name = sheet_name

    def to_answer(self):
        answer = {"cell": self.cell, "sheet_name": self.sheet_name, "text": self._text}
        return answer
