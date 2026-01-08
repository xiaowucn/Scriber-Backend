from collections import Counter

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.schema_answer import CharResult

P_SYLLABUS = PatternCollection(r"(股票|个股)(投资|选择)(策略|风格)$")
P_PARENT_SYLLABUS = PatternCollection(r"投资策略$")


class StockStyleConv(SyllabusEltV2):
    def get_model_data(self, column=None, *, name=None) -> Counter:
        return super().get_model_data(column, name="syllabus_elt_v2")

    def predict_schema_answer(self, elements):
        answers = []
        for answer in super().predict_schema_answer(elements):
            if not answer.element_results:
                continue
            syllabuses = self.pdfinsight_syllabus.find_by_elt_index(
                answer.element_results[0].element["index"], include_self=False
            )
            if len(syllabuses) < 2:
                continue
            if P_SYLLABUS.nexts(clean_txt(syllabuses[-1]["title"])):
                answer.answer_value = "是"
                answers.append(answer)
                continue
            for syl in syllabuses[-1:-3:-1]:
                if P_PARENT_SYLLABUS.nexts(clean_txt(syl["title"])):
                    if not (elements := self.pdfinsight.get_elements_by_syllabus(syl)):
                        continue
                    element_results = [CharResult(elements[0], elements[0]["chars"])]
                    answers.append(self.create_result(element_results, value="否", column=answer.schema.name))
                    break
        return answers
