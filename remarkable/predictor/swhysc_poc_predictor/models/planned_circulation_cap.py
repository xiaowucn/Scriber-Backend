from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.models.table_kv import KeyValueTable

column_pattern = PatternCollection([r"上限"])
answer_pattern = PatternCollection([r"上限|不超过"])


class PlannedCirculationCap(KeyValueTable):
    def __init__(self, options, schema, predictor):
        super(PlannedCirculationCap, self).__init__(options, schema, predictor)

    def predict_schema_answer(self, elements):
        ret = []
        answer_results = super(PlannedCirculationCap, self).predict_schema_answer(elements)
        for answer_result in answer_results:
            fixed_answer_result = {}
            for column, answer in answer_result.items():
                element = answer[0].relative_elements[0]
                if element["class"] == "TABLE":
                    answer_cell = answer[0].element_results[0].parsed_cells[0]
                    column_cell = element["cells"][f"{answer_cell.rowidx}_0"]
                    if not column_pattern.nexts(clean_txt(column_cell["text"])) and not answer_pattern.nexts(
                        clean_txt(answer_cell.text)
                    ):
                        continue
                fixed_answer_result[column] = answer
            ret.append(fixed_answer_result)

        return ret
