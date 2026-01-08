from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.table_kv import KeyValueTable
from remarkable.predictor.schema_answer import TableCellsResult

second_row_first_cell_pattern = PatternCollection([r"基金管理费收费账户"])


class PerformanceCalc(KeyValueTable):
    def predict_schema_answer(self, elements):
        ret = []
        parent_answer_results = super(PerformanceCalc, self).predict_schema_answer(elements)
        if not parent_answer_results:
            return ret
        precessed_elements = set()
        # ret.extend(parent_answer_results)
        # for parent_answer in parent_answer_results:
        #     for _, answer_item in parent_answer.items():
        #         element = answer_item[0].relative_elements[0]
        #         precessed_elements.add(element['index'])
        row_tag_pattern = PatternCollection(self.config.get("row_tag_pattern", []))
        for element in elements:
            table = parse_table(
                element,
                tabletype=TableType.KV.value,
                pdfinsight_reader=self.pdfinsight,
            )
            for row in table.rows:
                first_cell = clean_txt(row[0].text)
                if not row_tag_pattern.nexts(first_cell):
                    continue
                answer = self.create_result([TableCellsResult(element, [row[-1]])], column=self.schema.name)
                ret.append(answer)
                precessed_elements.add(element["index"])
                break

        for element in elements:
            if element["index"] in precessed_elements or element["class"] != "TABLE":
                continue
            table = parse_table(element, tabletype=TableType.KV.value, pdfinsight_reader=self.pdfinsight)
            if len(table.rows) >= 2:
                second_row_first_cell = table.rows[1][0]
                first_row_first_cell = table.rows[0][0]
                if (
                    second_row_first_cell_pattern.nexts(clean_txt(second_row_first_cell.text))
                    and first_row_first_cell.text == ""
                ):
                    aim_cell = table.rows[0][-1]
                    answer = self.create_result([TableCellsResult(element, [aim_cell])], column="业绩报酬-计算方式")
                    ret.append(answer)
        return ret
