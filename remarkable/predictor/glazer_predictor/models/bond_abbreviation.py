"""
债券简称详情
"""

import logging

from remarkable.predictor.models.base_model import get_char_position
from remarkable.predictor.models.syllabus_based import SyllabusBased
from remarkable.predictor.schema_answer import CellCharResult, CharResult


class BondAbbreviation(SyllabusBased):
    def predict_schema_answer(self, elements):
        answer_results = []
        temp_answer_results = super(BondAbbreviation, self).predict_schema_answer(elements)
        if not temp_answer_results:
            return answer_results

        abbreviations = self.sorted_results(temp_answer_results[0].get("债券简称", []))
        if not abbreviations:
            logging.warning("Bad result without 债券简称 for 债券简称详情")

        varieties = self.sorted_results(temp_answer_results[0].get("债券品种", []))
        codes = self.sorted_results(temp_answer_results[0].get("债券代码", []))

        for index, abbreviation in enumerate(abbreviations):
            answer_result = {"债券简称": [abbreviation]}
            if index < len(varieties):
                answer_result["债券品种"] = [varieties[index]]
            if index < len(codes):
                answer_result["债券代码"] = [codes[index]]
            answer_results.append(answer_result)
        return answer_results

    @staticmethod
    def sorted_results(results):
        res = []
        for result in results:
            char_result = result.element_results[0]
            cell_index = (0, 0)
            if isinstance(char_result, CharResult):
                chars = char_result.element["chars"]
                element_index = char_result.element["index"]
            elif isinstance(char_result, CellCharResult):
                cell = result.parsed_cells[0]
                chars = cell.raw_cell["chars"]
                element_index = char_result.element["index"]
                cell_index = (cell.rowidx, cell.colidx)
            else:
                logging.error(f"unexpected CharResult type. {type(char_result)}")
                return results

            position = get_char_position(char_result.chars[0], chars)
            if position is None:
                logging.error(f"char box not found in element chars. {char_result}. {char_result.chars}")
                return results

            res.append([position, result, element_index, cell_index])

        return [item[1] for item in sorted(res, key=lambda x: (x[2], x[3], x[0]))]
