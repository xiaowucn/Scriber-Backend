from copy import deepcopy

from remarkable.predictor.models.partial_text import PartialText


class SingleFormula(PartialText):
    def predict_schema_answer(self, elements):
        ret = []
        answer_results = super().predict_schema_answer(elements)
        formula_answers = self.get_formula_answers(answer_results)
        for answer_result in answer_results:
            fund_type_answers = answer_result.get("基金类型", [])
            ratio_answers = answer_result.get("计提比例", [])
            ratio_answer = None
            if fund_type_answers:
                fund_answer = deepcopy(fund_type_answers)[0]
                if len(fund_answer.element_results) > 1:
                    fund_answer.element_results = fund_answer.element_results[:1]
                if ratio_answers:
                    ratio_answer = deepcopy(ratio_answers)[0]
                    if len(ratio_answer.element_results) > 1:
                        ratio_answer.element_results = ratio_answer.element_results[:1]
                fixed_answer_result = {
                    "基金类型": [fund_answer],
                    "计提比例": [ratio_answer] if ratio_answer else [],
                    "计提公式": deepcopy(formula_answers) if formula_answers else [],
                }
                ret.append(fixed_answer_result)
        if not ret:
            # 没有提取到基金类型
            ret.extend(deepcopy(answer_results))
            ratio_answers = []
            formula_answers = []
            for answer_result in answer_results:
                if answer_result.get("计提比例", []):
                    ratio_answers.extend(answer_result.get("计提比例", []))
                if answer_result.get("计提公式", []):
                    formula_answers.extend(answer_result.get("计提公式", []))
            if ratio_answers:
                ratio_answer = deepcopy(ratio_answers)[0]
                if len(ratio_answer.element_results) > 1:
                    ratio_answer.element_results = ratio_answer.element_results[:1]
                fake_char_result = deepcopy(ratio_answer.element_results[0])
                fake_char_result.display_text = "母基金"
                fund_type_answers = [self.create_result([fake_char_result], column="基金类型")]
                fixed_answer_result = {
                    "基金类型": fund_type_answers,
                    "计提比例": [ratio_answer],
                    "计提公式": deepcopy(formula_answers) if formula_answers else [],
                }
                ret.append(fixed_answer_result)
        return ret

    def get_formula_answers(self, answer_results):
        for answer_result in answer_results:
            if formula_answers := answer_result.get("计提公式", []):
                return formula_answers
        return None
