from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.base_model import TableModel
from remarkable.predictor.schema_answer import CellCharResult


class AfterTableInfo(TableModel):
    def train(self, dataset, **kwargs):
        pass

    def extract_feature(self, elements, answer):
        pass

    def predict_schema_answer(self, elements):
        ret = []
        cell_text_patterns = self.config.get("cell_text_patterns", {})
        for element in elements:
            table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
            for col in self.columns:
                pattern = cell_text_patterns.get(col)
                row_num = len(table.rows)
                for i in (1, 2):  # 表格后两行
                    if row_num - i < 0:
                        break
                    last_cell = table.rows[row_num - i][-1]
                    dst_chars = self.get_dst_chars_from_pattern(pattern, cell=last_cell)
                    if not dst_chars:
                        continue
                    answer = self.create_result([CellCharResult(element, dst_chars, [last_cell])], column=col)
                    ret.append(answer)
                    break
        return ret

    def get_dst_chars_from_pattern(self, pattern, cell):
        dst_chars = None
        if clean_matcher := PatternCollection(pattern).nexts(clean_txt(cell.text)):
            dst_chars = self.get_dst_chars_from_matcher(clean_matcher, cell.raw_cell)
        elif matcher := PatternCollection(pattern).nexts(cell.text):
            dst_chars = self.get_dst_chars_from_matcher(matcher, cell.raw_cell, is_clean_matcher=False)

        return dst_chars
