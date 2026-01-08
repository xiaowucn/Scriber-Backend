from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import TableCellsResult

FUND_NAME_PATTERN = PatternCollection(["基金名称"])


class FundName(BaseModel):
    """
    找到 基金基本情况表
    一般第一行是 私募基金名称
    获取第一行第二列的内容
    """

    def train(self, dataset, **kwargs):
        pass

    def predict_schema_answer(self, elements):
        row = self.find_special_table_row()
        if not row:
            return []

        name_answer = self.create_result([TableCellsResult(row[-1].table.element, [row[-1]])], column=self.schema.name)
        return [name_answer]

    def find_special_table_row(self):
        table_list = list(self.pdfinsight.table_dict.values())
        for index in range(5):
            if index >= len(table_list):
                break
            merge_tale = table_list[index]  # 默认取文档第一个表格
            first_table_element = merge_tale.tables[0]
            first_table_element["cells"] = merge_tale.cells
            table = parse_table(first_table_element, tabletype=TableType.KV.value, pdfinsight_reader=self.pdfinsight)

            for row_index in range(10):
                if row_index >= len(table.rows):
                    break
                row = table.rows[row_index]
                first_cell = row[0]
                if FUND_NAME_PATTERN.nexts(clean_txt(first_cell.text)):
                    return row
        return None
