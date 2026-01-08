from contextlib import suppress
from copy import deepcopy

from remarkable.common.pattern import PatternCollection
from remarkable.pdfinsight.reader import PdfinsightTable
from remarkable.predictor.ecitic_predictor.models.scope_investment import KeyValueTableSplitter


def calculate_bounding_box(chars, page: int):
    if not chars:
        return [0, 0, 0, 0]
    min_left, min_top, max_right, max_bottom = chars[0]["box"]
    for char in chars[1:]:
        if char["page"] > page:
            break
        char_box = char["box"]
        if char_box[0] < min_left:
            min_left = char_box[0]
        if char_box[1] < min_top:
            min_top = char_box[1]
        if char_box[2] > max_right:
            max_right = char_box[2]
        if char_box[3] > max_bottom:
            max_bottom = char_box[3]

    return [min_left, min_top, max_right, max_bottom]


def get_previous_row_chars(key_chars, value_chars):
    if not key_chars:
        return None
    page = key_chars[0]["page"]
    top_index = 1
    bottom_index = 3

    key_cell_box = calculate_bounding_box(key_chars, page)
    top = key_cell_box[top_index]
    chars = []
    for idx, char in enumerate(value_chars):
        if char["page"] > page:
            break

        bottom = char["box"][bottom_index]
        if bottom < top:
            chars.append((idx, char))

    return chars


def get_next_index(cells):
    return max(int(key) for key in cells)


def add_cell_chars(target_cell, source_element, chars=None):
    max_index = len(target_cell["chars"])
    add_count = 0
    chinese_chars = set(source_element["chinese_chars"])
    english_chars = set(source_element["english_chars"])
    remove_indices = set()
    chars = chars or enumerate(source_element["chars"])
    for idx, char in chars:
        with suppress(IndexError):
            target_cell["chars"].append(char)
            current_index = max_index + add_count
            if idx in chinese_chars:
                target_cell["chinese_chars"].append(current_index)
            elif idx in english_chars:
                target_cell["english_chars"].append(current_index)
            else:
                pass
            target_cell["text"] += char["text"]
            add_count += 1
            remove_indices.add(idx)

    return remove_indices


class TradingExchangeFromMergedTableKV(KeyValueTableSplitter):
    __name__ = "trading_exchange_from_merged_kv"
    P_PREFIX = PatternCollection(r"指")
    P_EXCLUDE_SENTENCE_TEXT = PatternCollection([r"国务院或"])
    P_SYLLABUS = PatternCollection(
        [
            r"^[一二三四五六七八九十]+[、]",
        ]
    )

    def fix_previous_row_chars(self, key_cell, value_cell, previous_row):
        key_chars = key_cell["chars"]
        value_chars = value_cell["chars"]

        char_items = get_previous_row_chars(key_chars, value_chars)
        if char_items:
            previous_value_cell = previous_row[1]
            remove_indices = add_cell_chars(previous_value_cell, value_cell, char_items)

            new_chars = [char for idx, char in enumerate(value_chars) if idx not in remove_indices]
            value_cell["chars"] = new_chars
            value_cell["text"] = "".join(char["text"] for char in value_cell["chars"])

        return value_cell["chars"]

    def format_table_element(self, origin_element):
        element = deepcopy(origin_element)
        feature_white_list = self.config.get("table_config", {}).get("feature_white_list")
        element = super().format_table_element(element)
        # if not element.get("continued"):
        #     return element

        tbl = PdfinsightTable(element)
        fake_row = [
            {"chars": [], "chinese_chars": [], "english_chars": [], "text": ""},
            {"chars": [], "chinese_chars": [], "english_chars": [], "text": ""},
        ]
        last_independent_row = None
        for row in tbl.sorted_rows():
            key_cell = row[0]
            key_chars = key_cell["chars"]
            value_cell = row[-1]  # 存在dummy cell时, row的长度可能超过2
            if not key_chars:  # row_index为0时,可能并不是整个表格的首行,而是表格中间部分被识别成了段落
                continue

            previous_row = last_independent_row or fake_row

            value_cell_chars = self.fix_previous_row_chars(key_cell, value_cell, previous_row)
            if value_cell_chars:  # 修正完后,当前行的value_cell仍然保留有chars
                last_independent_row = row

        merged_table = element.get("page_merged_table")
        if merged_table:
            start_index = get_next_index(merged_table["cells_idx"])
            for next_index in range(start_index + 1, start_index + 100):
                ele_typ, _next_element = self.pdfinsight.find_element_by_index(next_index)
                if not _next_element:
                    break
                next_element = deepcopy(_next_element)
                if ele_typ == "PARAGRAPH":
                    if not next_element["text"]:
                        continue
                    if self.P_SYLLABUS.nexts(next_element["text"]):
                        continue
                    if abs(next_element["outline"][0] - value_cell["box"][0]) < 5:
                        add_cell_chars(value_cell, next_element)
                    else:
                        break
                elif ele_typ == "TABLE":
                    next_tbl = PdfinsightTable(next_element)

                    first_row = next_tbl.sorted_rows()[0]
                    if first_row[0]["chars"]:
                        self.fix_previous_row_chars(first_row[0], first_row[-1], previous_row=tbl.sorted_rows()[-1])

                    for row in next_tbl.sorted_rows():
                        non_empty_cells = [cell for cell in row if cell["text"]]
                        if not non_empty_cells:
                            break
                        first_cell = non_empty_cells[0]
                        if abs(first_cell["box"][0] - value_cell["box"][0]) < 5:
                            for cell in non_empty_cells:
                                add_cell_chars(value_cell, cell)
                        else:
                            break
                    break

        if merged_table and feature_white_list:  # 根据已知的特征，尝试修复跨页表格
            feature_white_list = PatternCollection(feature_white_list)
            table_index_list = list(merged_table["cells_idx"])
            for index in range(len(table_index_list) - 1):
                table_0 = merged_table["cells_idx"][table_index_list[index]]
                table_1 = merged_table["cells_idx"][table_index_list[index + 1]]
                max_row_0 = max(int(x.split("_")[0]) for x in table_0)
                min_row_1 = min(int(x.split("_")[0]) for x in table_1)
                key_cell_0 = tbl.sorted_rows()[max_row_0][0]
                key_cell_1 = tbl.sorted_rows()[min_row_1][0]
                if feature_white_list.nexts(key_cell_0["text"]) or feature_white_list.nexts(key_cell_1["text"]):
                    continue
                if feature_white_list.nexts(key_cell_0["text"] + key_cell_1["text"]):
                    value_cell_0 = tbl.sorted_rows()[max_row_0][1]
                    value_cell_1 = tbl.sorted_rows()[min_row_1][1]
                    key_cell_0["text"] += key_cell_1["text"]
                    key_cell_0["chars"] += key_cell_1["chars"]
                    value_cell_0["text"] += value_cell_1["text"]
                    value_cell_0["chars"] += value_cell_1["chars"]

        return element
