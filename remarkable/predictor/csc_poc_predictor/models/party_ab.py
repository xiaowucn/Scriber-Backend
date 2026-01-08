from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.dataset import DatasetItem
from remarkable.predictor.models.base_model import TableModel
from remarkable.predictor.schema_answer import TableCellsResult

col_pattern = {
    "单位名称": PatternCollection(r"单位名称"),
    "单位地址": PatternCollection(r"单位地址"),
    "法定代表人": PatternCollection(r"法定代表人"),
}


class PartyAB(TableModel):
    def extract_feature(self, elements, answer):
        pass

    def train(self, dataset: list[DatasetItem], **kwargs):
        pass

    @property
    def pattern(self):
        return PatternCollection(self.get_config("pattern", []))

    def predict_schema_answer(self, elements):
        ret = []
        for element in elements:
            table = parse_table(element, tabletype=TableType.KV.value, pdfinsight_reader=self.pdfinsight)
            for row in table.rows:
                first_cell = row[0]
                if not self.pattern.nexts(clean_txt(first_cell.text)):
                    continue
                second_cell = row[1]
                for col, pattern in col_pattern.items():
                    if not pattern.nexts(clean_txt(second_cell.text)):
                        continue
                    answer_cell = row[2]
                    element_results = [TableCellsResult(element, [answer_cell])]
                    answer = self.create_result(element_results, column=col)
                    ret.append(answer)
                    break
            if ret:
                break
        return ret
