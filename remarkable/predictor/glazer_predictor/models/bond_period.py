"""
债券期限详情
"""

from collections import defaultdict
from copy import deepcopy

from remarkable.common.pattern import PatternCollection
from remarkable.predictor.glazer_predictor.models import BondAbbreviation
from remarkable.predictor.glazer_predictor.schemas.citic_issue_announcement_plus_two_schema import p_bond_variety
from remarkable.predictor.models.partial_text import PartialText

p_renewable = PatternCollection([r"在每个周期末.*有权.*延长"])


class BondPeriod(PartialText):
    def predict_schema_answer(self, elements):
        answer_results = []
        temp_answer_results = super(BondPeriod, self).predict_schema_answer(elements)

        if not temp_answer_results:
            return answer_results

        all_elements = {}
        reconstructed_answer_results = self.get_reconstructed_answer_results(temp_answer_results)
        for key, val in reconstructed_answer_results.items():
            reconstructed_answer_results[key] = BondAbbreviation.sorted_results(val)
            for result in val:
                for ele in result.relative_elements:
                    all_elements[ele["index"]] = ele

        varieties = reconstructed_answer_results["债券品种"]
        if not reconstructed_answer_results["债券品种"]:
            return [reconstructed_answer_results]

        relative_element = varieties[0].relative_elements[0]
        renewable = p_renewable.nexts(relative_element["text"])

        variety_num = len({variety.text for variety in varieties})
        for index in range(variety_num):
            elements = self.get_fixed_elements(index, variety_num, all_elements.values())
            partial_text = PartialText(self.config, self.schema, predictor=self.predictor)
            answer_result = self.get_reconstructed_answer_results(partial_text.predict_schema_answer(elements))
            answer_result["债券品种"] = answer_result["债券品种"][:1]
            if renewable:
                for column in ["期限B", "期限C"]:
                    answer_result.pop(column)

            answer_results.append(answer_result)
        return answer_results

    def get_reconstructed_answer_results(self, answer_results):
        reconstructed_answer_results = defaultdict(list)
        for answer_result in answer_results:
            for column in self.columns:
                reconstructed_answer_results[column].extend(answer_result.get(column, []))
        return reconstructed_answer_results

    @staticmethod
    def get_non_mosaic_range(element_text, index, variety_num):
        points = []
        prev = None
        for match in PatternCollection(p_bond_variety).finditer(element_text):
            start, _ = match.span()
            if match.group() == prev:
                continue
            points.append(start)
            prev = match.group()

        non_mosaic_range = []
        point_num = len(points)
        group_numbers = int(point_num / variety_num)
        for offset_times in range(group_numbers):
            start_index = index + offset_times * variety_num
            end_index = index + 1 + offset_times * variety_num
            start_point = points[start_index] if not (offset_times == 0 and index == 0) else 0
            end_point = points[end_index] if end_index < point_num else len(element_text)
            non_mosaic_range.append((start_point, end_point))
        return non_mosaic_range

    @staticmethod
    def is_mosaic(non_mosaic_range, pos):
        for start, end in non_mosaic_range:
            if start <= pos < end:
                return False
        return True

    def make_mosaic(self, element_text, index, variety_num):
        non_mosaic_range = self.get_non_mosaic_range(element_text, index, variety_num)
        text = ""
        for pos, char in enumerate(element_text):
            if not self.is_mosaic(non_mosaic_range, pos):
                text += char
            else:
                text += "A"
        return text

    def get_fixed_elements(self, index, variety_num, all_elements):
        fixed_elements = []
        for element in all_elements:
            fixed_element = deepcopy(element)

            fixed_element["text"] = self.make_mosaic(element["text"], index, variety_num)
            if element.get("page_merged_paragraph"):
                fixed_element["page_merged_paragraph"]["text"] = self.make_mosaic(
                    element["page_merged_paragraph"]["text"], index, variety_num
                )
            fixed_elements.append(fixed_element)
        return fixed_elements
