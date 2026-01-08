from remarkable.common.pattern import PatternCollection
from remarkable.predictor.models.table_kv import KeyValueTable
from remarkable.predictor.schema_answer import PredictorResult


class TableKVAmount(KeyValueTable):
    p_unit_map = {
        "金额单位": PatternCollection(r"(?P<unit>[亿万元]+)"),
        "期限单位": PatternCollection(r"(?P<unit>[年月日天])"),
    }

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        answer_results = super().predict_schema_answer(elements)
        for answer_result in answer_results:
            for column, items in answer_result.items():
                if column in ["金额单位", "期限单位"]:
                    self.fix_unit(column, items)

        return answer_results

    def fix_unit(self, column, predictor_results):
        p_unit = self.p_unit_map[column]
        split_pattern = self.get_config("split_pattern", column=column)

        for predictor_result in predictor_results:
            if p_unit.nexts(predictor_result.text):
                continue
            parsed_cell = predictor_result.element_results[0].parsed_cells[0]
            element = predictor_result.element_results[0].element
            row = parsed_cell.table.rows[parsed_cell.rowidx]
            cell = row[0]
            if p_unit.nexts(cell.text):
                if cell.unit and p_unit.nexts(cell.unit.text):
                    predictor_result.element_results.append(cell.unit)
                else:
                    predictor_result.element_results.extend(
                        self.create_content_result(element, cell.raw_cell["chars"], [cell], split_pattern)
                    )
                new_predictor_result = self.create_result(
                    predictor_result.element_results, schema=predictor_result.schema
                )
                predictor_result.answer_value = new_predictor_result.answer_value
