from collections import defaultdict

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.models.table_kv import KeyValueTable
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import CellCharResult


class KvCellText(KeyValueTable):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(KvCellText, self).__init__(options, schema, predictor=predictor)

    def predict_schema_answer(self, elements):
        ret = []
        parent_answer_results = super(KvCellText, self).predict_schema_answer(elements)
        if not parent_answer_results:
            return ret
        parent_answer_results = self.regroup(parent_answer_results)
        cell_text_patterns = self.config.get("cell_text_patterns", {})
        for col in self.columns:
            parent_answers = parent_answer_results.get(col)
            if not parent_answers:
                continue
            pattern = cell_text_patterns.get(col)
            for parent_answer in parent_answers:
                element = parent_answer.relative_elements[0]
                cell = parent_answer.element_results[0].parsed_cells[0]
                dst_chars = self.get_dst_chars_from_pattern(pattern, cell=cell)
                if not dst_chars:
                    continue
                answer = self.create_result([CellCharResult(element, dst_chars, [cell])], column=col)
                ret.append(answer)
        return ret

    def get_dst_chars_from_pattern(self, pattern, cell):
        matcher = PatternCollection(pattern).nexts(clean_txt(cell.text))
        if matcher:
            dst_chars = self.get_dst_chars_from_matcher(matcher, cell.raw_cell)
            if dst_chars:
                return dst_chars
        return None

    @staticmethod
    def regroup(answers):
        ret = defaultdict(list)
        for answer in answers:
            for col, value in answer.items():
                ret[col].extend(value)
        return ret
