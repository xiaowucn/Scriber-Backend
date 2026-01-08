import re

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.models.table_kv import KeyValueTable
from remarkable.predictor.schema_answer import CharResult

PERSONNEL_SPLIT_PATTERN = re.compile(r"[、与和]")
PROPORTION_PATTERN = [r"[\d%％]"]


class ActualControlSituation(KeyValueTable):
    def __init__(self, options, schema, predictor):
        super(ActualControlSituation, self).__init__(options, schema, predictor)

    def predict_schema_answer(self, elements):
        ret = []
        answer_results = super(ActualControlSituation, self).predict_schema_answer(elements)
        person_answers, proportion_answers = [], []
        for answer_result in answer_results:
            name_answers = answer_result.get("名称", [])
            person_answers.extend(self.process_name_answer(name_answers))
            proportions = answer_result.get("持股比例", [])
            proportion_answers.extend(self.process_proportion_answer(proportions))
        if person_answers:
            ret.extend(person_answers)
        if proportion_answers:
            ret.extend(proportion_answers)

        return ret

    def process_name_answer(self, name_answers):
        ret = []
        for name_answer in name_answers:
            element_result = name_answer.element_results[0]
            parsed_cell = element_result.parsed_cells[0]
            element = name_answer.relative_elements[0]
            matcher = PatternCollection([PERSONNEL_SPLIT_PATTERN]).nexts(clean_txt(parsed_cell.text))
            if matcher:
                for text in PERSONNEL_SPLIT_PATTERN.split(clean_txt(parsed_cell.text)):
                    name_dst_chars = self.get_dst_chars_from_text(text, parsed_cell.raw_cell)
                    if not name_dst_chars:
                        continue
                    ret.append(self.create_result([CharResult(element, name_dst_chars)], column="名称"))
        return ret

    @staticmethod
    def process_proportion_answer(proportions):
        ret = []
        for proportion in proportions:
            element_result = proportion.element_results[0]
            parsed_cell = element_result.parsed_cells[0]
            if PatternCollection(PROPORTION_PATTERN).nexts(clean_txt(parsed_cell.text)):
                ret.append(proportion)
        return ret
