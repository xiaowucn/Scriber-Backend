from copy import deepcopy

from remarkable.predictor.models.partial_text import PartialText


class PerformanceExtract(PartialText):
    def predict_schema_answer(self, elements):
        ret = []
        answer_results = super().predict_schema_answer(elements)
        for answer_result in answer_results:
            principle_answer = None
            fund_type_answers = answer_result.get("基金类型", [])
            principle_answers = answer_result.get("业绩报酬提取原则", [])
            if principle_answers:
                principle_answer = deepcopy(principle_answers[0])
                if len(principle_answer.element_results) > 1:
                    principle_answer.element_results = principle_answer.element_results[:1]
            if fund_type_answers:
                fund_type_answer = fund_type_answers[0]
                if len(fund_type_answer.element_results) == 1:
                    fixed_answer_result = {
                        "基金类型": fund_type_answers,
                        "业绩报酬提取原则": [principle_answer] if principle_answer else [],
                    }
                    ret.append(fixed_answer_result)
                    continue
                for element_result in fund_type_answer.element_results:
                    fixed_answer_result = {
                        "基金类型": [self.create_result([element_result], column="基金类型")],
                        "业绩报酬提取原则": [deepcopy(principle_answer)] if principle_answer else [],
                    }
                    ret.append(fixed_answer_result)
            elif principle_answers:
                fake_char_result = deepcopy(principle_answer.element_results[0])
                fake_char_result.display_text = "母基金"
                fixed_answer_result = {
                    "基金类型": [self.create_result([fake_char_result], column="基金类型")],
                    "业绩报酬提取原则": [principle_answer] if principle_answer else [],
                }
                ret.append(fixed_answer_result)
        return ret
