# -*- coding: utf-8 -*-
"""按行/列读取的表格
表格解析方法：除 header 外，每行/列解析成 {"col1": "val1", "col2": "val2"}
模型：统计字段对应的 key
特殊情况：暂无

model 示意:
{
    "attr1": Counter({
        "header_key_1": 100,
        "header_key_2": 60,
        ...
    }),
    ...
}
"""

import logging
import re
from collections import Counter
from copy import deepcopy
from functools import cached_property
from itertools import groupby

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt, index_in_space_string
from remarkable.pdfinsight.parser import ParsedTableCell, parse_table
from remarkable.plugins.predict.common import is_paragraph_elt
from remarkable.predictor.dataset import DatasetItem
from remarkable.predictor.models.base_model import TableModel
from remarkable.predictor.schema_answer import (
    CharResult,
    PredictorResult,
    TableCellsResult,
)

logger = logging.getLogger(__name__)
serial_number_pattern = [r"序号"]
P_XPATH_TBL = re.compile(r"/w:tbl\[(\d+)]")


class TableRow(TableModel):
    # table_row 的 sub_primary_key 是默认配置为了所有的columns, 见SchemaPredictor.sub_primary_key
    __name__ = "table_row"
    filter_elements_by_target = True

    @property
    def multi(self):
        return self.get_config("multi", True)

    @property
    def table_type(self):
        return TableType.ROW.value if self.parse_by == "row" else TableType.COL.value

    @property
    def force_group_by_row(self):
        # group_by_row默认是True 代表使用table_row的模型会默认一行一组
        # 不同表格相同的数据也可提取出来
        # 如果不想提取重复的数据 可以将该配置修改为False
        return self.get_config("force_group_by_row", True)

    @property
    def parse_by(self):
        return self.get_config("parse_by", "row")

    def feature_from(self, col=None):
        return self.get_config("feature_from", "header", col)  # header/self/left_cells/right_cells

    @property
    def filter_serial_number(self):  # 忽略序号
        return self.get_config("filter_serial_number", False)

    @property
    def filter_single_data_row(self):  # 忽略整行合并成一个单元格的行
        return self.get_config("filter_single_data_row", True)

    @property
    def split_table_pattern(self):
        """切分表格的正则：有些表格解析不规范，会把表格上方的段落当成表格第一行，导致表头解析错误，需要切分，如：
        A: 关于xxx的公告
        | a | b | c |
        | - | - | - |
        | 1 | 2 | 3 |
        | x | y | z |
        ...
        会被解析成
        | A: 关于xxx的公告 |
        | - | - | - |
        | a | b | c |
        | 1 | 2 | 3 |
        | x | y | z |
        ...
        这就需要一个正则`r^a$`来切分表格，将表格上方的段落切分出去。
        """
        return PatternCollection(self.get_config("split_table_pattern"))

    @property
    def unit_column_pattern(self):
        """带单位的列名正则，如：产品数量-单位"""
        return PatternCollection(self.get_config("unit_column_pattern"))

    @property
    def special_title_pattern(self):
        return PatternCollection(self.get_config("special_title_pattern"))

    @property
    def width_from_all_rows(self):
        return PatternCollection(self.get_config("width_from_all_rows", False))

    @cached_property
    def cell_regs(self):
        cell_regs = {}
        for column in self.columns:
            cell_regs[column] = PatternCollection(self.get_config("cell_regs", [], column=column))
        return cell_regs

    @property
    def neglect_title_pattern(self):
        return PatternCollection(self.get_config("neglect_title_pattern", []))

    @staticmethod
    def calc_table_size(element, by="col") -> int:
        return len({idx.split("_")[1 if by == "col" else 0] for idx in element["cells"]})

    def __init__(self, options, schema, predictor=None):
        super().__init__(options, schema, predictor=predictor)
        self.syllabus_pattern = self.get_config("syllabus_pattern")  # abandon
        self.primary_schema_name = self.get_config("primary_schema_name")  # abandon
        self.header_regs = self.get_config("header_regs", [])  # 行头和列头需匹配的正则
        self.row_header_regs = self.get_config("row_header_regs", [])  # 行头需匹配的正则
        self.col_header_regs = self.get_config("col_header_regs", [])  # 列头需匹配的正则
        self.neglect_row = PatternCollection(self.get_config("neglect_row", []))  # 行的负向正则
        self.neglect_header_regs = self.get_config("neglect_header_regs", [])  # 行头和列头的负向正则  自动提取忽略这个
        self.neglect_row_header_regs = self.get_config("neglect_row_header_regs", [])  # 行头负向正则
        self.neglect_col_header_regs = self.get_config("neglect_col_header_regs", [])  # 列头负向正则
        self.ignore_header_regs = self.get_config(
            "ignore_header_regs", []
        )  # 生成特征时需要忽略的header,一般是因为表格解析问题 将表格上方的段落当成了表格第一行

    def train(self, dataset: list[DatasetItem], **kwargs):
        model_data = {}
        for col, col_path in self.columns_with_fullpath():
            logger.debug(f"<table_row> <train> {col=}")
            for item in dataset:
                logger.debug(f"<table_row> <train> {item.fid=}")
                for node in self.find_answer_nodes(item, col_path):
                    if node.data is None:
                        continue
                    try:
                        _features = self.extract_feature(item.data["elements"], node)
                    except IndexError as e:
                        logger.error(f"train for table_row failed, {item.fid=} {col=}")
                        logger.exception(e)
                    _model = model_data.setdefault(col, Counter())
                    _model.update(_features)
        self.model_data = model_data

    def get_model_data(self, column=None):
        model_data = super().get_model_data(column=column) or Counter()

        # blacklist
        blacklist = self.get_config("feature_black_list", default=[], column=column)
        blacklist_features = [k for k in model_data if any(self.is_match(b, k) for b in blacklist)]
        for bfeature in blacklist_features:
            model_data.pop(bfeature)

        # whitelist
        model_data.update(self.get_config("feature_white_list", default=[], column=column))

        return model_data

    def get_primary_cells(self, group, primary_models):
        res = {}
        for p_k, p_model in primary_models.items():
            for headers, aim_cell in group:
                header_str = self.feature_key_str({c.get("text") or "" for c in headers})
                if any(feature == header_str for feature, _ in p_model.most_common()):
                    res[p_k] = aim_cell
        return res

    def is_valid_content(self, cell, patterns, column):
        neglect_pattern = PatternCollection(patterns or [])
        cells = [cell]
        if self.feature_from(column) in ("self", "left_cells", "right_cells"):
            cells.extend(cell.row_header_cells or [cell.table.rows[cell.rowidx][0]])
        return not any(neglect_pattern.nexts(clean_txt(cell.text)) for cell in cells)

    def create_answer_result(self, column, element, cell):
        if self.unit_column_pattern and self.unit_column_pattern.nexts(column) and cell.unit:
            # *-单位：有单位就直接取单位的结果
            return self.create_result([CharResult(element, cell.unit.chars)], column=column)
        return self.create_result([TableCellsResult(element, [cell])], column=column)

    def prepare_table(self, element):
        table = None
        if self.split_table_pattern:
            # 尝试切分表格
            cells = {}
            idx = None
            chars = []
            sorted_cells = sorted(element["cells"].values(), key=lambda x: (x["row"], x["col"]))
            for cell in sorted_cells:
                if idx is None and self.split_table_pattern.nexts(cell.get("text", "")):
                    idx = cell["row"]
                if idx is None:
                    if not cell.get("dummy"):
                        chars.extend(cell["chars"])
                else:
                    # 整体上移
                    new_idx = f"{cell['row'] - idx}_{cell['col']}"
                    cells[new_idx] = cell.copy()
                    cells[new_idx]["top"] -= idx
                    cells[new_idx]["bottom"] -= idx

            if idx == 0:
                # 首行即匹配到表头，说明表格解析正确，不需要特殊处理。
                pass
            elif idx is not None:
                # 首行未匹配到表头，表格解析错误，需要拆分，表头上方的单元格拆分为段落，剩余的单元格row idx向上抬升。
                merged = []
                for row in element["merged"]:
                    new_merged = []
                    for row_idx, col_idx in row:
                        if row_idx < idx:
                            # 过滤
                            continue
                        # 上移
                        new_merged.append([row_idx - idx, col_idx])
                    if new_merged:
                        merged.append(new_merged)

                element_above = {
                    "text": "".join(c["text"] for c in chars),
                    "chars": chars,
                    "class": "PARAGRAPH",
                    "index": element["index"],
                    "outline": [*chars[0]["box"][:2], *chars[-1]["box"][2:]] if chars else element["outline"],
                }
                element = {**element, "cells": cells, "merged": merged, "title": element_above["text"]}
                table = parse_table(
                    element,
                    tabletype=self.table_type,
                    elements_above=[element_above],
                    special_title_patterns=self.special_title_pattern,
                )

        table = table or parse_table(
            element,
            tabletype=self.table_type,
            pdfinsight_reader=self.pdfinsight,
            special_title_patterns=self.special_title_pattern,
        )
        sticky_tables = [element]
        for elt in table.elements_above:
            if is_consecutive_sticky_table(sticky_tables[0], elt):
                sticky_tables.insert(0, elt)

        if len(sticky_tables) == 1:
            return table

        # 处理粘连表格
        new_element = deepcopy(sticky_tables[0])
        offset = self.calc_table_size(new_element, by="row")
        for elt in sticky_tables[1:]:
            heights = set()
            for merge_pairs in elt["merged"]:
                for pairs in merge_pairs:
                    pairs[0] += offset
                new_element["merged"].append(merge_pairs)
            for idx_str, cell in elt["cells"].items():
                row_idx, col_idx = idx_str.split("_")
                cell["row"] = int(row_idx) + offset
                cell["top"] += offset
                cell["bottom"] += offset
                cell["index"] = f"{int(row_idx) + offset}_{col_idx}"
                new_element["cells"][cell["index"]] = cell
                heights.add(int(row_idx))
            offset += max(heights)
        table = parse_table(
            new_element,
            tabletype=self.table_type,
            pdfinsight_reader=self.pdfinsight,
            special_title_patterns=self.special_title_pattern,
        )
        return table

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        answer_results = []
        elements = self.revise_elements(elements)
        if self.multi_elements:
            elements.sort(key=lambda x: x["index"])
        for element in elements:
            if element["class"] != "TABLE":
                # AutoModel中 filter_elements_by_target设置为None 所以这里需要再次过滤下
                continue
            if self.neglect_title_pattern and self.neglect_title_pattern.nexts(clean_txt(element.get("title"))):
                continue
            table = self.prepare_table(element)
            if not table:
                continue
            # distinguish_shape为True时，需要严格区分表格形状
            if self.predictor.config.get("distinguish_shape", False) and table.tabletype != TableType.ROW.value:
                continue
            self.process_table_items(table, element, answer_results)
            if not self.multi_elements and answer_results:
                # 多元素块
                break
        return answer_results

    def process_table_items(self, table, element, answer_results):
        items = table.rows if self.parse_by == "row" else table.cols
        for row in items:
            # 跳过 全是合并单元格的一行
            if self.filter_single_data_row and len(row) > 1 and len({cell.text for cell in row if cell.text}) == 1:
                continue
            if self.neglect_row and self.neglect_row.nexts(clean_txt("".join(cell.text for cell in row))):
                continue

            answer_result = {}
            answer_from_title = {}
            answer_from_above_row = {}
            answer_from_header = {}
            for column in self.columns:
                from_title_regs = self.get_config("from_title", column=column)
                distinguish_header = self.get_config("distinguish_header", default=True, column=column)

                if from_above_row := self.get_config("from_above_row", column=column):
                    answer = self.get_answer_from_above_row(column, table, row, from_above_row)
                    if answer:
                        answer_from_above_row.update(answer)
                        continue

                if from_title_regs and (not distinguish_header or not row[0].is_header):
                    answer = self.get_answer_from_title(from_title_regs, column, table)
                    if answer and not answer_from_title.get(column):
                        answer_from_title.update(answer)
                        continue

                cell_regs = self.cell_regs[column]
                model_data = self.get_model_data(column=column)
                if not model_data:
                    continue
                row_texts = {cell.normalized_text for cell in row if not cell.dummy}
                if not self.filter_single_data_row and len(row_texts) == 1 and "" in row_texts:
                    continue
                for cell in row:
                    if not self.is_valid_cell(cell, model_data, table.element, row_texts, column):
                        continue
                    if self.get_config("lazy_match") and answer_result.get(column):
                        # FIXME: 惰性匹配，对于'D_date'特征, 可能会匹配到多列, 暂时只取一列
                        continue
                    if cell_regs and (matcher := cell_regs.nexts(clean_txt(cell.text))):
                        if dst_chars := self.get_dst_chars_from_matcher(matcher, cell.raw_cell):
                            answer_result.setdefault(column, []).append(
                                self.create_result(
                                    self.create_content_result(element, dst_chars, [cell], None), column=column
                                )
                            )
                        continue
                    else:
                        if from_header_regs := self.get_config("from_header", column=column):
                            if (
                                answer := self.get_answer_from_header(element, from_header_regs, column, cell)
                            ) and not answer_from_header.get(column):
                                answer_from_header.update(answer)
                            continue
                    answer_result.setdefault(column, []).append(self.create_answer_result(column, table.element, cell))

            if answer_result:
                answer_result.update(answer_from_title)
                answer_result.update(answer_from_above_row)
                answer_result.update(answer_from_header)
                answer_results.append(answer_result)
                if not self.multi:
                    # 多行
                    break

    def is_valid_cell(self, cell, model_data, element, row_texts, column):
        distinguish_header = self.get_config("distinguish_header", default=True, column=column)
        if (
            self.feature_from(column) == "header"
            and distinguish_header
            and ((self.parse_by == "row" and cell.is_col_header) or (self.parse_by == "col" and cell.is_row_header))
        ):
            return False
        if not self.match_feature(cell, model_data, column):
            return False
        if not self.is_valid_content(cell, self.get_config("neglect_patterns", default=[], column=column), column):
            return False
        if self.header_regs and not self.match_special_header(self.header_regs, cell, element):
            return False
        if self.row_header_regs and not self.match_special_header(self.row_header_regs, cell, element, col=False):
            return False
        if self.col_header_regs and not self.match_special_header(self.col_header_regs, cell, element, row=False):
            return False
        if self.neglect_header_regs and self.match_special_header(self.neglect_header_regs, cell, element):
            return False
        if self.neglect_row_header_regs and self.match_special_header(
            self.neglect_row_header_regs, cell, element, col=False
        ):
            return False
        if self.neglect_col_header_regs and self.match_special_header(
            self.neglect_col_header_regs, cell, element, row=False
        ):
            return False
        if self.filter_serial_number and self.match_special_header(serial_number_pattern, cell, element):
            return False
        # 过滤掉同一行的合并单元格
        if cell.dummy and cell.normalized_text in row_texts:
            return False
        return True

    @staticmethod
    def match_special_header(header_regs, cell, element, col=True, row=True):
        header_reg_pattern = PatternCollection(header_regs)
        row_headers = [element["cells"].get(f"{cell.rowidx}_{i}", {}).get("text", "") for i in range(2)]
        col_headers = [element["cells"].get(f"{i}_{cell.colidx}", {}).get("text", "") for i in range(2)]
        headers = []
        if row:
            headers.extend(row_headers)
        if col:
            headers.extend(col_headers)
        return any((any(header_reg_pattern.search(clean_txt(i))) for i in headers))

    def get_answer_from_title(self, from_title_regs, column, table):
        answer_result = {}
        if not from_title_regs or not table.elements_above:
            return answer_result

        pattern = PatternCollection(from_title_regs)
        for ele in table.elements_above:
            if not is_paragraph_elt(ele) or (table.title and ele["text"] != table.title.text):
                continue
            ele_text = clean_txt(ele["text"])
            if match := pattern.nexts(ele_text):
                c_start, c_end = match.span("dst")
                sp_start, sp_end = index_in_space_string(ele["text"], (c_start, c_end))
                dst_chars = ele.get("chars")[sp_start:sp_end]
                if dst_chars:
                    answer_result.setdefault(column, []).append(
                        self.create_result([CharResult(ele, dst_chars)], column=column)
                    )
                    break
        return answer_result

    def get_answer_from_above_row(self, column, table, row, regs):
        answer_result = {}
        pattern = PatternCollection(regs)

        above_rows = [x for x in table.rows if x[0].rowidx < row[0].rowidx]
        for item in above_rows[::-1]:
            for cell in item:
                if matcher := pattern.nexts(clean_txt(cell.text)):
                    if dst_chars := self.get_dst_chars_from_matcher(matcher, cell.raw_cell):
                        answer_result.setdefault(column, []).append(
                            self.create_result(
                                self.create_content_result(table.element, dst_chars, [cell], None), column=column
                            )
                        )
                        return answer_result
        return answer_result

    def get_answer_from_header(self, element, from_header_regs, column, cell):
        answer_result = {}
        pattern = PatternCollection(from_header_regs)
        headers = self.get_headers(cell, column)
        for header in headers:
            if matcher := pattern.nexts(clean_txt(header.text)):
                if dst_chars := self.get_dst_chars_from_matcher(matcher, header.raw_cell):
                    answer_result.setdefault(column, []).append(
                        self.create_result(
                            self.create_content_result(element, dst_chars, [header], None), column=column
                        )
                    )
                    break

        return answer_result

    def match_feature(self, cell: ParsedTableCell, model_data, column):
        if not model_data:
            return False
        # 先用包含subtitle的匹配一次
        header_str, origin_texts = self.prepare_data(cell, column, include_subtitle=True)
        for feature, _ in model_data.most_common():
            if self.is_match(feature, header_str, origin_texts):
                return True

        # 再用不包含subtitle的匹配一次
        header_str, origin_texts = self.prepare_data(cell, column, include_subtitle=False)
        for feature, _ in model_data.most_common():
            if self.is_match(feature, header_str, origin_texts):
                return True
        return False

    def prepare_data(self, cell: ParsedTableCell, column, include_subtitle=False):
        feature_texts = []
        if include_subtitle and cell.subtitle:
            feature_texts.append(clean_txt(cell.subtitle))
        headers = self.get_headers(cell, column)
        origin_texts = feature_texts[::]  # 包含 cell text, sub title的 原始数据
        feature_texts.extend([clean_txt(c.normalized_text) for c in headers if c.text])
        origin_texts.extend([clean_txt(c.text) for c in headers if c.text])
        header_str = self.feature_key_str(feature_texts)
        return header_str, origin_texts

    def extract_feature(self, elements, answer):
        features = Counter()
        for answer_data in answer.data["data"]:
            if not answer_data["boxes"]:
                continue
            box = answer_data["boxes"][0]  # TODO:
            for eid in answer_data["elements"]:
                element = elements.get(eid)
                if not element or not self.is_target_element(element):
                    logger.debug(f"element index: <{eid}> is not target element")
                    logger.debug(f"{box=}")
                    continue
                table = parse_table(element, tabletype=self.table_type, width_from_all_rows=self.width_from_all_rows)
                for answer_cell in table.find_cells_by_outline(box["page"], box["box"]):
                    feature_texts = []
                    if answer_cell.subtitle:
                        feature_texts.append(clean_txt(answer_cell.subtitle))
                    headers = self.get_headers(answer_cell, answer.name)
                    if not headers:
                        continue
                    feature_texts.extend([clean_txt(header.normalized_text) for header in headers if header.text])
                    header_str = self.feature_key_str(feature_texts)
                    features.update([header_str])
        return features

    def get_headers(self, cell: ParsedTableCell, col):
        feature_from = self.feature_from(col)
        if feature_from == "header":
            if not self.ignore_header_regs:
                return {"row": cell.col_header_cells, "col": cell.row_header_cells}[self.parse_by]
            ignore_pattern = PatternCollection(self.ignore_header_regs)
            col_header_cells = [i for i in cell.col_header_cells if not ignore_pattern.nexts(clean_txt(i.text))]
            row_header_cells = [i for i in cell.row_header_cells if not ignore_pattern.nexts(clean_txt(i.text))]
            return {"row": col_header_cells, "col": row_header_cells}[self.parse_by]
        if feature_from == "self":
            return [cell]
        if feature_from == "left_cells":
            # 取左边单元格作为feature
            return cell.table.rows[cell.rowidx][: cell.colidx]
        if feature_from == "right_cells":
            # 取右边单元格作为feature
            return cell.table.rows[cell.rowidx][cell.colidx + 1 :]
        return []

    # @staticmethod
    # def parse_table(element):
    #     """按行解析
    #     | col1 | col2 | col3 |
    #     | val1 | val2 | val3 |
    #     """
    #     tbl = PdfinsightTable(element)
    #     # topleft = tbl.cells[0][0]
    #     # header_height = topleft["bottom"] - topleft["top"]

    #     # 获取header_cell 所在的行
    #     header_row_index = get_header_row_index(tbl)
    #     # 获取header信息
    #     headers, excluded_index = get_header(header_row_index, tbl)
    #     # 获取header_index 和 answer_index
    #     header_id_group, answer_index_group = get_header_and_
    #     answer_ids(tbl, headers, header_row_index, excluded_index)
    #     # 分组遍历header和rows
    #     records = iter_answer(tbl, headers, answer_index_group, header_id_group)
    #     return records

    @staticmethod
    def find_tuple_by_same_text(group, answer_box):
        for header, value_cell in group:
            answer_text = answer_box.get("text")
            value_cell_text = value_cell.get("text")
            if answer_text and value_cell_text and answer_text == value_cell_text:
                return header, value_cell
        return None, None

    @staticmethod
    def find_tuple_by_header_text(group, text):
        keys = text.split("|")
        for header_cells, value_cell in group:
            if all(any(TableRow.same_text(_cell, key) for _cell in header_cells) for key in keys):
                return header_cells, value_cell
        return None, None


def get_header(header_row_index, tbl):
    headers = {}
    excluded_index = set()
    for index in header_row_index:
        cells = tbl.cells[index]
        header_height = cells[0]["bottom"] - cells[0]["top"]
        if header_height > 1:  # 前几行合并的表格
            for i in range(header_height):
                excluded_index.add(i)
        elif len({cell.get("text") for cell in cells.values()}) == 1:
            header_height += 1
            excluded_index.add(index + 1)
        for i in range(len(cells)):
            header_cells = [tbl.cells[j][i] for j in range(index, index + header_height)]
            if all((cell.get("dummy") for cell in header_cells)):
                continue
            headers[f"{index}_{i}"] = header_cells
    return headers, excluded_index


def get_header_and_answer_ids(tbl, headers, header_row_index, excluded_index):
    header_row_index.update(excluded_index)
    answer_index = set(range(len(tbl.cells))).difference(header_row_index)
    answer_index_group = []
    for _, i in groupby(enumerate(answer_index), lambda x: x[1] - x[0]):
        answer_index_group.append([j for _, j in i])
    header_id_group = []
    for _, i in groupby(headers, lambda x: x[0]):
        header_id_group.append(list(i))
    return header_id_group, answer_index_group


def iter_answer(tbl, headers, answer_index_group, header_id_group):
    records = []
    for answer_indexes, header_ids in zip(answer_index_group, header_id_group):
        for answer_index in answer_indexes:
            group = []
            row = tbl.cells[answer_index]
            for header_id in header_ids:
                header = headers[header_id]
                _, header_col_id = header_id.split("_")
                val_cell = row.get(int(header_col_id), {})
                if val_cell and not val_cell.get("dummy"):
                    group.append((header, val_cell))
            records.append(group)
    return records


def is_consecutive_sticky_table(tbl_a, tbl_b) -> bool:
    """判断两个表格是否是连续粘连的表格"""
    if tbl_a["class"] != "TABLE" or tbl_b["class"] != "TABLE":
        return False
    if TableRow.calc_table_size(tbl_a) != TableRow.calc_table_size(tbl_b):
        return False
    if abs(tbl_a["page"] - tbl_b["page"]) > 1:
        return False
    if not tbl_a.get("docx_meta", {}).get("xpath") or not tbl_b.get("docx_meta", {}).get("xpath"):
        return False
    # {'xpath': '/w:document[1]/w:body[1]/w:tbl[6]'}
    xpath_a = tbl_a["docx_meta"]["xpath"]
    # {'xpath': '/w:document[1]/w:body[1]/w:tbl[7]'}
    xpath_b = tbl_b["docx_meta"]["xpath"]
    if match := P_XPATH_TBL.search(xpath_a):
        idx_a = int(match.group(1))
    else:
        return False
    if match := P_XPATH_TBL.search(xpath_b):
        idx_b = int(match.group(1))
    else:
        return False
    return abs(idx_b - idx_a) == 1
