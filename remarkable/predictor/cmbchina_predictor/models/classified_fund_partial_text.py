from collections import defaultdict

from remarkable.common.pattern import PatternCollection
from remarkable.predictor.models.partial_text import PartialText
from remarkable.predictor.schema_answer import PredictorResult


class ClassifiedFundPartialText(PartialText):
    def predict_schema_answer(self, elements):
        answer_results = []
        temp_answer_results = super().predict_schema_answer(elements)
        if not temp_answer_results:
            return answer_results

        fixed_answer_results = defaultdict(list)
        for answer_result in temp_answer_results:
            for key, predictor_results in answer_result.items():
                fixed_answer_results[key].extend(predictor_results)

        for key, predictor_results in fixed_answer_results.items():
            if key == "基金简称":
                fixed_answer_results[key] = self.revise_fund_abbreviation(predictor_results)

        return [fixed_answer_results]

    def revise_fund_abbreviation(self, answers: list[PredictorResult]) -> list[PredictorResult]:
        score_regs = [
            {"regs": [r"(?P<dst>[A-Z])$"], "score": 0.8},
            {"regs": [r"^(?P<dst>[A-Z])"], "score": 0.5},
            {"regs": [r"(?P<dst>.*)"], "score": 0.1},
        ]

        def calc_score(score_regs, answer):
            for score_reg in score_regs:
                regs = PatternCollection(score_reg["regs"])
                matcher = regs.nexts(answer.text)
                if matcher:
                    answer.reg_score = score_reg["score"]
                    answer.reg_tag = matcher.groupdict()["dst"]
                    break
            return answer

        group_by_tag = defaultdict(list)
        for answer in answers:
            answer = calc_score(score_regs, answer)
            group_by_tag[answer.reg_tag].append(answer)
        revised_answer = []
        for answers in group_by_tag.values():
            revised_answer.append(max(answers, key=lambda x: x.reg_score))
        return revised_answer
