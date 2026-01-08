from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.dataset import DatasetItem
from remarkable.predictor.models.base_model import TableModel
from remarkable.predictor.schema_answer import TableCellsResult

AMOUNT_PATTERN = PatternCollection(r"[\d,]+")


class OctopusAmount(TableModel):
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
            for row in table.rows[::-1]:
                row_text = clean_txt("".join([cell.text for cell in row]))
                matcher = self.pattern.nexts(row_text)
                if not matcher:
                    continue
                for cell in row[::-1]:
                    cell_text = clean_txt(cell.text)
                    amount_matcher = AMOUNT_PATTERN.nexts(cell_text)
                    if not amount_matcher:
                        continue
                    element_results = [TableCellsResult(element, [cell])]
                    answer = self.create_result(element_results, column=self.schema.name)
                    ret.append(answer)
                    break
                if ret:
                    break
            if ret:
                break
        return ret
