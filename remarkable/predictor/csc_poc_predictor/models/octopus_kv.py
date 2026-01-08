from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.dataset import DatasetItem
from remarkable.predictor.models.base_model import TableModel
from remarkable.predictor.schema_answer import CellCharResult


class OctopusKv(TableModel):
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
                for cell in row:
                    cell_text = clean_txt(cell.text)
                    matcher = self.pattern.nexts(cell_text)
                    if not matcher:
                        continue
                    dst_chars = self.get_dst_chars_from_matcher(matcher, cell.raw_cell)
                    if not dst_chars:
                        continue
                    answer = self.create_result([CellCharResult(element, dst_chars, [cell])], column=self.schema.name)
                    ret.append(answer)
                    break
                if ret:
                    break
            if ret:
                break
        return ret
