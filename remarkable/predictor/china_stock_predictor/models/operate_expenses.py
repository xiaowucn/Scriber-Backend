from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import CellCharResult


class OperateExpenses(BaseModel):
    """
    遍历表格根据regs寻找答案
    因为有的表格跨页 所以没法用row_tag 定位row
    """

    def train(self, dataset, **kwargs):
        pass

    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(OperateExpenses, self).__init__(options, schema, predictor=predictor)

    def predict_schema_answer(self, elements):
        answer_results = []
        pattern = PatternCollection(self.config.get("regs", []))
        for element in elements:
            if element["class"] != "TABLE":
                continue
            table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
            for row in table.rows:
                for cell in row:
                    if cell.dummy:
                        continue
                    for column in self.columns:
                        matcher_results = self.get_dst_chars_from_pattern(pattern, cell=cell)
                        for dst_chars in matcher_results:
                            answer = self.create_result([CellCharResult(element, dst_chars, [cell])], column=column)
                            answer_results.append(answer)
                if answer_results:
                    break
            if answer_results:
                break
        return answer_results

    def get_dst_chars_from_pattern(self, pattern, cell):
        ret = []
        matchers = pattern.finditer(clean_txt(cell.text))
        for matcher in matchers:
            if not matcher:
                continue
            dst_chars = self.get_dst_chars_from_matcher(matcher, cell.raw_cell)
            if dst_chars:
                ret.append(dst_chars)
        return ret
