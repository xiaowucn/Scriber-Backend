from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.table_row import TableRow
from remarkable.predictor.schema_answer import CellCharResult

SPECIAL_COLUMNS = ["产品数量-单位", "资产净值-单位"]

unit_p = PatternCollection(r"[(（](?P<dst>只|元)[）)]")


class PartTimeSituation(TableRow):
    def predict_schema_answer(self, elements):
        ret = []
        parent_answer_results = super().predict_schema_answer(elements)
        if not parent_answer_results:
            return ret
        if answer := self.create_answer_without_table_header(elements, parent_answer_results):
            parent_answer_results.extend(answer)
        for answer_result in parent_answer_results:
            for column in SPECIAL_COLUMNS:
                answer = answer_result.get(column)
                if not answer:
                    continue
                parsed_cell = answer[0].element_results[0].parsed_cells[0]
                element = answer[0].relative_elements[0]
                for header in parsed_cell.headers:
                    matcher = unit_p.nexts(clean_txt(header.text))
                    if not matcher:
                        continue
                    dst_chars = self.get_dst_chars_from_matcher(matcher, header.raw_cell)
                    if not dst_chars:
                        continue
                    unit_answer = self.create_result([CellCharResult(element, dst_chars, [header])], column=column)
                    answer_result[column] = [unit_answer]
                    break
        return parent_answer_results

    def create_answer_without_table_header(self, elements, pre_table_answer):
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2173
        answer_results = []
        if len(elements) >= 2 and all(
            element["class"] == "TABLE" and element["title"] == elements[0]["title"] for element in elements[:2]
        ):
            table = parse_table(elements[1], tabletype=self.table_type, pdfinsight_reader=self.pdfinsight)
            items = table.rows if self.parse_by == "row" else table.cols
            columns = [column for column in self.columns if column not in SPECIAL_COLUMNS]
            for row in items:
                answer_result = {}
                for column, cell in zip(columns, row):
                    answer_result.setdefault(column, []).append(self.create_answer_result(column, elements[1], cell))
                for pre_answer, pre_answer_value in pre_table_answer[0].items():
                    if pre_answer in SPECIAL_COLUMNS:
                        answer_result.update({pre_answer: pre_answer_value})
                answer_results.append(answer_result)
        return answer_results
