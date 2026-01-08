from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.models.syllabus_elt import SyllabusElt
from remarkable.predictor.schema_answer import OutlineResult, ParagraphResult

special_pattern = PatternCollection(
    [
        r"完全复制",
    ]
)


class PerfectCopyMethod(SyllabusElt):
    def predict_schema_answer(self, elements):
        answer_results = []
        for col in self.columns:
            model_data = self.get_model_data(col)
            if not model_data:
                return answer_results
            aim_syllabuses = self.get_aim_syllabus(self.revise_model(model_data))
            for aim_syllabuse in aim_syllabuses:
                special_paras, from_second_child = self.get_title_children_paras(aim_syllabuse)
                if special_paras:
                    page_box = self.pdfinsight.elements_outline(special_paras)
                    element_results = [
                        OutlineResult(page_box=page_box, element=special_paras[0], origin_elements=special_paras)
                    ]
                    answer_results.append(self.create_result(element_results, column=col))

                if not aim_syllabuse["children"]:
                    continue
                _, end = aim_syllabuse["range"]
                next_answer = []
                start_element_index = self.pdfinsight_syllabus.syllabus_dict[aim_syllabuse["children"][0]]["element"]
                if from_second_child:
                    start_element_index = self.pdfinsight_syllabus.syllabus_dict[aim_syllabuse["children"][1]][
                        "element"
                    ]
                for index in range(start_element_index, end):
                    _, element = self.pdfinsight.find_element_by_index(index)
                    if element["class"] != "PARAGRAPH":
                        continue
                    if special_pattern.nexts(clean_txt(element["text"])):
                        next_answer.append(ParagraphResult(element, element["chars"]))
                        break
                if next_answer:
                    answer_results.append(self.create_result(next_answer, column=col))
        return answer_results

    def get_title_children_paras(self, aim_syllabuse):
        # 获取章节标题和第一个子章节之间的元素块
        ret = []
        from_second_child = False
        if not aim_syllabuse["children"]:
            return ret, from_second_child
        first_child = aim_syllabuse["children"][0]
        first_syll = self.pdfinsight_syllabus.syllabus_dict[first_child]
        for index in range(aim_syllabuse["element"] + 1, first_syll["element"]):
            _, element = self.pdfinsight.find_element_by_index(index)
            if element["class"] != "PARAGRAPH":
                continue
            ret.append(element)
        if not ret:
            second_child = aim_syllabuse["children"][1]
            second_syll = self.pdfinsight_syllabus.syllabus_dict[second_child]
            for index in range(first_syll["element"] + 1, second_syll["element"]):
                _, element = self.pdfinsight.find_element_by_index(index)
                if element["class"] != "PARAGRAPH":
                    continue
                ret.append(element)
            if ret:
                from_second_child = True
        if self.has_special_pattern(ret):
            return ret, from_second_child
        return [], from_second_child

    @staticmethod
    def has_special_pattern(elements):
        has_correct_answer = False
        for element in elements:
            if special_pattern.nexts(clean_txt(element["text"])):
                has_correct_answer = True
                break
        return has_correct_answer
