from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.row_match import RowMatch


class ChooseAccount(RowMatch):
    @property
    def need_first_row(self):
        return self.config.get("need_first_row", False)

    def predict_schema_answer(self, elements):
        answer_results = []
        nested_tables = self.pdfinsight.data.get("contain_index_nested_tables", {})
        if not nested_tables:
            return answer_results
        table_elements = []
        for tables in nested_tables.values():
            for table in tables:
                _, ele = self.pdfinsight.find_element_by_index(table["index"])
                table_elements.append(ele)
        for element in table_elements:
            answer_result = {}
            table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
            if len(table.rows) != 2:
                continue
            for column in self.columns:
                element_results = []
                row_pattern = PatternCollection(self.get_config("row_pattern", column=column))
                for valid_row in self.matched_rows(table.rows):
                    dst_chars_list, cells = self.get_answer_from_merge_row(row_pattern, valid_row)
                    if not dst_chars_list:
                        continue
                    for dst_chars in dst_chars_list:
                        element_results.extend(self.create_content_result(element, dst_chars, cells, None))
                    break
                if element_results:
                    answer_result[column] = [self.create_result(element_results, column=column)]
            if answer_result:
                answer_results.append(answer_result)
                break
        return answer_results

    def matched_rows(self, rows):
        if self.need_first_row:
            return rows[:1]
        return rows[1:]
