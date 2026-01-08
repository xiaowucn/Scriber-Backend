from collections import defaultdict
from copy import deepcopy
from itertools import chain

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.models.table_row import TableRow
from remarkable.predictor.schema_answer import PredictorResult


class TableSubscription(TableRow):
    __name__ = "table_subscription"

    def __init__(self, options, schema, predictor=None):
        super().__init__(options, schema, predictor=predictor)

    @property
    def multi_elements(self):
        return self.get_config("multi_elements", True)

    def header_patterns(self, column):
        return PatternCollection(self.get_config("header_patterns", [], column))

    @property
    def main_column(self):
        return self.get_config("main_column", "")

    @property
    def main_column_by_cell_regs(self):
        return self.get_config("main_column_by_cell_regs", False)

    @property
    def secondary_column(self):
        return self.get_config("secondary_column", "")

    @property
    def splits(self):
        return PatternCollection(self.get_config("splits"))

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        group_answers = []
        elements = self.revise_elements(elements)
        if self.multi_elements:
            elements.sort(key=lambda x: x["index"])

        for element in elements:
            if element["class"] != "TABLE":
                continue
            table = self.prepare_table(element)
            if not table:
                continue

            tag_index = 0  # 0: main_column是 列头 1: main_column 是横头
            for row in table.rows:
                main_cell = None
                for cell in row:
                    if self.header_patterns(self.main_column).nexts(clean_txt(cell.text)):
                        main_cell = cell
                        break
                if main_cell:
                    break
                tag_index += 1
            items = table.cols if tag_index == 0 else table.rows
            for item in items:
                main_column_result, secondary_column_result = None, None
                for cell in item:
                    cell_clean_txt = clean_txt(cell.text)
                    if self.header_patterns(self.main_column).nexts(cell_clean_txt):
                        if (
                            main_matcher := self.cell_regs[self.main_column].nexts(cell_clean_txt)
                        ) and self.main_column_by_cell_regs:
                            dst_chars = self.get_dst_chars_from_matcher(main_matcher, cell.raw_cell)
                            main_column_result = self.create_result(
                                self.create_content_result(table.element, dst_chars, cell, None),
                                column=self.main_column,
                            )
                        else:
                            main_column_result = self.create_answer_result(self.main_column, table.element, cell)
                    else:
                        if (
                            header_cells := cell.table.rows[cell.rowidx][: cell.colidx]
                            if tag_index == 0
                            else cell.table.cols[cell.colidx][: cell.rowidx]
                        ):
                            header_text = clean_txt(header_cells[0].text)
                            if not self.header_patterns(self.secondary_column).nexts(header_text):
                                continue
                            if matcher := self.cell_regs[self.secondary_column].nexts(header_text):
                                # 1、查看标题头是否有平台
                                dst_chars = self.get_dst_chars_from_matcher(matcher, header_cells[0].raw_cell)
                                secondary_column_result = self.create_result(
                                    self.create_content_result(table.element, dst_chars, [header_cells[0]], None),
                                    column=self.secondary_column,
                                )
                            # 2、平台和金额写在一起，有可能多个
                            start_index = 0
                            for match in chain(self.splits.finditer(cell.text), (None,)):
                                start, end = match.span() if match else (len(cell.text), 0)
                                if not (sub_text := cell.text[start_index:start]):
                                    start_index = end
                                    continue
                                sub_chars = cell.raw_cell["chars"][start_index:start]
                                answer_result = defaultdict(list)
                                for column in self.columns:
                                    if column == self.main_column and main_column_result is not None:
                                        answer_result[column] = [deepcopy(main_column_result)]
                                        continue
                                    if column == self.secondary_column and secondary_column_result is not None:
                                        answer_result[column] = [deepcopy(secondary_column_result)]
                                        continue
                                    if column_matcher := self.cell_regs[column].nexts(clean_txt(sub_text)):
                                        value = column_matcher.groupdict().get("dst", None)
                                        dst_chars = self.get_chars(
                                            sub_text, value, sub_chars, column_matcher.span("dst")
                                        )
                                        answer_result[column] = [
                                            self.create_result(
                                                self.create_content_result(table.element, dst_chars, [cell], None),
                                                column=column,
                                            )
                                        ]
                                if answer_result:
                                    group_answers.append(answer_result)
                                start_index = end
            if not self.multi_elements and group_answers:
                # 多元素块
                break
        return group_answers
