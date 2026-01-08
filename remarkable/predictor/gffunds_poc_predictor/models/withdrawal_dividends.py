from remarkable.common.pattern import PatternCollection
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.table_row import TableRow
from remarkable.predictor.schema_answer import CellCharResult, PredictorResult


class WithdrawalDividends(TableRow):
    @property
    def content_regs(self):
        return PatternCollection(self.get_config("content_regs"))

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        answer_results = []
        for element in elements:
            table = parse_table(element, tabletype=self.table_type, pdfinsight_reader=self.pdfinsight)
            for row in table.rows:
                # 跳过 全是合并单元格的一行
                if self.filter_single_data_row and len(row) > 1 and len({cell.text for cell in row if cell.text}) == 1:
                    continue
                answer_result = {}
                for column in self.columns:
                    cells = [cell for cell in row if cell.dummy is False]
                    row_texts = "".join(cell.normalized_text for cell in cells)
                    for cell in cells:
                        if not (match := self.match_cell(cell, row_texts, column)):
                            continue
                        if dst_chars := self.get_dst_chars_from_text(match.group("dst"), cell.raw_cell):
                            answer_result.setdefault(column, []).append(
                                self.create_result([CellCharResult(element, dst_chars, [cell])], column=column)
                            )
                if answer_result:
                    answer_results.append(answer_result)
                if not self.multi:
                    # 多行
                    break
            if not self.multi_elements and answer_results:
                # 多元素块
                break
        return answer_results

    def match_cell(self, cell, row_texts, column):
        if self.content_regs.nexts(row_texts):
            return PatternCollection(self.get_config(column)["regs"]).nexts(cell.text)
        return None
