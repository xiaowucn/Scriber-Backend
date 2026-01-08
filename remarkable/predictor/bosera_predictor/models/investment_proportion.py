"""
投资比例
"""

import logging

from remarkable.predictor.models.base_model import get_char_position
from remarkable.predictor.models.partial_text import PartialText
from remarkable.predictor.schema_answer import CellCharResult, CharResult


class InvestmentProportion(PartialText):
    def predict_schema_answer(self, elements):
        answer_results = []
        temp_answer_results = super().predict_schema_answer(elements)
        if not temp_answer_results:
            return answer_results

        categories = []
        contents = []
        for temp_answer_result in temp_answer_results:
            categories.extend(temp_answer_result.get("投资大类", []))
            contents.extend(temp_answer_result.get("大类内容", []))

        if not contents:
            logging.warning("Bad result without 大类内容 for 投资比例")
            return answer_results

        categories = self.sorted_results(categories)
        contents = self.sorted_results(contents)

        for category in categories:
            index = len(answer_results)
            category_ele_index = category.element_results[0].element["index"]
            if index < len(contents):
                content = contents[index]
                content_ele_index = content.element_results[0].element["index"]
                if content_ele_index not in (category_ele_index, category_ele_index + 1):
                    continue

                answer_result = {
                    "投资大类": [category],
                    "大类内容": [content],
                }

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
