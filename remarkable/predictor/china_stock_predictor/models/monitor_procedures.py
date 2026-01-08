from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import TableCellsResult


class MonitorProcedures(BaseModel):
    """
    先根据row_tag_pattern定位到row
    再获取该row最后一个cell
    """

    def train(self, dataset, **kwargs):
        pass

    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super().__init__(options, schema, predictor=predictor)

    def predict_schema_answer(self, elements):
        answer_results = []
        row_tag_pattern = PatternCollection(self.config.get("row_tag_pattern"))
        need_next_element = self.config.get("need_next_element", False)
        aim_index = self.config.get("aim_index", -1)
        overhead_cell_pattern = self.get_config("overhead_cell_pattern")
        for element in elements:
            if element["class"] != "TABLE":
                continue
            table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
            for column in self.columns:
                for row in table.rows:
                    valid_row = self.is_valid_row(row_tag_pattern, row)
                    if not valid_row:
                        continue
                    cell = row[aim_index]
                    if not self.is_valid_overhead_cell(overhead_cell_pattern, cell, table):
                        continue
                    element_results = [TableCellsResult(element, [cell])]
                    answer = {column: [self.create_result(element_results, column=column, text=cell.text)]}
                    answer_results.append(answer)
                    if need_next_element:
                        answer_results = self.get_answer_from_next_table(answer_results, element, column)
                    if answer_results and not self.multi:
                        break
            if answer_results:
                break
        return answer_results

    def get_answer_from_next_table(self, answer_results, element, column):
        post_elts = self.pdfinsight.find_elements_near_by(element["index"], amount=1, aim_types=["TABLE"])
        if not post_elts:
            return answer_results
        table = parse_table(post_elts[0], tabletype=TableType.KV.value, pdfinsight_reader=self.pdfinsight)
        first_cell = table.rows[0][0]
        if first_cell.text == "":
            cell = table.rows[0][-1]
            element_results = [TableCellsResult(post_elts[0], [cell])]
            answer = {column: [self.create_result(element_results, column=column, text=cell.text)]}
            answer_results.append(answer)
        return answer_results

    @staticmethod
    def is_valid_row(row_tag_pattern, row):
        first_cell = row[0]
        if row_tag_pattern.nexts(clean_txt(first_cell.text)):
            return True
        return False

    @staticmethod
    def is_valid_overhead_cell(overhead_cell_pattern, cell, table):
        if not overhead_cell_pattern:
            return True
        overhead_cell_pattern = PatternCollection(overhead_cell_pattern)
        if cell.rowidx < 1:
            return False
        header_row = table.rows[cell.rowidx - 1]
        header_cell = header_row[cell.colidx]
        if overhead_cell_pattern.nexts(clean_txt(header_cell.text)):
            return True
        return False
