from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.table_row import TableRow
from remarkable.predictor.schema_answer import TableCellsResult

SPECIAL_COLUMN = "岗位"
NAME_COLUMN = "姓名"


class FundPeople(TableRow):
    def predict_schema_answer(self, elements):
        ret = []
        parent_answer_results = super().predict_schema_answer(elements)
        if not parent_answer_results:
            return ret
        answers = self.regroup(parent_answer_results)
        element = self.find_total_element(answers)
        if not element:
            return ret
        table = parse_table(element, tabletype=self.table_type, pdfinsight_reader=self.pdfinsight)
        # 只包含'岗位' 一个字段的答案时 为了分组 手动添加'姓名'的答案
        if len(answers) == 1 and SPECIAL_COLUMN in answers:
            for predictor_result in answers[SPECIAL_COLUMN]:
                answer_element = predictor_result.element_results[0]
                answer_cell = answer_element.parsed_cells[0]
                if answer_cell.dummy:
                    continue
                cell_row_idx, cell_col_idx = answer_element.cells[0].split("_")
                name_cell_col_idx = int(cell_col_idx) + 1
                aim_cell = table.rows[int(cell_row_idx)][name_cell_col_idx]
                name_answer = self.create_result([TableCellsResult(element, [aim_cell])], column=NAME_COLUMN)
                result = {
                    SPECIAL_COLUMN: [predictor_result],
                    NAME_COLUMN: [name_answer],
                }
                ret.append(result)

            return ret
        return parent_answer_results

    @staticmethod
    def find_total_element(answers):
        for answer in answers.values():
            return answer[0].relative_elements[0]
        return None
