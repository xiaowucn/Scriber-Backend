from remarkable.predictor.models.table_row import TableRow
from remarkable.predictor.schema_answer import CharResult, TableCellsResult


class ExtraDateInfo(TableRow):
    @staticmethod
    def is_unit(col):
        return col.endswith("-单位")

    def get_model_data(self, column=None):
        column = self.columns[0] if self.is_unit(column) else column
        self.model_data = self.predictor.model_data.get(self.name) or self.predictor.model_data.get("table_row")
        return super(ExtraDateInfo, self).get_model_data(column)

    def create_answer_result(self, column, element, cell):
        if not self.is_unit(column):
            return self.create_result([TableCellsResult(element, [cell])], column=column)
        return self.create_result([cell.unit if cell.unit else CharResult(element, [])], column=column)
