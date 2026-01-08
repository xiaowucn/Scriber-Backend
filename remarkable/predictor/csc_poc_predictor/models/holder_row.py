from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.dataset import DatasetItem
from remarkable.predictor.models.base_model import TableModel
from remarkable.predictor.schema_answer import TableCellsResult

SERIAL_PATTERN = PatternCollection(r"^\d{1,2}$")

key_map = {
    "持有人全称": 2,
    "持有人账号": 3,
    "承销/认购金额（万元）": 4,
}


class HolderRow(TableModel):
    def extract_feature(self, elements, answer):
        pass

    def train(self, dataset: list[DatasetItem], **kwargs):
        pass

    @property
    def pattern(self):
        return PatternCollection(self.get_config("pattern", []))

    def predict_schema_answer(self, elements):
        ret = []
        holders = set()
        for element in elements:
            table = parse_table(element, tabletype=TableType.KV.value, pdfinsight_reader=self.pdfinsight)
            for row in table.rows:
                second_cell_text = clean_txt(row[1].text)
                if not SERIAL_PATTERN.nexts(second_cell_text):
                    continue
                answer_result = {}
                for column in self.columns:
                    cell = row[key_map[column]]
                    if column == "持有人全称":
                        if cell.text in holders:
                            break
                        holders.add(cell.text)

                    element_results = [TableCellsResult(element, [cell])]
                    answer = self.create_result(element_results, column=column)
                    answer_result.setdefault(column, []).append(answer)
                if answer_result:
                    ret.append(answer_result)
        return ret
