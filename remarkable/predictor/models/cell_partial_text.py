import logging
from collections import defaultdict

from remarkable.common.constants import TableType
from remarkable.common.multiprocess import run_in_multiprocess
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.predictor.dataset import DatasetItem
from remarkable.predictor.eltype import ElementClassifier
from remarkable.predictor.models.partial_text import VMSP, PartialText, VMSPInput
from remarkable.service.predictor import (
    PatternString,
    extract_feature_by_group,
    generate_answer_boundary,
)

logger = logging.getLogger(__name__)


class CellPartialText(PartialText):
    # target_element = ElementType.TABLE
    filter_elements_by_target = False

    @property
    def merge_row(self):
        return self.get_config("merge_row", False)

    @property
    def width_from_all_rows(self):
        return self.get_config("width_from_all_rows", False)  # 默认取表格第一行宽度, 为True时取最宽的行

    @property
    def merge_condition(self):
        return self.get_config("merge_condition")

    @property
    def header_pattern(self):
        return PatternCollection(self.get_config("header_pattern", []))

    @property
    def neglect_row_pattern(self):
        return PatternCollection(self.get_config("neglect_row_pattern", []))

    @property
    def break_pattern(self):
        return PatternCollection(self.get_config("break_pattern", []))

    @property
    def filter_by(self):
        return self.get_config("filter_by", "row")

    @property
    def from_cell(self):
        return self.get_config("from_cell", True)

    def is_mergeable(self, row):
        return any(merge_flag not in "".join([cell.text for cell in row]) for merge_flag in self.merge_condition)

    def predict_schema_answer(self, elements):
        answer_results = []
        elements = elements or []
        predicted_columns = []
        logger.debug(f"start predict answer by cell_partial_text, for schema: {self.predictor.schema_name}")
        for element in elements:
            if element["class"] != "TABLE":
                continue
            # todo 过滤不支持的表格
            logger.debug(f"<cell_partial_text>: {element['index']=}")
            answer_result = self.extract_by_element(element, predicted_columns)
            if answer_result:
                answer_results.append(answer_result)
                if not self.multi_elements:
                    break
        logger.debug(f"length of result by cell_partial_text: {len(answer_results)}")
        return answer_results

    def extract_by_element(self, element, predicted_columns):
        answer_result = {}
        table = parse_table(
            element,
            tabletype=TableType.TUPLE.value,
            pdfinsight_reader=self.pdfinsight,
            width_from_all_rows=self.width_from_all_rows,
        )
        items = table.rows if self.filter_by == "row" else table.cols

        for item in items:
            if self.header_pattern:
                if self.filter_by == "row":
                    header_text = clean_txt("|".join(header.text for header in item[0].row_header_cells))
                else:
                    header_text = clean_txt("|".join(header.text for header in item[0].col_header_cells))
                if not self.header_pattern.nexts(header_text):
                    continue

            row_text = clean_txt("|".join(cell.text for cell in item))  # include dummy cell
            if self.neglect_row_pattern:
                if self.neglect_row_pattern.nexts(row_text):
                    continue
            if self.break_pattern and self.break_pattern.nexts(row_text):
                break

            if self.from_cell:
                for cell in item:
                    vmsp_input = VMSPInput.from_cell(cell.raw_cell, element)
                    for column in self.columns:
                        logger.debug(f"<cell_partial_text>: from_cell {column=}, {cell.text=}")
                        if column in answer_result:
                            continue
                        column_answer_result = self.extract_for_column(element, column, predicted_columns, vmsp_input)
                        if column_answer_result:
                            answer_result.update(column_answer_result)
            if not answer_result:
                row_text = ""
                row_chars = []
                for cell in item:
                    if cell.dummy and cell.text in row_text:
                        logger.debug(f"<cell_partial_text>: {cell.text=} is dummy, skip...")
                        continue
                    row_text += cell.text
                    row_chars.extend(cell.raw_cell["chars"])
                logger.debug(f"<cell_partial_text>: {row_text=}")
                vmsp_input = VMSPInput.from_cell({"text": row_text, "chars": row_chars}, element)
                for column in self.columns:
                    logger.debug(f"<cell_partial_text>: {column=}, {row_text=}")
                    column_answer_result = self.extract_for_column(element, column, predicted_columns, vmsp_input)
                    if column_answer_result:
                        answer_result.update(column_answer_result)
        # 答案换行了，需要进行处理
        # |律所住所-field|
        # |--------|
        # |住所：广东省广州市天河区珠江新城珠江东路6号广州周大福金融中心（广州东塔）29|
        # |层，30层|
        # |负责人: .......|
        if not answer_result and self.merge_row:
            for idx, item in enumerate(items):
                row_chars = []
                next_idx = idx + 1
                if len(items) > next_idx and self.is_mergeable(items[next_idx]):
                    row_text = "".join([cell.text for cell in item]) + "".join([cell.text for cell in items[next_idx]])
                    row_chars.extend(*[cell.raw_cell["chars"] for cell in item])
                    row_chars.extend(*[cell.raw_cell["chars"] for cell in items[next_idx]])
                    vmsp_input = VMSPInput.from_cell({"text": row_text, "chars": row_chars}, element)
                    for column in self.columns:
                        column_answer_result = self.extract_for_column(element, column, predicted_columns, vmsp_input)
                        if column_answer_result:
                            answer_result.update(column_answer_result)
                            return answer_result
        return answer_result

    def extract_by_model(self, column, element, vmsp_input, split_pattern, keep_separator, neglect_answer_patterns):
        element_results = []
        model_data = self.get_model_data(column=column)
        if not model_data:
            logger.debug("<cell_partial_text>: no model exists, return!!!")
            return element_results
        use_answer_pattern = self.get_config("use_answer_pattern", default=True, column=column)
        need_match_length = self.get_config("need_match_length", default=True, column=column)
        answer_items = VMSP.extract_answers(vmsp_input, model_data, use_answer_pattern, need_match_length)
        logger.debug(f"<cell_partial_text>: extract_answers by VMSP, length of answer items: {len(answer_items)}")
        for item in answer_items:
            chars = vmsp_input.chars[item.start : item.end]
            if not chars:
                continue
            element_results.extend(self.create_content_result(element, chars, split_pattern, keep_separator))
            if not self.multi:
                break
        return element_results

    def extract_feature(self, attr, dataset: list[DatasetItem], workers=None):
        answer_texts_list = []

        for item in dataset:
            elements = item.data["elements"]
            col_path = self.schema.sibling_path(attr)
            nodes = self.find_answer_nodes(item, col_path)
            for node in nodes:
                if not node.data or not node.data["data"]:
                    continue
                for data in node.data["data"]:
                    for box in data["boxes"]:
                        cell_para = {}
                        box_relative_elements = self.select_elements(elements.values(), box)
                        if not box_relative_elements:
                            continue
                        box_element = box_relative_elements[0]
                        if ElementClassifier.like_paragraph(box_element):
                            continue
                        table = parse_table(box_element, tabletype=TableType.TUPLE.value)
                        for row in table.rows:
                            for cell in row:
                                if self.same_box(cell.raw_cell, box):
                                    cell_para = cell.raw_cell
                                    break
                            if cell_para:
                                break
                        content = clean_txt("".join([box.get("text", "") for box in data["boxes"]]))
                        if cell_para and content in clean_txt(cell_para.get("text", "")):  # 完整句子被切分的情况
                            text_parts = self.get_answer_text_parts(cell_para, data["boxes"])
                            if not text_parts[1]:
                                continue
                            answer_texts = [[PatternString(t) for t in text_parts]]
                            answer_texts_list.extend(answer_texts)

        answers_groupby_boundary = generate_answer_boundary(answer_texts_list)
        features = run_in_multiprocess(
            extract_feature_by_group, list(answers_groupby_boundary), workers=workers, maxtasksperchild=10
        )
        return sorted(features, key=lambda f: f["score"], reverse=True)

    @staticmethod
    def get_answer_text_parts(para, answer_boxes):
        left_chars = []
        answer_chars = []
        right_chars = []
        for char in para.get("chars", []):
            if not any(PdfinsightReader.box_in_box(char["box"], box["box"]) for box in answer_boxes):
                if not answer_chars:
                    left_chars.append(char)
                else:
                    right_chars.append(char)
            else:
                answer_chars.append(char)

        left, answer, right = [
            "".join([c["text"] for c in chars]).strip() for chars in (left_chars, answer_chars, right_chars)
        ]
        return left, answer, right


class KvPartialText(CellPartialText):
    @property
    def multi_rows(self):
        return self.get_config("multi_rows", True)

    @property
    def column_from_multi_rows(self):
        return self.get_config("column_from_multi_rows", False)

    @property
    def skip_dummy(self):
        return self.get_config("skip_dummy", False)

    def extract_by_element(self, element, predicted_columns):
        answer_result = defaultdict(list)
        table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
        logger.debug(f"<kv_partial_text>: {element['index']=}")
        for row in table.rows:
            row_texts = ""
            row_chars = []
            for cell in row:
                if self.skip_dummy and cell.dummy:
                    continue
                row_chars.extend(cell.raw_cell["chars"])
                row_texts += cell.text
            fake_cell = {
                "text": row_texts,
                "chars": row_chars,
            }
            vmsp_input = VMSPInput.from_cell(fake_cell, element)
            for column in self.columns:
                logger.debug(f"<kv_partial_text>: {column=}, {row_texts=}")
                column_answer_result = self.extract_for_column(element, column, predicted_columns, vmsp_input)
                if not column_answer_result:
                    continue
                if self.column_from_multi_rows:
                    answer_result[column].extend(column_answer_result[column])
                else:
                    answer_result.update(column_answer_result)
            if not self.multi_rows and answer_result:
                break
        return answer_result

    def extract_feature(self, attr, dataset: list[DatasetItem], workers=None):
        answer_texts_list = []

        for item in dataset:
            elements = item.data["elements"]
            col_path = self.schema.sibling_path(attr)
            nodes = self.find_answer_nodes(item, col_path)
            for node in nodes:
                if not node.data or not node.data["data"]:
                    continue
                for data in node.data["data"]:
                    for box in data["boxes"]:
                        box_relative_elements = self.select_elements(elements.values(), box)
                        if not box_relative_elements:
                            continue
                        box_element = box_relative_elements[0]
                        if ElementClassifier.like_paragraph(box_element):
                            continue
                        table = parse_table(box_element, tabletype=TableType.TUPLE.value)
                        answer_row_data = {}
                        for row in table.rows:
                            if any(cell for cell in row if self.same_box(cell.raw_cell, box)):
                                row_texts = ""
                                row_chars = []
                                for cell in row:
                                    row_chars.extend(cell.raw_cell["chars"])
                                    row_texts += cell.text
                                answer_row_data = {
                                    "text": row_texts,
                                    "chars": row_chars,
                                }
                                break

                        content = clean_txt("".join([box.get("text", "") for box in data["boxes"]]))
                        if answer_row_data and content in clean_txt(
                            answer_row_data.get("text", "")
                        ):  # 完整句子被切分的情况
                            text_parts = self.get_answer_text_parts(answer_row_data, data["boxes"])
                            if not text_parts[1]:
                                continue
                            answer_texts = [[PatternString(t) for t in text_parts]]
                            answer_texts_list.extend(answer_texts)

        answers_groupby_boundary = generate_answer_boundary(answer_texts_list)
        features = run_in_multiprocess(
            extract_feature_by_group, list(answers_groupby_boundary), workers=workers, maxtasksperchild=10
        )
        return sorted(features, key=lambda f: f["score"], reverse=True)
