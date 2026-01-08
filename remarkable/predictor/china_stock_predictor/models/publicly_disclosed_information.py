from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.schema_answer import ParagraphResult

special_pattern = PatternCollection(
    [
        r"公开披露的基金信息包括",
    ]
)


class PubliclyDisclosedInformation(SyllabusEltV2):
    def predict_schema_answer(self, elements):
        self.load_model_data()
        answer_results = []
        for col in self.columns:
            model_data = self.get_model_data(col)
            if not model_data:
                return answer_results
            element_results = []
            aim_syllabuses = self.get_aim_syllabus(model_data)
            for aim_syllabuse in aim_syllabuses:
                start, end = aim_syllabuse["range"]
                for index in range(start, end):
                    _, element = self.pdfinsight.find_element_by_index(index)
                    if element["class"] != "PARAGRAPH":
                        continue
                    if special_pattern.nexts(clean_txt(element["text"])):
                        element_results.append(ParagraphResult(element, element["chars"]))
                        break

                for index in aim_syllabuse["children"]:
                    syllabus = self.pdfinsight_syllabus.syllabus_dict[index]
                    _, element = self.pdfinsight.find_element_by_index(syllabus["element"])
                    element_results.append(ParagraphResult(element, element["chars"]))

            answer_result = self.create_result(element_results, column=col)
            answer_results.append(answer_result)
        return answer_results
