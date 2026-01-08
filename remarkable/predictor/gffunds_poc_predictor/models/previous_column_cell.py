from collections import defaultdict

from remarkable.common.pattern import PatternCollection
from remarkable.pdfinsight.reader import PdfinsightTable
from remarkable.predictor.models.base_model import TableModel
from remarkable.predictor.schema_answer import CharResult


class TablePreviousColumnCellContent(TableModel):
    def predict_schema_answer(self, elements):
        answers = []
        elements = self.revise_elements(elements)
        pattern = self.get_config("regs")
        for element in elements:
            table = PdfinsightTable(element)
            columns = self.extrat_columns(table)
            for column in columns.values():
                cell = self.search_cell(column, pattern)
                if cell is not None:
                    answer_result = self.build_answer_result(cell, element)
                    answers.append(answer_result)
                    return answers

        return answers

    def build_answer_result(self, cell, element):
        element_results = [CharResult(element, cell["chars"])]
        return self.create_result(element_results)

    @staticmethod
    def extrat_columns(table):
        table_columns = defaultdict(list)
        for cell in table.cells.values():
            for column_idx, cell_value in cell.items():
                if column_idx not in table_columns:
                    table_columns[column_idx] = [cell_value]
                else:
                    table_columns[column_idx].append(cell_value)
        return table_columns

    @staticmethod
    def search_cell(column, pattern):
        for index, cell_value in enumerate(column):
            if PatternCollection(pattern).nexts(cell_value["text"]):
                return column[index - 1] if index > 0 else None
        return None

    def train(self, dataset, **kwargs):
        pass

    def print_model(self):
        pass

    def extract_feature(self, elements, answer):
        pass
