import copy
import logging
import os
import re
from collections import Counter, OrderedDict, defaultdict
from copy import deepcopy
from difflib import SequenceMatcher
from functools import cached_property
from itertools import groupby
from typing import Callable, Iterable, Pattern

import attr
import msgspec
from pdfparser.pdftools.interdoc import Interdoc
from pdfparser.pdftools.pdf_util import PDFUtil

from remarkable.common.box_util import get_bound_box
from remarkable.common.exceptions import PDFInsightNotFound
from remarkable.common.pattern import RE_TYPE
from remarkable.common.rectangle import Rectangle, merge_box
from remarkable.common.util import (
    Singleton,
    clean_txt,
    fix_ele_type,
    group_cells,
    is_aim_element,
    is_consecutive,
    read_zip_first_file,
)
from remarkable.common.util import box_in_box as box_in_box_common
from remarkable.pdfinsight.itable import ITable
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.predictor.eltype import ElementClassifier, ElementType

PDFINSIGHT_CLASS_MAPPING = {
    "syllabuses": "SYLLABUS",
    "paragraphs": "PARAGRAPH",
    "tables": "TABLE",
    "page_headers": "PAGE_HEADER",
    "page_footers": "PAGE_FOOTER",
    "shapes": "SHAPE",
    "images": "IMAGE",
    "footnotes": "FOOTNOTE",
    "infographics": "INFOGRAPHIC",
    "nested_tables": "TABLE",
    "stamps": "STAMP",
}
logger = logging.getLogger(__name__)


@attr.s(slots=True)
class Index:
    idx: int = attr.ib(default=0)
    page: int = attr.ib(default=0)
    index: int = attr.ib(default=0)
    outline: list = attr.ib(default=[0.0, 0.0, 0.0, 0.0])
    data: dict | None = attr.ib(default=None)

    def __getitem__(self, index):
        logger.warning("Please do not use indexing of this object")
        return attr.astuple(self)[index]


def _pretreat(data):
    # https://mm.paodingai.com/cheftin/pl/oia5cdfogtd1ty6ncjbjycznzr
    data = Interdoc.restore_page_merged_table(data)
    for group_name, class_name in PDFINSIGHT_CLASS_MAPPING.items():
        for item in data.get(group_name, []):
            if "class" not in item:
                if isinstance(item, str):
                    # 内嵌表格，遍历出的是一个字典，其key为字符串，值为列表
                    # {'1-5_2':[{'class': 'TABLE', 'index': None, 'page': 0, ...}]}
                    # 1-5_2: 表格index为1, 5_2为cell的index
                    for nest_table in data.get(group_name).get(item):
                        nest_table["class"] = class_name
                else:
                    item["class"] = class_name
    nested_tables = defaultdict(list)
    contain_index_nested_tables = deepcopy(data.get("nested_tables", {}))
    # 按照 table index 分组
    for k, v in contain_index_nested_tables.items():
        parent_idx = int(k.split("-", maxsplit=1)[0])
        nested_tables[parent_idx].extend(v)
    # 更新 table index,并将内嵌表格插入到tables里面
    for k, v in nested_tables.items():
        for idx, table in enumerate(v, start=1):
            table["index"] = int(k) + idx / 100
            table["is_nested"] = True
            data["tables"].append(table)
    data["contain_index_nested_tables"] = nested_tables

    items = {}
    index_keys = list(PDFINSIGHT_CLASS_MAPPING.keys())
    index_keys.remove("syllabuses")
    index_keys.remove("nested_tables")  # nested_tables已经附加到 tables中 下面无需再遍历
    for cate in index_keys:
        for idx, elt in enumerate(data.get(cate, [])):
            items[elt.get("index")] = Index(idx, elt.get("page"), elt.get("index"), elt.get("outline"), elt)
    data["_index"] = items
    return data


class Cacher(Singleton):
    def __init__(self, size=0):
        if not self._inited:
            self.size = size
            self.keys = []
            self.data = {}
            self._inited = True

    def __reinit__(
        self,
    ):
        self.keys = []
        self.data = {}

    def get(self, zip_path):
        if not os.path.isfile(zip_path):
            raise PDFInsightNotFound("file {} not exists".format(zip_path))

        if zip_path not in self.data:
            data = msgspec.json.decode(read_zip_first_file(zip_path))
            _pretreat(data)
            if self.size > 0:
                self.data[zip_path] = data
                self._push(zip_path)
        else:
            data = self.data[zip_path]
            self._push(zip_path)

        return data

    def close(self, zip_path):
        if not zip_path:
            self.__reinit__()

        if not os.path.isfile(zip_path):
            return

        if zip_path in self.keys and zip_path in self.data:
            self.keys.remove(zip_path)
            self.data.pop(zip_path, None)

    def _push(self, key):
        if key in self.keys:
            self.keys.remove(key)

        self.keys.insert(0, key)
        while len(self.keys) > self.size:
            key_ = self.keys.pop()
            self.data.pop(key_, None)


def fill_merged_cells(table):
    """
    填充被合并的单元格
    """
    cells = table["cells"]
    for merged in table.get("merged", []):
        cell = None
        for row, col in merged:
            cell = cells.get("{}_{}".format(row, col))
            if cell is not None:
                break
        if cell is not None:
            for row, col in merged:
                dummy_cell = deepcopy(cell)
                dummy_cell["dummy"] = True
                cells.setdefault("{}_{}".format(row, col), dummy_cell)
    return table


class PdfinsightReader:
    def __init__(self, path, cachesize=0, data=None, include_special_table=False):
        self.path = path
        # TODO: remove the Cacher
        self.cacher = Cacher(size=cachesize)
        self.data = self.cacher.get(path) if not data else _pretreat(data)
        self.syllabus_dict = {syl["index"]: syl for syl in self.syllabuses}
        self.syllabus_reader = PdfinsightSyllabus(self.syllabuses)
        self.element_dict = {}
        for _, elt in sorted(self.data["_index"].items(), key=lambda x: x[0]):
            self.element_dict.setdefault(elt.page, []).append(elt)

        self.table_dict = {}
        if combo_tables := self.data.get("combo_tables"):
            # use attr 'combo_tables' for merged_table
            merged_tales = self.get_all_tables(combo_tables)
        else:
            # 兼容旧数据格式
            merged_tales = self.fix_tables(include_special_table)
        for table in merged_tales:
            for item in table.tables:
                self.table_dict[item["index"]] = table

    def __getattr__(self, name):
        """
        id, name, path,
        syllabuses, paragraphs, tables,
        page_headers, page_footers
        """
        if name in self.data:
            return [self._return(elt)[1] for elt in self.data[name]]
        return []

    @cached_property
    def paragraphs(self):
        return self.__getattr__("paragraphs")

    @cached_property
    def syllabuses(self):
        return self.__getattr__("syllabuses")

    @cached_property
    def page_headers(self):
        return self.__getattr__("page_headers")

    def _return(self, elt):
        if "processed" not in elt:
            if elt.get("class") == "TABLE":
                table = self.table_dict.get(elt.get("index"))
                if table:
                    elt["cells"] = table.cells
                    if elt["index"] != table.index:
                        elt["fragment"] = True
            if elt.get("page_merged_paragraph"):
                elt = copy.deepcopy(elt)
                chars = []
                for idx in elt["page_merged_paragraph"]["paragraph_indices"]:
                    if idx in self.data["_index"]:
                        element = self.data["_index"][idx].data
                        chars.extend(element.get("chars", []))
                        if not element.get("continued"):
                            elt["merge_chars_count"] = len(element.get("chars", []))
                            elt["page_merged_paragraph"]["page"] = element["page"]
                            elt["page_merged_paragraph"]["outline"] = element["outline"]
                elt["page_merged_paragraph"]["chars"] = chars
                if elt["index"] != elt["page_merged_paragraph"]["paragraph_indices"][0]:
                    elt["fragment"] = True
                else:
                    # 覆盖跨页段落片段原信息
                    # （只保证片段的一个元素块完整，后面的 elt['fragment'] = True 且内容不完整）
                    elt["chars"] = chars
                    elt["text"] = elt["page_merged_paragraph"]["text"]
            elt["processed"] = True
        return elt.get("class"), elt

    def find_cell_idx_by_outline(self, tbl, outline, box_page):
        def inter_x(*outlines):
            overlap_length = min(outlines[0][2], outlines[1][2]) - max(outlines[0][0], outlines[1][0])
            return overlap_length if overlap_length > 0 else 0

        def inter_y(*outlines):
            overlap_length = min(outlines[0][3], outlines[1][3]) - max(outlines[0][1], outlines[1][1])
            return overlap_length if overlap_length > 0 else 0

        def area(*outlines):
            return (outlines[1][3] - outlines[1][1]) * (outlines[1][2] - outlines[1][0])

        def overlap_percent(*outlines):
            _area = area(*outlines)
            if _area == 0:
                return 0
            return inter_y(*outlines) * inter_x(*outlines) / _area

        if not tbl:
            _type, elt = self.reader.find_element_by_outline(box_page, outline)
            tbl = elt if elt is not None and _type == "TABLE" else {}

        max_overlap = None
        for cell_idx, cell in tbl.get("cells", {}).items():
            if int(cell["page"]) != int(box_page):
                continue
            if cell.get("dummy"):
                continue
            overlap = overlap_percent(outline, cell["box"])
            if overlap <= 0:
                continue
            if max_overlap is None or max_overlap[1] < overlap:
                max_overlap = (cell_idx, overlap)
        if max_overlap is not None:
            return max_overlap[0]
        return None

    def find_cell_idxes_by_outline(self, tbl, outline, box_page):
        """
        依据：覆盖率超过 overlap_threshold，且有框住 char
        """
        box_page = int(box_page)
        overlap_threshold = 0  # 有覆盖即可，还要按 char 过滤
        res = []
        for cell_idx, cell in tbl.get("cells", {}).items():
            if int(cell["page"]) != box_page:
                continue
            if cell.get("dummy"):
                continue
            cell_box = cell.get("box")
            if not cell_box:
                continue
            overlap = self.overlap_percent(cell_box, outline, base="element")
            if overlap <= overlap_threshold:
                continue
            for char in cell["chars"]:
                if char["text"] in ("\n", " "):
                    # pdfinsight 有时会添加空字符，超过单元格线
                    continue
                if self.is_box_in_box_by_center(char["box"], outline):
                    res.append(cell_idx)
                    break

        return res

    def find_element_by_outline(self, page, outline):
        def inter_x(*outlines):
            overlap_length = min(outlines[0][2], outlines[1][2]) - max(outlines[0][0], outlines[1][0])
            return overlap_length if overlap_length > 0 else 0

        def inter_y(*outlines):
            overlap_length = min(outlines[0][3], outlines[1][3]) - max(outlines[0][1], outlines[1][1])
            return overlap_length if overlap_length > 0 else 0

        def area(*outlines):
            return (outlines[1][3] - outlines[1][1]) * (outlines[1][2] - outlines[1][0])

        def overlap_percent(*outlines):
            try:
                return inter_y(*outlines) * inter_x(*outlines) / area(*outlines)
            except ZeroDivisionError:
                return 0

        max_overlap = None
        elements = self.find_elements_by_page(page)
        # logger.debug("find outline: %s", outline)
        for elt in elements:
            overlap = overlap_percent(outline, elt["outline"])
            # logger.debug("%.2f, %s", overlap, elt['outline'])
            if overlap == 0:
                continue
            if max_overlap is None or max_overlap[1] < overlap:
                max_overlap = (elt, overlap)

        if max_overlap is not None:
            return self._return(max_overlap[0])

        return None, None

    @staticmethod
    def overlap_percent(element_outline, box_outline, base="box", method="area"):
        """outline:
        (left, top, right, bottom)
        or
        {"box_bottom": bottom, "box_left": left, ...}
        """

        def inter_x(*outlines):
            overlap_length = min(outlines[0][2], outlines[1][2]) - max(outlines[0][0], outlines[1][0])
            return overlap_length if overlap_length > 0 else 0

        def inter_y(*outlines):
            overlap_length = min(outlines[0][3], outlines[1][3]) - max(outlines[0][1], outlines[1][1])
            return overlap_length if overlap_length > 0 else 0

        def area(outline):
            return (outline[3] - outline[1]) * (outline[2] - outline[0])

        def normalize_outline(outline):
            if isinstance(outline, (tuple, list)):
                return outline
            if isinstance(outline, dict):
                return (outline["box_left"], outline["box_top"], outline["box_right"], outline["box_bottom"])
            raise ValueError("not support input outline")

        if not element_outline or not box_outline:
            return 0

        element_outline = normalize_outline(element_outline)
        box_outline = normalize_outline(box_outline)

        if method == "edge":
            if base == "element":
                base_x, base_y = element_outline[2] - element_outline[0], element_outline[3] - element_outline[1]
            else:
                base_x, base_y = box_outline[2] - box_outline[0], box_outline[3] - box_outline[1]
            return (
                inter_x(element_outline, box_outline) / base_x,
                inter_y(element_outline, box_outline) / base_y if base_y else 0,
            )
        if base == "element":
            base_area = area(element_outline)
        elif base == "max":
            base_area = max(area(element_outline), area(box_outline))
        elif base == "min":
            base_area = min(area(element_outline), area(box_outline))
        else:
            base_area = area(box_outline)

        return (
            inter_y(element_outline, box_outline) * inter_x(element_outline, box_outline) / base_area
            if base_area
            else 0
        )

    @staticmethod
    def box_in_box(element_outline, box_outline):
        return box_in_box_common(element_outline, box_outline)

    def box_in_table(self, box, page):
        elements = self.find_elements_by_page(page)
        for ele in elements:
            if ele.get("class") == "TABLE":
                if self.box_in_box(box, ele["outline"]):
                    return True
        return False

    @staticmethod
    def filter_table_cross_page(elements):
        """
        过滤重复的跨页表格
        """
        return [
            e
            for e in elements
            if e.get("fragment", False) is False or e.get("page_merged_table", e["index"]) == e["index"]
        ]

    def find_elements_by_page(self, page):
        return [x.data for x in self.element_dict.get(page, [])]

    def find_elements_by_outline(self, page, outline):
        overlap_threshold = 0.618

        res = []
        max_overlap = None
        elements = self.find_elements_by_page(page)
        # logger.debug("find outline: %s", outline)
        for elt in elements:
            overlap = self.overlap_percent(outline, elt["outline"], base="min")
            # logger.debug("%.2f, %s", overlap, elt['outline'])
            if overlap == 0:
                continue

            if max_overlap is None or max_overlap[1] < overlap:
                max_overlap = (elt, overlap)

            if overlap > overlap_threshold:
                res.append(self._return(elt))

        if not res and max_overlap is not None:
            res.append(self._return(max_overlap[0]))

        # logger.info("find %s elements", len(res))

        if not res:
            logger.warning("can't find elements by outline %s, in page %s", outline, page)

        return res

    def find_chars_by_outline(self, page, outline):
        """
        outline应该只包含一个段落/单元格
        :param page:
        :param outline:
        :return:
        """
        chars = []
        may_chars = []
        etype, element = self.find_element_by_outline(page, outline)
        if not element:
            return element, chars

        if "chars" in element:
            may_chars = element["chars"]
        elif "cells" in element:
            for cell in element["cells"].values():
                if cell.get("dummy"):
                    continue
                may_chars.extend(cell["chars"])

        for char in may_chars:
            if char["page"] != page:
                continue
            if self.is_box_in_box_by_center(char["box"], outline):
                chars.append(char)

        return element, chars

    def find_chars_before_outline(self, page, outline):
        """
        outline应该只包含一个段落/单元格
        :param page:
        :param outline:
        :return:
        """
        chars = []
        may_chars = []
        etype, element = self.find_element_by_outline(page, outline)
        if not element:
            return element, chars

        if "chars" in element:
            may_chars = element["chars"]
        elif "cells" in element:
            for cell in element["cells"].values():
                if cell.get("dummy"):
                    continue
                may_chars.extend(cell["chars"])

        for char in may_chars:
            if char["page"] < page:
                chars.append(char)
            elif char["page"] == page:
                if self.is_box_before_box(char["box"], outline):
                    chars.append(char)
                else:
                    break
            else:
                break

        return element, chars

    @staticmethod
    def is_box_in_box_by_center(char_box, box2):
        if not char_box or not box2:
            return False
        h_center = (char_box[0] + char_box[2]) / 2
        v_center = (char_box[1] + char_box[3]) / 2
        return box2[2] >= h_center >= box2[0] and box2[3] >= v_center >= box2[1]

    @staticmethod
    def is_box_before_box(char_box, box2):
        if not char_box or not box2:
            return False
        h_center = (char_box[0] + char_box[2]) / 2
        v_center = (char_box[1] + char_box[3]) / 2
        return v_center < box2[1] or (v_center < box2[3] and h_center < box2[0])

    def is_ocr_page(self, page: int) -> bool:
        page_data = self.data["pages"].get(str(page))
        if page_data and page_data["statis"].get("ocr"):
            return True

        return False

    def find_chars_idx_by_outline(self, page, outline, element=None):
        chars_idx = []
        if not element:
            etype, element = self.find_element_by_outline(page, outline)
        if element:
            for idx, char in enumerate(element.get("chars", [])):
                if self.is_box_in_box_by_center(char["box"], outline):
                    chars_idx.append(idx)

        return element, chars_idx

    def find_element_by_index(self, index):
        """Unique index only works for tables and paragraphs"""
        if index in self.data["_index"]:
            return self._return(self.data["_index"][index].data)
        return None, None

    def elements_iter(self, filter_func: Callable | None = None) -> Iterable[dict]:
        for items in self.element_dict.values():
            for item in items:
                _, element = self.find_element_by_index(item.data["index"])
                if element and (not filter_func or filter_func(element)):
                    yield element

    def find_elements_near_by(
        self, index, amount=1, step=1, steprange=100, include=False, aim_types=None, neg_patterns=None
    ):
        """Unique index only works for tables and paragraphs"""
        elements = []
        cursor = index
        if include:
            etype, ele = self.find_element_by_index(cursor)
            elements.append(ele)
        while True:
            cursor += step
            etype, ele = self.find_element_by_index(cursor)
            if ele and is_aim_element(ele, aim_types, neg_patterns):
                elements.append(ele)
            if abs(cursor - index) >= steprange:
                break
            if len(elements) >= amount:
                break

        return elements

    def find_next_paragraph(self, index: int, step: int = 1, steprange: int = 5) -> dict | None:
        next_elements = self.find_elements_near_by(index=index, step=step, steprange=steprange, aim_types=["PARAGRAPH"])
        next_element = next_elements[0] if next_elements else None
        return next_element

    def find_syllabuses_by_index(self, index):
        """Unique element index"""
        return self.syllabus_reader.find_by_elt_index(index)

    def find_paragraphs_by_chapters(
        self,
        chapter_patterns: list[Pattern],
        is_continued_chapter=True,
        with_parent_chapters=False,
        candidates=None,
        valid_types=None,
    ):
        paragraphs = []
        chapters = self.find_chapter_by_patterns(
            chapter_patterns,
            reverse=False,
            is_continued_chapter=is_continued_chapter,
            candidates=candidates,
        )
        if not chapters:
            return [], []
        for chapter in chapters[-1:]:
            paragraphs.extend(self.get_elements_by_syllabus(chapter, valid_types=valid_types))
        return chapters if with_parent_chapters else chapters[-1:], paragraphs

    def get_elements_by_syllabus(self, syllabus, valid_types=None):
        elements = []
        if not valid_types:
            valid_types = ["PARAGRAPH"]
        if not syllabus:
            return elements
        for index in range(*syllabus["range"]):
            elt_type, element = self.find_element_by_index(index)
            if elt_type not in valid_types:
                continue
            if elt_type == "PARAGRAPH" and element.get("fragment"):
                continue
            elements.append(element)
        return elements

    def find_sylls_by_pattern(self, patterns, candidates=None, order="index", reverse=False, clean_func=None):
        return self.syllabus_reader.find_by_pattern(patterns, candidates, order, reverse, clean_func=clean_func)

    def find_chapter_by_patterns(
        self, patterns, candidates=None, reverse=False, clean_func=None, is_continued_chapter=True
    ):
        return self.syllabus_reader.find_syllabus_by_patterns(
            patterns, candidates, reverse, clean_func=clean_func, is_continued_chapter=is_continued_chapter
        )

    def get_parent_syllabuses(self, index):
        return self.syllabus_reader.full_syll_path(self.syllabus_dict[index])

    def find_sylls_by_clear_title(self, title, order_by="index", reverse=False, multi=False, equal_mode=True):
        return self.syllabus_reader.find_by_clear_title(
            title, order_by=order_by, reverse=reverse, multi=multi, equal_mode=equal_mode
        )

    def find_tables_by_pattern(self, patterns, start=None, end=None, multi=True):
        res = []
        for table in self.tables:
            if start is not None and table["index"] < start:
                continue
            if end is not None and table["index"] > end:
                continue
            match_all = True
            for pattern in patterns:
                match = False
                for cell in table["cells"].values():
                    if pattern.search(clean_txt(cell["text"])):
                        match = True
                        break
                if not match:
                    match_all = False
                    break
            if match_all:
                res.append(table)
            if res and not multi:
                break
        return res

    def find_paragraphs_by_pattern(self, patterns, start=None, end=None, multi=True):
        res = []
        for para in self.paragraphs:
            if start is not None and para["index"] < start:
                continue
            if end is not None and para["index"] > end:
                continue
            match_all = True
            for pattern in patterns:
                if not pattern.search(clean_txt(para["text"])):
                    match_all = False
                    continue
            if match_all:
                res.append(para)
            if res and not multi:
                break
        return res

    def fix_tables(self, include_special_table=False):
        """表格合并：
        1. 遇到连续的表格即尝试用 fix_table_column 合并
            fix_table_column：列数一致则合并
        2. 连续表格之间可以有 空段落、`续上表` 或者前一个表格由 pdfinsight 明确标记 `continued`
        """
        tables = []
        table_blocks = []
        table_ids = set()
        elements = sorted(self.data["_index"].items(), key=lambda x: x[0])
        for idx, element in elements:
            element = element.data
            if element["class"] == "PARAGRAPH":
                if re.sub(r"[-\d\s]", "", element["text"]) == "":  # 过滤页脚（页码）
                    continue
                if (
                    (not table_blocks or not table_blocks[-1].get("continued"))
                    and element["text"].strip()
                    and element["text"].find("续上表") < 0
                ):
                    if table_blocks:
                        tables.append(MergedTable(table_blocks))
                        table_blocks = []
            elif element["class"] == "TABLE":
                if element["index"] not in table_ids:
                    table_blocks.append(element)
                    table_ids.add(element["index"])
                if (
                    element.get("continued")
                    and element.get("page_merged_table")
                    and isinstance(element["page_merged_table"], dict)
                ):
                    # PDFinsight 明确记录了跨页表格信息
                    for i in element["page_merged_table"].get("cells_idx", {}):
                        if int(i) != idx and int(i) not in table_ids:
                            table_blocks.append(self.data["_index"][int(i)].data)
                            table_ids.add(int(i))
                else:
                    if len(table_blocks) > 2:
                        # 跨多页合并的 这里先把前两个区分开 后面统一使用 combo_tables 字段中的数据
                        merged_tables = table_blocks[:2]
                    else:
                        merged_tables = table_blocks[-2:]
                    if MergedTable.fix_table_column(merged_tables, include_special_table) is None:
                        if len(table_blocks) > 2:
                            tables.append(MergedTable(table_blocks[:1]))
                            table_blocks = table_blocks[1:]
                        else:
                            tables.append(MergedTable(table_blocks[:-1]))
                            table_blocks = table_blocks[-1:]
        if table_blocks:
            tables.append(MergedTable(table_blocks))
        return tables

    def get_all_tables(self, combo_tables):
        tables = []
        elements = sorted(self.data["_index"].items(), key=lambda x: x[0])
        table_elements = {idx: element.data for idx, element in elements if element.data["class"] == "TABLE"}
        table_blocks = {idx: [element] for idx, element in table_elements.items()}
        for combo_table in combo_tables:
            table_block = []
            for table_idx in combo_table["table_indices"]:
                table_block.append(table_elements[table_idx])
            merge_table = MergedTable(table_block)
            for table_idx in combo_table["table_indices"]:
                table_blocks[table_idx] = merge_table
        for table_block in table_blocks.values():
            if isinstance(table_block, MergedTable):
                tables.append(table_block)
            else:
                tables.append(MergedTable(table_block))
        return tables

    def fix_continued_para(self, elt):
        """
        拼接跨页段落
        """
        elt = deepcopy(elt)
        prev_elts = self.find_elements_near_by(elt["index"], step=-1, amount=1)
        if prev_elts and prev_elts[0] and prev_elts[0]["class"] == "PARAGRAPH" and prev_elts[0]["continued"]:
            elt["text"] = prev_elts[0]["text"] + elt["text"]
            elt["chars"] = prev_elts[0]["chars"] + elt["chars"]

        if elt["continued"]:
            next_elts = self.find_elements_near_by(elt["index"], step=1, amount=3)
            for next_elt in next_elts:
                if next_elt["class"] == "PARAGRAPH":
                    elt["text"] += next_elt["text"]
                    elt["chars"] += next_elt["chars"]
                    break
        return elt

    def merge_elements(self, element, elements):
        new_element = deepcopy(element)
        if ElementClassifier.get_type(element) == ElementType.PARAGRAPH:
            all_elements = [element] + elements
            all_elements = sorted(all_elements, key=lambda x: x["index"])
            text = ""
            chars = []
            for item in all_elements:
                if ElementClassifier.get_type(element) == ElementType.PARAGRAPH:
                    text += item["text"]
                    chars += item["chars"]
            new_element["text"] = text
            new_element["chars"] = chars

        else:
            pass  # TODO
        return new_element

    @staticmethod
    def merge_char_rects(chars, pos_key="char-position"):
        if not chars:
            return {}
        merged_page_rects = {}
        for page, group in groupby(chars, key=lambda x: x.get("page")):
            merged_rects = []
            index = 0
            for item_char in group:
                if not item_char["text"].strip():
                    continue
                rect = Rectangle(*item_char[pos_key])
                if not merged_rects:
                    merged_rects.append(rect)
                    continue
                if rect.y < merged_rects[index].yy:
                    merged_rects[index] = merged_rects[index].union(rect)
                elif chars.index(item_char) == 1:
                    merged_rect = merged_rects[index].union(rect)
                    if merged_rect.x == merged_rects[index].x and merged_rect.xx == rect.xx:
                        merged_rects[index] = merged_rect
                    else:
                        index += 1
                        merged_rects.append(rect)
                else:
                    index += 1
                    merged_rects.append(rect)
            merged_page_rects[page] = merged_rects
        return merged_page_rects

    def detail_locality_in_element(self, element, page, outline):
        element_class = element["class"]
        if element_class == "TABLE":
            cell_idxes = self.find_cell_idxes_by_outline(element, outline, page)
            return {"cells_idx": cell_idxes}
        if element_class in ["PARAGRAPH", "PAGE_HEADER", "PAGE_FOOTER"]:
            _, chars_idx = self.find_chars_idx_by_outline(page, outline, element)
            return {"chars_idx": chars_idx}
        if element_class in ["IMAGE", "SHAPE"]:
            return {}
        raise ValueError("Unknown element type: %s" % element_class)

    @staticmethod
    def get_page_rotation(page: dict) -> float:
        if PDFUtil.is_ocr_page(page):
            return page["ret_rotation"]
        return page.get("page_rotation", page["rotate"])

    def create_interdoc_from_answer(self, items: list[dict]):
        interdoc = {key: self.data[key] for key in ("id", "name", "path", "styles", "pages", "model_version", "thin")}

        chars_by_index = defaultdict(list)
        interdoc["orig_elements"] = elements = []
        for item in items:
            prev_left_texts = []
            for box in item["boxes"]:
                outline = [
                    box["box"]["box_left"],
                    box["box"]["box_top"],
                    box["box"]["box_right"],
                    box["box"]["box_bottom"],
                ]
                texts: list[str] = prev_left_texts + [
                    clean_txt(text).replace("|", "") for text in box["text"].split("\n") if text
                ]
                prev_left_texts = []
                for _, element in self.find_elements_by_outline(box["page"], outline):
                    elements.append(element)
                    intersection = Rectangle(*outline).intersect(Rectangle(*element["outline"]))
                    _, chars = self.find_chars_by_outline(box["page"], intersection.coords())
                    chars = [char for char in chars if clean_txt(char["text"]) and char["text"] != "|"]
                    full_text = "".join(char["text"] for char in chars)
                    for i, text in enumerate(texts):
                        text_len = len(text)
                        if not full_text:
                            break
                        if len(text) > len(full_text):
                            text_len = len(full_text)
                            start = full_text.find(text[:text_len])
                        else:
                            start = full_text.find(text)
                        if start >= 0:
                            texts[i] = text[text_len:]
                            chars_by_index[(box["page"], element["index"])].extend(chars[start : start + text_len])
                            chars = chars[:start] + chars[start + text_len :]
                            full_text = "".join(char["text"] for char in chars)
                        else:
                            break
                    texts = [text for text in texts if clean_txt(text)]
                prev_left_texts.extend(texts)

        index = 0
        interdoc["paragraphs"] = []
        for (page, _), chars in sorted(chars_by_index.items()):
            interdoc["paragraphs"].append(
                {
                    "page": page,
                    "index": index,
                    "text": "".join(char["text"] for char in chars),
                    "type": "PARAGRAPH_1",
                    "class": "PARAGRAPH",
                    "outline": merge_box(chars, offset=2),
                    "chars": chars,
                }
            )
            index += 1
        return interdoc

    @staticmethod
    def is_element_multi_lines(element):
        if not (chars := element.get("chars")):
            return False
        box_bottom = chars[0]["box"][3]
        for char in chars[1:]:
            if char["box"][1] > box_bottom:
                return True
        return False

    @staticmethod
    def get_paragraphs_from_table(element, cell_separator="", cols=None, keep_dummy=False):
        """
        公司代码/公司简称/公告编号/户名/开户行 等误识别为table的情况,把element组装成paragraphs
        """
        paragraphs = []
        cells_by_row, _ = group_cells(element["cells"])
        for _, cells in cells_by_row.items():
            line_content = []
            line_chars = []
            for col, cell in cells.items():
                if cell.get("dummy") and (not keep_dummy or col != 0):
                    continue
                if cols and int(col) not in cols:
                    continue
                cell_text = clean_txt(cell.get("text", ""))
                if cell_text:
                    line_content.append(cell_text)
                    line_chars.extend([i for i in cell["chars"] if not re.search(r"^\s+$", i["text"])])
                    if cell_separator and line_chars:
                        line_content.append(cell_separator)
                        fake_char = copy.deepcopy(line_chars[-1])
                        fake_char["text"] = cell_separator
                        line_chars.append(fake_char)

            paragraph = {
                "index": element["index"],
                "syllabus": element["syllabus"],
                "cells": element["cells"],
                "text": cell_separator.join(line_content),
                "para_cells": cells,
                "chars": line_chars,
                "class": "PARAGRAPH",
                "origin_class": "TABLE",
                "page": element["page"],
                "outline": get_bound_box([char["box"] for char in line_chars]),
            }
            paragraphs.append(paragraph)
        return paragraphs

    @staticmethod
    def restore_table_from_paragraphs(paragraphs):
        """get_paragraphs_from_table 的逆向操作"""
        if not paragraphs:
            return None

        table = paragraphs[0]
        cells = {}
        for paragraph in paragraphs:
            for cell in paragraph["para_cells"].values():
                cells[cell["index"]] = cell
        table["cells"] = cells
        return table

    @staticmethod
    def get_line_paragraphs_from_table(element, min_text_length=1):
        cache_key = f"paras_gte_{min_text_length}"
        if cache_key in element:
            return element[cache_key]

        paragraphs = []
        cells_by_row, _ = group_cells(element["cells"])
        for row, cells in cells_by_row.items():
            for col, cell in cells.items():
                if cell.get("dummy"):
                    continue
                text = cell.get("text", "")
                if len(text) < min_text_length:
                    continue
                chars = cell["chars"]
                start = 0
                for part in text.split("\n"):
                    _len = len(part)
                    line_chars = chars[start : start + _len]
                    start += _len + 1
                    if not line_chars:
                        continue
                    for page, _chars in groupby(line_chars, key=lambda c: c["page"]):
                        page_chars = list(_chars)
                        paragraph = {
                            "index": element["index"],
                            "syllabus": element["syllabus"],
                            "text": "".join(char["text"] for char in page_chars),
                            "cell": cell,
                            "cell_path": f"{element['index']}@{page}@{row}_{col}",
                            "chars": page_chars,
                            "class": "PARAGRAPH",
                            "type": "PARAGRAPH_1",
                            "origin_class": "TABLE",
                            "page": page,
                            "outline": get_bound_box([char["box"] for char in page_chars]),
                        }
                        paragraphs.append(paragraph)
        element[cache_key] = paragraphs
        return paragraphs

    def get_paragraphs_by_syllabus(self, syllabus, table_cell_line_min_length=0):
        if not table_cell_line_min_length:
            return self.get_elements_by_syllabus(syllabus)

        index_multiplier = 10_0000
        elements = self.get_elements_by_syllabus(syllabus, ["PARAGRAPH", "TABLE"])
        paras = []
        for element in elements:
            if element["class"] == "TABLE":
                table_paras = self.get_line_paragraphs_from_table(element, min_text_length=table_cell_line_min_length)
                for idx, table_para in enumerate(table_paras):
                    copied_para = table_para.copy()
                    copied_para["index"] = copied_para["index"] * index_multiplier + idx  # 新版calliper会合并相同index
                    paras.append(copied_para)
            else:
                copied_element = element.copy()
                copied_element["index"] = copied_element["index"] * index_multiplier
                paras.append(copied_element)
        return paras

    def elements_outline(self, elements):
        """
        获取elements的外框
        """
        page_elements = OrderedDict()
        for element in elements:
            page_elements.setdefault(element["page"], []).append(element)
            # 跨页段落的框属于下一页 添加一个fake_element 仅用于计算大框
            page_merged_paragraph = element.get("page_merged_paragraph", {})
            if (
                page_merged_paragraph
                and page_merged_paragraph.get("page")
                and page_merged_paragraph["page"] != element["page"]
            ):
                fake_element = {"fragment": True, "class": "fake_element", "outline": page_merged_paragraph["outline"]}
                page_elements.setdefault(page_merged_paragraph["page"], []).append(fake_element)

            # 跨页表格
            page_merged_table = element.get("page_merged_table") or {}
            if not page_merged_table:
                continue
            for table_index in page_merged_table.get("cells_idx", {}):
                table_index = int(table_index)
                if table_index == element["index"]:
                    continue
                _, table_element = self.find_element_by_index(table_index)
                if table_element:
                    fake_element = {"fragment": True, "class": "fake_element", "outline": table_element["outline"]}

                    page_elements.setdefault(table_element["page"], []).append(fake_element)

        page_box = []
        for page, elts in page_elements.items():
            outline = [
                min(e["outline"][0] for e in elts),
                min(e["outline"][1] for e in elts),
                max(e["outline"][2] for e in elts),
                max(e["outline"][3] for e in elts),
            ]

            page_box.append(
                {
                    "page": page,
                    "outline": outline,
                    "text": "\n".join(
                        [self.element_text(ele) for ele in elts if not ele.get("fragment")]
                    ),  # 添加完整的段落text
                    "elements": [ele for ele in elts if ele.get("class") != "fake_element"],
                }
            )
            if elts and elts[0].get("fragment") and page_box[-1]["text"] and len(page_box) > 1:
                page_box[-1]["text"] = "\n" + page_box[-1]["text"]

        return page_box

    @staticmethod
    def element_text(ele):
        text = ""
        if ElementClassifier.like_paragraph(ele):
            text = ele.get("text", "")
        elif ElementClassifier.is_stamp(ele):
            text = ele.get("text", "")
        elif ElementClassifier.is_table(ele):
            cells_by_row, _ = group_cells(ele["cells"])
            row_texts = []
            for cells in cells_by_row.values():
                row_texts.append("|".join([cell["text"] for cell in cells.values()]))
            text = "\n".join(row_texts)
        else:
            logger.info(f"Pdfinsight.element_text unknown element type: {ele['class']}")
        return text


class PdfinsightElement:
    def __init__(self, element):
        self.element = element

    @property
    def index(self):
        return self.element["index"]

    @property
    def chars(self):
        return defaultdict(dict)

    @property
    def text(self):
        return "".join(i.get("text", "") for i in self.chars)


class PdfinsightParagraph(PdfinsightElement):
    @property
    def chars(self):
        return self.element.get("chars", [])


class PdfinsightTable(PdfinsightElement):
    def __init__(self, element):
        super().__init__(element)
        self._cells = None
        self._merged_mapping = None

    def sorted_rows(self, cells=None):
        return [
            [cell for cidx, cell in sorted(cell_dict.items(), key=lambda c: c[0])]
            for ridx, cell_dict in sorted(self.cells.items() if cells is None else cells.items(), key=lambda r: r[0])
        ]

    @property
    def cells(self):
        if not self.element.get("cells"):
            logger.warning(f"Invalid table {self.index} with no cells, {self.element.get('class')=}")
            self._cells = {}

        if self._cells is None:
            cells = {}
            for idx, cell in self.element["cells"].items():
                cell["index"] = idx
                ridx, cidx = idx.split("_")
                _row = cells.setdefault(int(ridx), {})
                _row[int(cidx)] = cell
            # 特例: 首行列头A|B|C|A|B|C, 需要水平拆分
            # NOTE: 暂时只检测首行
            # https://mm.paodingai.com/cheftin/pl/7idnbxabgjdxm8hgmw46r1chre
            sorted_rows = self.sorted_rows(cells)
            cell_count = Counter(cell["text"] for cell in sorted_rows[0])
            unique_counts = list(cell_count.values())
            if len(unique_counts) > 1 and all((unique_counts[0] == c and c > 1) for c in unique_counts):
                col_idx_group = [[] for _ in range(unique_counts[0])]
                for cell in sorted_rows[0]:
                    text = cell["text"]
                    col_idx_group[unique_counts[0] - cell_count[text]].append(int(cell["index"].split("_")[-1]))
                    cell_count[text] -= 1
                    if cell_count[text] == 0:
                        cell_count.pop(text)
                if all(is_consecutive(x) for x in col_idx_group):  # A|A|B|B, 不需要水平拆分
                    cells = self.regroup_table(sorted_rows, col_idx_group)
            self._cells = cells
        return self._cells

    @property
    def chars(self):
        ret = []
        for row_cells in self.cells.values():
            for cell in row_cells.values():
                ret.extend(cell["chars"])
        return ret

    @staticmethod
    def regroup_table(sorted_rows, idx_group: list[list[int]]):
        table = {}
        origin_len = len(sorted_rows)
        idx_group_map = {
            col_idx: {"group_idx": idx, "new_col_idx": col_idxes.index(col_idx)}
            for idx, col_idxes in enumerate(idx_group)
            for col_idx in col_idxes
        }
        for row_idx, row in enumerate(sorted_rows):
            for col_idx, cell in enumerate(row):
                _row_idx = row_idx + origin_len * idx_group_map[col_idx]["group_idx"]
                _col_idx = idx_group_map[col_idx]["new_col_idx"]
                table.setdefault(_row_idx, {})[_col_idx] = cell
        return table

    @property
    def size(self):
        height = len(self.cells)
        width = max(len(row_cells) for row_cells in self.cells.values()) if self.cells else 0
        return height, width

    @property
    def merged(self) -> list[tuple[int, int]]:
        return self.element["merged"]

    @cached_property
    def markdown(self):
        return self.to_markdown(self.element)

    def cell_merged_to(self, cidx, ridx) -> tuple[int, int]:
        if self._merged_mapping is None:
            self._merged_mapping = {}
            for item in self.merged:
                for cell in item[1:]:
                    self._merged_mapping[tuple(cell)] = tuple(item[0])
        return self._merged_mapping.get((cidx, ridx))

    def is_merged_cell(self, cell):
        for merge_group in self.element["merged"]:
            merge_group = ["_".join(map(str, x)) for x in merge_group]
            if cell["index"] in merge_group:
                return True
        return False

    def cell(self, row: int, col: int):
        return PdfinsightTableCell(self.cells[row][col])

    def find_cellidx_list_by_outline(self, page, outline):
        cells = []
        for ridx, row in self.cells.items():
            for cidx, cell in row.items():
                if cell["page"] == page and PdfinsightReader.overlap_percent(cell["box"], outline) > 0.618:
                    cells.append((ridx, cidx))
        return cells

    def find_first_cellidx_list_by_outline(self, page, outline):
        cells = self.find_cellidx_list_by_outline(page, outline)
        return cells[0] if cells else None

    @staticmethod
    def to_markdown(element, need_merged_table=True):
        """Convert table to markdown format"""

        def _get_merged_cell_dict(table):
            merged_cell_dict = {}
            for merged in table["merged"]:
                for cell_id in merged[1:]:
                    merged_cell_dict.setdefault(tuple(merged[0]), []).append(tuple(cell_id))
            return merged_cell_dict

        def _get_cell_text_dict(table):
            merged_cell_dict = _get_merged_cell_dict(table)
            cell_dict = {}
            for cell_id, cell in list(table["cells"].items()):
                x, y = [int(_x) for _x in cell_id.split("_")]
                cell_text = cell["text"]
                cell_dict.setdefault((x, y), cell_text)
                # copy text info to merged cell
                if not need_merged_table:
                    cell_text = ""
                for sub_cell_id in merged_cell_dict.get((x, y), []):
                    cell_dict.setdefault(sub_cell_id, cell_text)
            return cell_dict

        cell_texts = _get_cell_text_dict(element)
        n_row = len(element["grid"]["rows"]) + 1
        n_col = len(element["grid"]["columns"]) + 1
        md_table = ""
        header_line = "|" + "-|" * n_col + "\n"
        for i in range(n_row):
            md_table += "|"
            for j in range(n_col):
                md_table += cell_texts.get((i, j), "").replace("\n", "") + "|"
            md_table += "\n"
            if i == 0:
                md_table += header_line
        return md_table


class PdfinsightTableCell(dict):
    pass


class PdfinsightSyllabus:
    def __init__(self, syllabuses):
        self.syllabuses = syllabuses
        self.syllabus_dict = {syl["index"]: syl for syl in syllabuses}
        self.elt_syllabus_dict = {syl["element"]: syl for syl in syllabuses if "element" in syl}

    def is_syllabus_elt(self, element):
        return element.get("index") in self.elt_syllabus_dict

    def find_by_elt_index(self, index, include_self=True):
        """Unique element index"""
        sylls = [s for s in self.syllabus_dict.values() if index in range(*s["range"])]
        if index in self.elt_syllabus_dict and not include_self:
            # 如果elt是一个章节 那么这里返回的结果应该是其父级节点 自己不应该返回
            sylls = [i for i in sylls if i["element"] != index]
        return sorted(sylls, key=lambda s: s["index"])

    def full_syll_path(self, syll):
        sylls = []
        cursor = syll
        while cursor:
            sylls.insert(0, cursor)
            cursor = self.syllabus_dict.get(cursor["parent"])
        return sylls

    def get_root_syllabus(self, syllabus):
        parent = self.syllabus_dict.get(syllabus["parent"])
        if not parent:
            return syllabus
        return self.get_root_syllabus(parent)

    def get_child_syllabus(self, syllabus, level=None) -> list:
        if level and syllabus["level"] >= level:
            return []
        syllabus_list = []
        for index in syllabus["children"] or []:
            if child_syllabus := self.syllabus_dict.get(index):
                syllabus_list.append(child_syllabus)
                if child_list := self.get_child_syllabus(child_syllabus, level=level):
                    syllabus_list.extend(child_list)
        return syllabus_list

    def find_by_index(self, index):
        syll = self.syllabus_dict.get(index)
        return self.full_syll_path(syll)

    @staticmethod
    def match(pattern: Pattern | str, name: str):
        if isinstance(pattern, RE_TYPE):
            return pattern.search(name)
        if isinstance(pattern, str):
            return SequenceMatcher(None, pattern, name).ratio() > 0.6
        return False

    def find_by_pattern(
        self,
        patterns: list[Pattern | str],
        candidates: list[int] | None = None,
        order_by="index",
        reverse=False,
        clean_func=None,
    ):
        """
        patterns 支持 正则、字符串 两种模式：
        正则：正则匹配
        字符串：相似度超过 60%
        """

        if not patterns:
            return []
        res = []
        head_p, *tails_p = patterns
        if candidates is None:
            syllabuses = list(self.syllabus_dict.values())
        else:
            syllabuses = [self.syllabus_dict[i] for i in candidates if i in self.syllabus_dict]
        for syllabus in sorted(syllabuses, key=lambda x: x[order_by], reverse=reverse):
            cleaned_title = clean_func(syllabus["title"]) if clean_func else clean_txt(syllabus["title"])
            if not self.match(head_p, cleaned_title):
                continue
            if not tails_p:
                # 只有一个pattern取当前章节
                res.append(syllabus)
            elif tails := self.find_by_pattern(
                tails_p, candidates=syllabus["children"] or [], clean_func=clean_func, order_by=order_by
            ):
                # 多个pattern说明是按父子关系严格匹配, 取后续子章节
                res.extend(tails)
        return res

    def find_syllabus_by_patterns(
        self,
        patterns: list[Pattern | str],
        candidates: list[int] | None = None,
        reverse=False,
        clean_func=None,
        is_continued_chapter=True,
    ):
        res = []
        head_p, *tails_p = patterns
        if candidates is None:
            syllabuses = list(self.syllabus_dict.values())
        else:
            syllabuses = [self.syllabus_dict[i] for i in candidates if i in self.syllabus_dict]
        candidates = set()
        for syllabus in sorted(syllabuses, key=lambda x: x["level"], reverse=reverse):
            cleaned_title = clean_func(syllabus["title"]) if clean_func else clean_txt(syllabus["title"])
            match_res = self.match(head_p, cleaned_title)
            if not match_res:
                if is_continued_chapter:
                    continue
                for idx in syllabus["children"] or []:
                    candidates.add(idx)
            else:
                if not tails_p:
                    # 只有一个pattern取当前章节
                    return [syllabus]
                child_syllabus = self.find_syllabus_by_patterns(
                    tails_p,
                    candidates=syllabus["children"] or [],
                    reverse=reverse,
                    clean_func=clean_func,
                    is_continued_chapter=is_continued_chapter,
                )
                if child_syllabus and len(child_syllabus) == len(tails_p):
                    res.append(syllabus)
                    res.extend(child_syllabus)
                    break
        else:
            if candidates:
                child_syllabus = self.find_syllabus_by_patterns(
                    patterns,
                    candidates=list(candidates),
                    reverse=reverse,
                    clean_func=clean_func,
                    is_continued_chapter=is_continued_chapter,
                )
                if child_syllabus and len(child_syllabus) == len(patterns):
                    res.extend(child_syllabus)
        return res if len(patterns) == len(res) else []

    def find_by_clear_title(self, title, order_by="index", reverse=False, multi=False, equal_mode=False):
        res = []
        for syl in sorted(self.syllabus_dict.values(), key=lambda x: x[order_by], reverse=reverse):
            condition = (
                clear_syl_title(syl["title"]) == title
                if equal_mode
                else re.search(title, clear_syl_title(syl["title"]))
            )
            if condition:
                res.append(syl)
                if not multi:
                    break
        return res

    def find_sylls_by_name(self, names, candidates=None):
        res = []
        name = names[0]
        if not candidates:
            candidates = sorted(self.syllabus_dict.keys())
        for syll_idx in candidates:
            syll = self.syllabus_dict[syll_idx]
            if name == syll["title"]:
                res.append(syll)
                if len(names) > 1:
                    tails = self.find_sylls_by_name(names[1:], candidates=syll["children"])
                    if not tails:
                        return []
                    res.extend(tails)
        return res

    @classmethod
    def syl_outline(
        cls,
        syllabus,
        pdfinsight,
        include_title=False,
        ignore_pattern=None,
        only_before_first_chapter=None,
        include_sub_title=True,
        break_para_pattern=None,
        include_break_para=False,
        skip_table=False,  # 跳过syllabus里的表格
        page_header_patterns=None,
        skip_types=None,
        valid_types=None,
    ):
        """
        获取章节外框
        """

        def get_page_merged_paragraph_indexes(elt):
            indexes = set()
            if elt.get("page_merged_paragraph"):
                for elt_index in elt["page_merged_paragraph"]["paragraph_indices"]:
                    element_indices.add(elt_index)
            else:
                element_indices.add(elt["index"])
            return indexes

        if skip_types is None:
            skip_types = []
        elements = []
        start, end = syllabus["range"]
        if only_before_first_chapter:
            children = syllabus["children"]
            if children:
                first_children = children[0]
                first_children_syllabus = pdfinsight.syllabus_dict[first_children]
                end = first_children_syllabus["element"]
        if include_title:  # 是否包含章节标题
            elt_type, elt = pdfinsight.find_element_by_index(start)
            if elt_type == "PARAGRAPH":
                elements.append(elt)
        element_indices = set()
        exclude_indices = set()
        for idx in range(start + 1, end):
            elt_type, elt = pdfinsight.find_element_by_index(idx)
            if not elt:
                continue
            if elt["index"] in exclude_indices:
                continue
            if (
                not include_sub_title
                and elt.get("syllabus") in syllabus["children"]
                and elt["index"] in pdfinsight.syllabus_reader.elt_syllabus_dict
            ):
                continue
            if elt_type == "TABLE" and skip_table:
                continue
            if elt_type in skip_types:
                continue
            if valid_types and elt_type not in valid_types:
                continue
            clean_element_text = clean_txt(elt.get("text", ""))
            if break_para_pattern and break_para_pattern.nexts(clean_element_text):
                if include_break_para:
                    elements.append(elt)
                break
            elt_type = fix_ele_type(pdfinsight, page_header_patterns, elt_type, elt)
            if elt and elt_type not in ["PAGE_HEADER", "PAGE_FOOTER"] and elt["index"] not in element_indices:
                if ignore_pattern and ignore_pattern.patterns and ignore_pattern.nexts(clean_element_text):
                    exclude_indices.update(get_page_merged_paragraph_indexes(elt))
                    continue
                elements.append(elt)
                element_indices.update(get_page_merged_paragraph_indexes(elt))
        return cls.elements_outline(elements)

    @classmethod
    def elements_outline(cls, elements):
        """
        获取elements的外框
        """
        page_elements = OrderedDict()
        for element in elements:
            page_elements.setdefault(element["page"], []).append(element)
            # 跨页段落的框属于下一页 添加一个fake_element 仅用于计算大框
            page_merged_paragraph = element.get("page_merged_paragraph", {})
            if (
                page_merged_paragraph
                and page_merged_paragraph.get("page")
                and page_merged_paragraph["page"] != element["page"]
            ):
                fake_element = {"fragment": True, "class": "fake_element", "outline": page_merged_paragraph["outline"]}
                page_elements.setdefault(page_merged_paragraph["page"], []).append(fake_element)

        page_box = []
        for page, elts in page_elements.items():
            outline = [
                min(e["outline"][0] for e in elts),
                min(e["outline"][1] for e in elts),
                max(e["outline"][2] for e in elts),
                max(e["outline"][3] for e in elts),
            ]

            page_box.append(
                {
                    "page": page,
                    "outline": outline,
                    "text": "\n".join(
                        [cls.element_text(ele) for ele in elts if not ele.get("fragment")]
                    ),  # 添加完整的段落text
                    "elements": [ele for ele in elts if ele.get("class") != "fake_element"],
                }
            )
            if elts and elts[0].get("fragment") and page_box[-1]["text"] and len(page_box) > 1:
                page_box[-1]["text"] = "\n" + page_box[-1]["text"]

        return page_box

    @staticmethod
    def element_text(ele):
        text = ""
        if ElementClassifier.like_paragraph(ele):
            text = ele.get("text", "")
        elif ElementClassifier.is_stamp(ele):
            text = ele.get("text", "")
        elif ElementClassifier.is_table(ele):
            cells_by_row, _ = group_cells(ele["cells"])
            row_texts = []
            for cells in cells_by_row.values():
                row_texts.append("|".join([cell["text"] for cell in cells.values()]))
            text = "\n".join(row_texts)
        else:
            logger.info(f"Pdfinsight.element_text unknown element type: {ele['class']}")
        return text

    @staticmethod
    def is_valid_syllabus(syllabus_id):
        return not (syllabus_id is None or syllabus_id == -1)


def init_cells_bound(tbl, row_base):
    for idx, cell in tbl["cells"].items():
        row, col = idx.split("_")
        row, col = int(row) + row_base, int(col)
        cell.setdefault("left", col)
        cell.setdefault("right", col + 1)
        cell.setdefault("top", row)
        cell.setdefault("bottom", row + 1)


class MergedTable:
    def __init__(self, tables):
        self.tables = tables or []
        self._cells = None
        self.column_count = self.fix_table_column(tables)
        if len(self.tables) > 1:
            for tbl in self.tables[1:]:
                tbl["page_merged_table"] = self.tables[0]["index"]  # 此处修改了page_merged_table的数据格式

    @property
    def index(self):
        return self.tables[0].get("index", 0)

    @property
    def row_count(self):
        return max(int(idx.split("_")[0]) for idx in self.cells) + 1

    @classmethod
    def fix_table_column(cls, tables, include_special_table=False):
        if not tables:
            return 0
        if len(tables) == 1:
            return cls.get_table_col_size(tables[0])
        # 内嵌表格的index为 float,增加了is_nested属性来辅助判断该表格是否为内嵌表格，只有内嵌表格才有该属性
        if tables[0].get("is_nested") and tables[1].get("is_nested"):
            return None
        column_0 = cls.get_table_col_size(tables[0])
        column_1 = cls.get_table_col_size(tables[1])
        if tables[0]["continued"]:
            return max(column_1, column_0)
        if column_0 == column_1:
            return column_0
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/904#note_229140
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1582
        if include_special_table and column_1 > column_0 > 1:
            cls.fix_special_table_columns(tables, column_0, column_1)
            return column_1
        return None

    @classmethod
    def fix_special_table_columns(cls, tables, column_0, column_1):
        """
        处理跨页表格，跨页时第一个表格的列比第二个表格的列少的情况
        """
        step = (column_1 - 1) // (column_0 - 1) or 1
        new_cells = {}
        merged = tables[0].get("merged", [])
        new_merged = deepcopy(merged)
        for idx, cell in tables[0]["cells"].items():
            row, col = [int(item) for item in idx.split("_")]
            new_col = None
            if col > 0:
                new_col = (col - 1) * step + 1
                key = "{}_{}".format(row, new_col)
            else:
                key = idx
            new_cells[key] = cell
            if new_col is None:
                continue
            cell_indices = [row, col]
            new_cell_indices = [[row, icol] for icol in range(new_col, new_col + step)]
            inserted = False
            for item, new_item in zip(merged, new_merged):
                if cell_indices in item and cell_indices in new_item:
                    new_item.remove(cell_indices)
                    new_item.extend(new_cell_indices)
                    inserted = True
                    break
            if not inserted:
                new_merged.append(new_cell_indices)
        tables[0]["cells"] = new_cells
        tables[0]["merged"] = new_merged

    @property
    def cells(self):
        if self._cells:
            return self._cells
        self._cells = ITable(self.tables).cells
        return self._cells

    @classmethod
    def fix_tbl_merged(cls, table, next_table):
        if table["merged"]:
            return
        merged = []
        merged_data_by_col = defaultdict(list)
        merged_data_by_row = defaultdict(list)
        continued_row = table["continued_row"] or 0
        if continued_row > 0:  # 说明下面表格的第一行不需要跟上方的表格的最后一行合并 有可能是重复写的表头
            next_table_merged = next_table["merged"]
            for merged_data in next_table_merged:
                min_row = min(row for row, col in merged_data)
                if min_row >= continued_row:
                    break
                if min_row < cls.get_table_row_size(table):
                    merged.append(merged_data)
                    if len({i[0] for i in merged_data}) == 1:
                        merged_data_by_row[merged_data[0][0]].append(merged_data)
                    elif len({i[1] for i in merged_data}) == 1:
                        merged_data_by_col[merged_data[0][1]].append(merged_data)

        # todo 先按照行处理 需要将col+offset 暂时未处理按列合并的情况 遇到再处理
        if not merged_data_by_row:
            return
        # 修改cell的keys
        tbl_cells = table["cells"]
        new_cells = {}
        # 按照行将table_cells 分组
        tbl_cells_groups = defaultdict(dict)
        for idx, cell in tbl_cells.items():
            row, col = idx.split("_")
            tbl_cells_groups[int(row)][idx] = cell
        for idx, merged_datas in merged_data_by_row.items():
            row = tbl_cells_groups.get(idx)
            if not row:
                continue
            offset = 0
            for merged_data in merged_datas:
                offset += len(merged_data) - 1
                first_idx = f"{merged_data[0][0]}_{merged_data[0][1]}"
                new_cells[first_idx] = row[first_idx]
                for item in merged_data[1:]:
                    row_idx, col_idx = item
                    old_cell_idx = f"{str(row_idx)}_{str(col_idx)}"
                    cell_idx = f"{str(row_idx)}_{str(col_idx + offset)}"
                    new_cells[cell_idx] = row[old_cell_idx]
        table["merged"] = merged
        table["cells"] = new_cells

    @classmethod
    def fix_merged_cells(cls, tbl, row_base, cells, row_continued, next_tbl=None):
        """填充被合并的单元格"""
        if not tbl["merged"]:
            cls.fix_tbl_merged(tbl, next_tbl)
        tbl_cells = tbl["cells"]
        for merged in tbl["merged"]:
            cell = None
            max_row = row_base + max(row for row, col in merged)
            max_col = max(col for row, col in merged)
            for row, col in merged:
                cell = tbl_cells.get("{}_{}".format(row, col))
                if cell is not None:
                    # 修改跨页合并单元格的内容
                    if row_continued and row == 0 and col == 0 and cells.get(f"{row_base}_{col}"):
                        dummy_cell = deepcopy(cells[f"{row_base}_{col}"])
                        dummy_cell["right"] = max_col + 1
                        dummy_cell["bottom"] = max_row + 1
                        dummy_cell["dummy"] = True
                        cell = dummy_cell
                    else:
                        cell["right"] = max_col + 1
                        cell["bottom"] = max_row + 1
                    break
            if cell is not None:
                for row, col in merged:
                    key = "{}_{}".format(row, col)
                    if tbl_cells.get(key) is None:
                        dummy_cell = deepcopy(cell)
                        dummy_cell["dummy"] = True
                        tbl_cells[key] = dummy_cell

        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2173
        continued_cols: list[int] | None = tbl["continued_cols"]
        if continued_cols:
            pre_table_max_row: int = cls.get_table_row_size(tbl)
            next_table_cells: dict = next_tbl["cells"]
            next_table_merged: list[list[list[int]]] = next_tbl["merged"]  # [[[0, 0], [1, 0]],]
            start_cell_offset: int = tbl[
                "continued_row"
            ]  # 确定下一个表格的起始合并的idx,可能下一个表格的起始行是表头，这个会标识开始合并的行索引
            next_table_cross_cell: list[list[int]] = [
                [start_cell_offset, col] for col in continued_cols
            ]  # 下一个表格跨页合并列的cell
            # 1. 遍历所有下一个表里需要跨页合并的cell
            # 2. 如果这个cell在下一个表的合并项（合并项是一个列表嵌套结构，如果这个cell在其中的一个嵌套合并项目中）里，则需要进行替换其值
            for cross_cell in next_table_cross_cell:
                for merge_cell in next_table_merged:
                    if cross_cell not in merge_cell:
                        continue
                    for row, col in merge_cell:
                        cell = next_table_cells.get("{}_{}".format(row, col))
                        if cell is not None:
                            pre_tbl_last_cell = tbl_cells.get(f"{pre_table_max_row - 1}_{col}")
                            cell["text"] = pre_tbl_last_cell["text"]
                            cell["chars"] = pre_tbl_last_cell["chars"]

    @classmethod
    def get_table_row_begin(cls, tbl):
        return min(int(idx.split("_")[0]) for idx in tbl["cells"])

    @classmethod
    def get_table_row_size(cls, tbl):
        return max(int(idx.split("_")[0]) for idx in tbl["cells"]) + 1

    @classmethod
    def get_table_col_size(cls, tbl):
        return max(int(idx.split("_")[1]) for idx in tbl["cells"]) + 1

    @classmethod
    def get_table_rows(cls, tbl):
        return sorted({int(idx.split("_")[0]) for idx in tbl["cells"]})

    @staticmethod
    def is_cross_page_cell(cells, table, row, row_idx):
        """
        是否跨页单元格
        此处先只处理一种情况:cell不为空,cell在表格的第一行且该行第一列的单元格为空,上一页最后一行第一列单元格不为空
        :return:
        """
        if row != 0:  # cell在表格的第一行
            return False
        last_row_head_cell = cells.get("{}_{}".format(row_idx - 1, 0))
        row_head_cell = table["cells"].get("0_0")
        if not (last_row_head_cell and row_head_cell):
            return False
        if last_row_head_cell["page"] + 1 != row_head_cell["page"]:  # 仅相邻页
            return False
        if last_row_head_cell["text"] and not row_head_cell["text"]:  # 该行第一列的单元格为空
            return True
        return False
