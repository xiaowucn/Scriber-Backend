from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.dataset import DatasetItem
from remarkable.predictor.models.row_match import RowMatch
from remarkable.predictor.schema_answer import PredictorResult


def compute_tab_len(char: dict, cell_box: tuple) -> tuple:
    # 计算行首字符距离外框 缩进距离 或 无缩进
    tabulation = char["box"][0] - cell_box[0]
    font_width = char["box"][2] - char["box"][0]
    if tabulation < font_width:
        return 0, font_width
    return tabulation, font_width


def get_compare_data(start_char: dict) -> tuple:
    return start_char["page"], start_char["box"][-1]  # 当前页 下边界


def split_cell_chars(chars: list[dict], outline: tuple | list) -> list[list[dict]]:
    if len(chars) < 3:
        return [chars]
    res = []
    start_char = chars[0]
    current_segment = [start_char]
    tabulation, font_width = compute_tab_len(start_char, outline)
    current_page, bottom_threshold = get_compare_data(start_char)  # 当前页 下边界

    for char_info in chars[1:]:
        if char_info["page"] > current_page:  # 换页
            current_page, bottom_threshold = get_compare_data(char_info)
        if char_info["box"][1] > bottom_threshold:  # 顶部大于上一行底部
            bottom_threshold = char_info["box"][-1]  # 重置行下边界
            char_tabulation, _ = compute_tab_len(char_info, outline)
            if 0 < tabulation < char_tabulation + 2 and char_tabulation < tabulation + 2:
                # 和首行缩进相近 误差系数小于2
                res.append(current_segment)
                current_segment = [char_info]
                continue
        current_segment.append(char_info)
    res.append(current_segment)
    return res


class CellItems(RowMatch):
    def __init__(self, options, schema, predictor=None):
        super().__init__(options, schema, predictor=predictor)

    def extract_feature(self, elements, answer):
        pass

    def train(self, dataset: list[DatasetItem], **kwargs):
        pass

    def matched_row(self, table_rows, column):
        rows = []
        pattern = PatternCollection(self.get_config("key_pattern", column=column))
        neglect_row_pattern = PatternCollection(self.get_config("neglect_row_pattern", column=column))
        for row in table_rows:
            if self.merge_row:
                neglect_matcher = False
                row_texts = "".join([clean_txt(cell.text) for cell in row if not cell.dummy or self.keep_dummy])
                matcher = pattern.nexts(row_texts)
                if matcher and neglect_row_pattern.patterns:
                    neglect_matcher = neglect_row_pattern.nexts(row_texts)
                if matcher and not neglect_matcher:
                    rows.append(row)
            else:
                row_texts = {clean_txt(cell.text) for cell in row if not cell.dummy}
                for row_text in row_texts:
                    if pattern.nexts(row_text):
                        rows.append(row)
        return rows

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        answer_results = []
        for element in elements:
            if element["class"] != "TABLE":
                continue
            answer_result = {}
            table = parse_table(
                element,
                tabletype=TableType.TUPLE.value,
                pdfinsight_reader=self.pdfinsight,
                width_from_all_rows=self.width_from_all_rows,
            )
            for column in self.columns:
                element_results = []
                split_pattern = self.get_config("split_pattern", column=column)
                sub_start_end = self.get_config("sub_start_end")
                valid_rows = self.matched_row(table.rows, column)
                for valid_row in valid_rows:
                    cell = valid_row[-1]
                    chars_lines = split_cell_chars(cell.raw_cell["chars"], cell.outline)[
                        sub_start_end[0] : sub_start_end[1]
                    ]
                    for chars_line in chars_lines:
                        fix_chras = []
                        exist_split = False
                        for char in chars_line:
                            if exist_split:
                                fix_chras.append(char)
                            if char["text"] in split_pattern:
                                exist_split = True
                        if exist_split:
                            chars_line = fix_chras
                        element_results.extend(self.create_content_result(element, chars_line, [cell], None))
                    if not self.multi:
                        break
                if element_results:
                    answer_result[column] = [self.create_result(element_results, column=column)]
            if answer_result:
                answer_results.append(answer_result)
            if answer_results and not self.multi_elements:
                break
        return answer_results
