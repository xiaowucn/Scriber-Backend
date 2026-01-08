from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.base_model import TableModel


class RowMatch(TableModel):
    """
    类似于para_match
    先根据row_pattern定位到row
    再获取content_patterns获取具体答案
    """

    def extract_feature(self, elements, answer):
        pass

    def train(self, dataset, **kwargs):
        pass

    @property
    def merge_row(self):
        return self.get_config("merge_row", True)  # 将一行的cell合并,cell.text拼接起来

    @property
    def keep_first_dummy_cell(self):
        return self.get_config("keep_first_dummy_cell", False)

    @property
    def width_from_all_rows(self):
        return self.get_config("width_from_all_rows", False)  # 默认取表格第一行宽度, 为True时取最宽的行

    @property
    def multi_answer_in_one_cell(self):
        return self.get_config("multi_answer_in_one_cell", False)  # 一个单元格内提取多个答案

    @property
    def merge_char_result(self):  # 一个element里提取的element_results合并创建一个PredictorResult
        return self.get_config("merge_char_result", True)

    def predict_schema_answer(self, elements):
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
                content_pattern = PatternCollection(self.get_config("content_pattern", column=column))
                split_pattern = self.get_config("split_pattern", column=column)
                keep_separator = self.get_config("keep_separator", column=column)

                valid_rows = self.get_valid_rows(table, column)
                for valid_row in valid_rows:
                    if self.merge_row:
                        dst_chars_list, cells = self.get_answer_from_merge_row(
                            content_pattern,
                            valid_row,
                            self.keep_first_dummy_cell,
                            self.multi_answer_in_one_cell,
                            self.keep_dummy,
                        )
                        if not dst_chars_list:
                            continue
                        for dst_chars in dst_chars_list:
                            element_results.extend(
                                self.create_content_result(
                                    element, dst_chars, cells, split_pattern, keep_separator=keep_separator
                                )
                            )
                    else:
                        cells = self.get_answer_cells(content_pattern, valid_row)
                        if not cells:
                            continue
                        for cell in cells:
                            dst_chars = self.get_dst_chars_from_pattern(content_pattern, cell=cell)
                            element_result = self.create_content_result(
                                element, dst_chars, [cell], split_pattern, keep_separator=keep_separator
                            )
                            element_results.extend(element_result)
                    if not self.multi:
                        break
                if element_results:
                    if self.merge_char_result:
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

    @classmethod
    def get_answer_from_merge_row(
        cls, pattern, row, keep_first_dummy_cell=False, multi_answer_in_one_cell=False, keep_dummy=False
    ):
        row_texts = "".join([clean_txt(cell.text) for cell in row if not cell.dummy or keep_dummy])
        matchers = list(pattern.finditer(clean_txt(row_texts)))

        first_dummy_cell_matcher = None
        if not matchers:
            first_cell = row[0]
            if keep_first_dummy_cell and first_cell.dummy:
                if not (first_dummy_cell_matcher := pattern.nexts(clean_txt(first_cell.text))):
                    return None, None
            else:
                return None, None
        if first_dummy_cell_matcher:
            matchers = [first_dummy_cell_matcher]
        dst_chars_list = []
        dst_cells = []
        for matcher in matchers:
            row_chars = []
            for idx, cell in enumerate(row):
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1413
                # 需要第一个单元格做判断，但第一个单元格是dummy,因此需要特殊处理
                if keep_first_dummy_cell and idx == 0 and first_dummy_cell_matcher:
                    row_chars.extend(cell.raw_cell["chars"])
                elif cell.dummy and not keep_dummy:
                    continue
                else:
                    row_chars.extend(cell.raw_cell["chars"])
            fake_element = {
                "text": "".join(i["text"] for i in row_chars),
                "chars": row_chars,
            }
            dst_chars = cls.get_dst_chars_from_matcher(matcher, fake_element)
            if not dst_chars:
                return None, None
            dst_chars_list.append(dst_chars)

            dst_texts = matcher.groupdict().get("dst", None)
            for cell in row:
                cell_text = clean_txt(cell.text)
                if cell_text and cell_text in dst_texts:
                    dst_cells.append(cell)
            if not multi_answer_in_one_cell:
                break
        return dst_chars_list, dst_cells

    def get_answer_cells(self, pattern, table_row):
        cells = []
        for cell in table_row:
            matcher = pattern.nexts(clean_txt(cell.text))
            if matcher and matcher.group() not in list(self.get_config("row_pattern")):
                cells.append(cell)
                if not self.multi:
                    break
        return cells

    def get_valid_rows(self, table, column):
        valid_rows = table.rows
        _valid_rows = []
        top_anchor_range_patterns = PatternCollection(self.get_config("top_anchor_range_patterns", column=column))
        bottom_anchor_range_patterns = PatternCollection(self.get_config("bottom_anchor_range_patterns", column=column))
        if top_anchor_range_patterns or bottom_anchor_range_patterns:
            start = False
            for row in table.rows:
                row_text = "".join([clean_txt(cell.text) for cell in row if not cell.dummy or self.keep_dummy])
                if not start and top_anchor_range_patterns.nexts(row_text):
                    start = True
                    _valid_rows.append(row)
                    continue
                if start:
                    _valid_rows.append(row)
                    if bottom_anchor_range_patterns.nexts(row_text):
                        break
            valid_rows = _valid_rows

        matched_rows = self.matched_row(valid_rows, column)
        return matched_rows

    def matched_row(self, table_rows, column):
        pattern = PatternCollection(self.get_config("row_pattern", column=column))
        neglect_row_pattern = PatternCollection(self.get_config("neglect_row_pattern", column=column))
        rows = []
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

    def get_dst_chars_from_pattern(self, pattern, cell):
        dst_chars = cell.raw_cell["chars"]
        if pattern:
            matcher = pattern.nexts(clean_txt(cell.text))
            if matcher:
                dst_chars = self.get_dst_chars_from_matcher(matcher, cell.raw_cell)

        return dst_chars
