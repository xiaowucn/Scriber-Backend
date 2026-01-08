"""Key-Value 形式的表格
表格解析方法：每两个格子组成 pair， 左 key 右 value
模型：统计字段对应的 key
特殊情况：暂无

model 示意:
{
    "attr1": Counter({
        "key_1": 100,
        "key_2": 60,
        ...
    }),
    ...
}

注：带大表格的先不用实现，只取定位大表格即可
"""

import re
from collections import Counter, defaultdict
from copy import deepcopy

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import ParsedTable, ParsedTableCell, parse_table
from remarkable.pdfinsight.reader import PdfinsightTable
from remarkable.predictor.models.base_model import TableModel
from remarkable.predictor.schema_answer import PredictorResult

INVALID_HEADER_PATTERN = PatternCollection([r"序号"])
INVALID_CELL_PATTERN = PatternCollection([r"^[:：指]$"])
SPLIT_ONE_COLUMN_TABLE = re.compile(r"[:：]")


class KeyValueTable(TableModel):
    __name__ = "table_kv"
    filter_elements_by_target = True

    model_intro = {
        "doc": """
        多个信息项以表格列示，如发行人-值，注册地址-值
        """,
        "name": "多个信息项列示表",
    }

    def __init__(self, options, schema, predictor=None):
        super().__init__(options, schema, predictor=predictor)
        self.only_matched_value = self.get_config("only_matched_value")  # value是否必须匹配regs
        self.split_single_column_table = self.get_config(
            "split_single_column_table", False
        )  # 尝试拆分单列表,需搭配regs
        self.width_from_all_rows = self.get_config(
            "width_from_all_rows", False
        )  # 默认取表格第一行宽度, 为True时取最宽的行
        self.multi_answer_in_one_cell = self.get_config("multi_answer_in_one_cell", False)  # 一个单元格内提取多个答案
        self.merge_same_key_pairs = self.get_config(
            "merge_same_key_pairs", False
        )  # 将同一key的pairs合并(需multi为True)
        self.skip_empty_cell = self.get_config("skip_empty_cell", False)
        self.deduplicate_by_cell = self.get_config("deduplicate_by_cell", True)
        self.merge_cell_result = self.get_config("merge_cell_result", True)
        self.col_num = self.get_config("col_num", default=None)

    def get_model_data(self, column=None):
        # todo remove to parent class
        model_data = super().get_model_data(column=column) or Counter()

        # blacklist
        blacklist = self.get_config("feature_black_list", default=[], column=column)
        blacklist_features = [k for k in model_data if any(self.is_match(b, k) for b in blacklist)]
        for bfeature in blacklist_features:
            model_data.pop(bfeature)

        # whitelist
        for feature in self.get_config("feature_white_list", default=[], column=column):
            if feature not in model_data:
                model_data[feature] = max(model_data.values()) + 1 if model_data else 1

        return model_data

    def format_table_element(self, element):
        return regroup_table_element(element)

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        answer_results = []
        elements = self.revise_elements(elements)

        for element in elements:
            if element["class"] != "TABLE":
                # AutoModel中 filter_elements_by_target设置为None 所有这里需要再次过滤下
                continue
            answer_result = {}
            element = self.format_table_element(element)
            table = parse_table(
                element,
                tabletype=TableType.KV.value,
                pdfinsight_reader=self.pdfinsight,
                width_from_all_rows=self.width_from_all_rows,
            )
            if self.col_num and self.col_num != len(table.cols):
                continue
            left_and_right_pairs = self.parse_kv_pairs(table, direction="left_and_right")
            up_and_down_pairs = self.parse_kv_pairs(table, direction="up_and_down")

            for column in self.columns:
                kv_directions = self.get_config("kv_directions", column=column, default=["left_and_right"])
                kv_pairs = []
                for direction in kv_directions:
                    if direction == "left_and_right":
                        kv_pairs.extend(left_and_right_pairs)
                    elif direction == "up_and_down":
                        kv_pairs.extend(up_and_down_pairs)

                element_results = []
                # TODO: 这里有个问题, 子节点应该用自己的初步定位 element, 而不是父节点的
                # elements = self.predictor.get_candidate_elements([self.schema.parent.name, column])
                pattern = self.get_config("regs", column=column)  # 根据key提取到value后,再尝试根据正则提
                neglect_pattern = self.get_config("neglect_regs", column=column)
                neglect_row = PatternCollection(self.get_config("neglect_row", column=column))

                split_pattern = self.get_config("split_pattern", column=column)
                model_data = self.get_model_data(column=column)
                if not model_data:
                    continue
                used_pairs = set()
                for key, _ in model_data.most_common():
                    pairs = self.find_kv_pairs(kv_pairs, key, findby="key", mode="text")
                    for pair in pairs:
                        cell = pair[1]
                        row_text = table.get_row_text(cell.rowidx)
                        if neglect_row.nexts(row_text):
                            continue

                        cleaned_cell_text = clean_txt(cell.text)
                        if not cleaned_cell_text:
                            continue
                        if self.deduplicate_by_cell and cleaned_cell_text in used_pairs:
                            continue

                        if neglect_pattern:
                            if PatternCollection(neglect_pattern).nexts(cleaned_cell_text) or PatternCollection(
                                neglect_pattern
                            ).nexts(clean_txt(pair[0].text)):
                                continue
                        if pattern:
                            matchers = list(PatternCollection(pattern).finditer(cleaned_cell_text))
                            if not matchers:
                                if self.only_matched_value:
                                    continue
                                element_results.extend(
                                    self.create_content_result(element, cell.raw_cell["chars"], [cell], split_pattern)
                                )
                                used_pairs.add(cleaned_cell_text)
                            else:
                                answer_for_cell = []
                                for matcher in matchers:
                                    dst_chars = self.get_dst_chars_from_matcher(matcher, cell.raw_cell)
                                    if not dst_chars:
                                        continue
                                    answer_for_cell.extend(
                                        self.create_content_result(element, dst_chars, [cell], split_pattern)
                                    )
                                    used_pairs.add(cleaned_cell_text)

                                    if answer_for_cell and not self.multi_answer_in_one_cell:
                                        break
                                if answer_for_cell:
                                    element_results.extend(answer_for_cell)
                        else:
                            element_results.extend(
                                self.create_content_result(element, cell.raw_cell["chars"], [cell], split_pattern)
                            )
                            used_pairs.add(cleaned_cell_text)
                        if element_results and not self.multi:
                            break
                    if element_results and not self.multi:
                        break
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4125#note_486363
                # 当有空列时(表格识别问题，多了一个空列), 认为没有匹配到内容，不能作为答案
                if element_results and all(r.chars for r in element_results):
                    if len(element_results) > 1:
                        # 按照单元格的顺序 从上到下 从左到右排序
                        element_results.sort(
                            key=lambda x: (int(x.cells[0].split("_")[0]), int(x.cells[0].split("_")[1]))
                        )
                    if self.merge_cell_result:
                        answer_result[column] = [self.create_result(element_results, column=column)]
                    else:
                        answer_result[column] = []
                        for element_result in element_results:
                            answer_result[column].append(self.create_result([element_result], column=column))

            if answer_result:
                answer_results.append(answer_result)
            if answer_results and not self.multi_elements:
                break
        return answer_results

    def extract_feature(self, elements, answer):
        features = Counter()
        for answer_data in answer["data"]:
            if not answer_data["boxes"]:
                continue
            box = answer_data["boxes"][0]  # TODO:
            for eid in answer_data["elements"]:
                element = elements.get(eid)
                if not self.is_target_element(element):
                    continue
                element = regroup_table_element(element)
                table = parse_table(element, tabletype=TableType.KV.value)
                kv_pairs = self.parse_kv_pairs(table)
                pairs = self.find_kv_pairs(kv_pairs, box, findby="value", mode="box")
                for pair in pairs:
                    features.update([clean_txt(pair[0].text)])
        return features

    def parse_kv_pairs(
        self, table: ParsedTable, direction: str = "left_and_right"
    ) -> list[tuple[ParsedTableCell, ParsedTableCell]]:
        """将表格相邻两个单元格解析成键值对
        | key1 | value1 | key2 | value2 |
        """
        kv_pairs = []
        if direction == "left_and_right":
            rows_list = [self.fix_table_rows(table)]
        elif direction == "up_and_down":
            rows_list = [table.cols, [x[1:] for x in table.cols]]
        else:
            raise ValueError(f"direction {direction} not supported")

        for rows in rows_list:
            for row in rows:
                # 大于两列时忽略合并单元格 这里应该忽略的是跨列的单元格，而不应忽略跨行的单元格
                # 这里可以根据PDFinsight element里的merged信息来判断
                # 但PDFinsight在处理跨页的表格时，表格开头的元素块中的merged信息可能为空 暂时没有加上面的逻辑  todo
                cells = []
                if len(row) > 2:
                    for c in row:
                        if c.dummy and not self.keep_dummy:
                            continue
                        if self.skip_empty_cell and not c.text:
                            continue
                        cells.append(c)
                else:
                    cells = row
                cells = [c for idx, c in enumerate(cells) if is_valid_cell(idx, c)]
                kv_pairs.extend(zip(cells[0::2], cells[1::2]))
        return kv_pairs

    def fix_table_rows(self, table: ParsedTable) -> list[list[ParsedTableCell]]:
        if self.split_single_column_table:
            rows = self.split_one_column_table(table)
            return rows
        return table.rows

    @staticmethod
    def split_one_column_table(table: ParsedTable) -> list[list[ParsedTableCell]]:
        if len(table.cols) != 1:
            return table.rows
        rows = []
        for row in table.rows:
            if not row:
                return table.rows
            split_ret = SPLIT_ONE_COLUMN_TABLE.split(row[0].text)
            if len(split_ret) != 2:
                return table.rows
            rows.append(row * 2)

        return rows

    def find_kv_pairs(
        self, kv_pairs: list[tuple[ParsedTableCell, ParsedTableCell]], feature, findby="key", mode="text"
    ):
        """根据单元格的 text 或者 box 查找对应的 kv_pair"""

        def same_text(cell: ParsedTableCell, feature):
            if "__regex__" in feature:
                pattern = [item for item in feature.split("__regex__") if item]
                return PatternCollection(pattern).nexts(clean_txt(cell.text))
            return clean_txt(cell.text) == clean_txt(feature)

        findidx = 0 if findby == "key" else 1
        pairs = defaultdict(list)
        for pair in kv_pairs:
            cell = pair[findidx]
            if mode == "text" and same_text(cell, feature):
                pairs[pair[0].text].append(pair)
            elif mode == "box" and self.same_box(cell.raw_cell, feature):
                pairs[pair[0].text].append(pair)
        ret = []
        for items in pairs.values():
            if self.multi:
                if self.merge_same_key_pairs:
                    ret.append(merge_same_key_cells(items))
                else:
                    ret.extend(items)
            elif items:
                ret.extend(items[-1:])  # 仅仅保留最后一个
        return ret


def merge_same_key_cells(pair_values):
    pair_key = deepcopy(pair_values[0][0])
    pair_value = deepcopy(pair_values[0][1])
    for item in pair_values[1:]:
        pair_value.raw_cell["chars"].extend(item[1].raw_cell["chars"])
        pair_value.raw_cell["text"] += item[1].raw_cell["text"]
        pair_value.text += item[1].text

    return pair_key, pair_value


def has_invalid_header(cell):
    for header in cell.col_header_cells:
        if INVALID_HEADER_PATTERN.nexts(clean_txt(header.text)):
            return True
    return False


def is_valid_cell(idx, cell):
    if idx == 0 and not cell.text:
        return False
    if has_invalid_header(cell):
        return False
    # if cell.text.isdigit():
    #     return False
    if INVALID_CELL_PATTERN.nexts(clean_txt(cell.text)):
        return False
    return True


def regroup_table_element(element):
    """尝试将可能合并的单元格分割开，重组成新的元素块"""
    ret_elt = deepcopy(element)
    tbl = PdfinsightTable(element)
    for _, row in tbl.cells.items():
        cells = [c for cidx, c in sorted(row.items()) if not c.get("dummy")]
        for cell in split_cell(cells):
            ret_elt["cells"][cell["index"]] = deepcopy(cell)
    return ret_elt


def split_cell(cells):
    """将可能的合并单元格拆成两个单元格，暂用冒号做拆分依据。确保不符合条件返回空列表，以防止在`regroup_table_element`中的 deepcopy 失效。"""
    pattern = re.compile(r":|：")
    if len(cells) != 1:
        return []
    cell = cells[0]
    if cell["right"] - cell["left"] < 2 or len(pattern.split(cell["text"])) != 2:
        # 只考虑列向合并的情况
        return []
    ret_cells = []
    virtual_cell = {
        "styles": cell["styles"],
        "box": [],
        "text": "",
        "chars": [],
        "page": cell["page"],
        "styles_diff": cell["styles_diff"],
        "left": 0,
        "right": 1,
        "top": cell["top"],
        "bottom": cell["bottom"],
        "index": f"{cell['index'].split('_')[0]}_0",
    }
    for char in cell["chars"]:
        if pattern.search(char["text"]):
            ret_cells.append(deepcopy(virtual_cell))
            virtual_cell.update(
                {"box": [], "text": "", "chars": [], "left": 1, "right": 2, "index": f"{cell['index'].split('_')[0]}_1"}
            )
        else:
            virtual_cell["box"] = expand_box(virtual_cell["box"], char["box"][::])
            virtual_cell["text"] += char["text"]
            virtual_cell["chars"].append(char)
    ret_cells.append(virtual_cell)
    return ret_cells


def expand_box(origin_box, new_box):
    if not origin_box:
        return new_box
    left_top_x = min(origin_box[0], new_box[0])
    left_top_y = min(origin_box[1], new_box[1])
    right_bottom_x = max(origin_box[2], new_box[2])
    right_bottom_y = max(origin_box[3], new_box[3])
    return [left_top_x, left_top_y, right_bottom_x, right_bottom_y]
