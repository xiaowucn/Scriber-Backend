from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.row_match import RowMatch


class ParseMoney(RowMatch):
    def predict_schema_answer(self, elements):
        answer_results = []
        nested_tables = self.pdfinsight.data.get("contain_index_nested_tables", {})
        tables = []
        for element in elements:
            if element["class"] != "TABLE":
                continue
            tables.append(element)
            for tbs in nested_tables.get(element["index"], {}):
                _, ele = self.pdfinsight.find_element_by_index(tbs["index"])
                tables.append(ele)
        for element in tables:
            answer_result = {}
            table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
            for column in self.columns:
                element_results = []
                row_pattern = PatternCollection(self.get_config("row_pattern", column=column))
                content_pattern = PatternCollection(self.get_config("content_pattern", column=column))
                valid_rows = self.matched_rows(table, row_pattern)
                for valid_row in valid_rows:
                    dst_chars_list, cells = self.get_answer_from_merge_row(content_pattern, valid_row)
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

    @staticmethod
    def matched_rows(table, pattern):
        rows = []
        for idx, row in enumerate(table.rows):
            row_texts = "".join([clean_txt(cell.text) for cell in row if not cell.dummy])
            if pattern.nexts(row_texts):
                rows.append(row)
            if rows:
                rows.extend(table.rows[idx + 1 :])
                break
        return rows
