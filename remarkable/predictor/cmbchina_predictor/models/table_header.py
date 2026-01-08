from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.models.table_row import TableRow
from remarkable.predictor.schema_answer import PredictorResult


class TableHeader(TableRow):
    __name__ = "table_header"

    def __init__(self, options, schema, predictor=None):
        super().__init__(options, schema, predictor=predictor)

    def header_patterns(self, column):
        return PatternCollection(self.get_config("header_patterns", [], column))

    def neglect_header_patterns(self, column):
        return PatternCollection(self.get_config("neglect_header_patterns", [], column))

    def value_patterns(self, column):
        return PatternCollection(self.get_config("value_patterns", [], column))

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        answer_results = []
        elements = self.revise_elements(elements)
        if self.multi_elements:
            elements.sort(key=lambda x: x["index"])

        for element in elements:
            if element["class"] != "TABLE":
                continue
            table = self.prepare_table(element)
            if not table:
                continue
            items = table.rows if self.parse_by == "row" else table.cols
            for column in self.columns:
                cells_count = self.get_config("cells_count", None, column)
                answer_result = []
                for row in items:
                    cells = [cell for cell in row if not cell.dummy]
                    if cells_count and len(cells) != cells_count:
                        continue
                    row_text = clean_txt("".join(cell.normalized_text for cell in row))
                    if self.neglect_header_patterns(column).nexts(row_text):
                        continue
                    header_patterns = self.header_patterns(column)
                    if not header_patterns.all(row_text):
                        continue
                    for cell in cells:
                        if header_patterns.all(clean_txt(cell.text)):
                            continue
                        if column_value_pattern := self.value_patterns(column):
                            if matcher := column_value_pattern.nexts(clean_txt(cell.text)):
                                value = matcher.groupdict().get("dst", None)
                                dst_chars = self.get_chars(
                                    cell.text, value, cell.raw_cell["chars"], matcher.span("dst")
                                )
                                answer_result.append(
                                    {
                                        column: [
                                            self.create_result(
                                                self.create_content_result(table.element, dst_chars, [cell], None),
                                                column=column,
                                            )
                                        ]
                                    }
                                )
                        else:
                            answer_result.append({column: [self.create_answer_result(column, table.element, cell)]})
                if answer_result:
                    answer_results.append(answer_result)
        results = []
        for answer_result in zip(*answer_results):
            results.append({key: value for result in answer_result for key, value in result.items()})
        return results
