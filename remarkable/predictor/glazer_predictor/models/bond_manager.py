"""
债券受托管理人
"""

from remarkable.predictor.models.partial_text import PartialText
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2


class BondManager(SyllabusEltV2):
    def predict_schema_answer(self, elements):
        answer_results = []
        temp_answer_results = super(BondManager, self).predict_schema_answer(elements)
        for temp_answer_result in temp_answer_results:
            if temp_answer_result.schema.name != "债券受托管理人机构信息":
                continue
            answer_result = {
                "债券受托管理人机构信息": [temp_answer_result],
                "债券受托管理人名称": self.predict_name(temp_answer_result),
            }
            answer_results.append(answer_result)
        return answer_results

    def predict_name(self, answer_result):
        name_result = []
        relative_element = answer_result.relative_elements[0]
        title_element = self.get_title_element(relative_element)
        partial_text_config = [
            {
                "config": {"regs": [r"名称[:：](?P<dst>.*公司)"]},
                "element": relative_element,
            },
            {
                "config": {"regs": [r"(债券|受托|债券受托)管理人.*[:：](?P<dst>.*)"]},
                "element": title_element,
            },
        ]
        for item in partial_text_config:
            element = item["element"]
            if not element:
                continue
            partial_text = PartialText(item["config"], self.schema, predictor=self.predictor)
            result = partial_text.predict_schema_answer([element])
            if result:
                name_result = result[0]["债券受托管理人名称"]
                break

        return name_result
