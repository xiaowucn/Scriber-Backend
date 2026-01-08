from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.schema_answer import OutlineResult


class SplitByReg(SyllabusEltV2):
    """
    开放日和临时开发日经常会放在一个单元格里
    kv模型没有办法直接区分
    加了一个后处理 对于kv预测的结果使用split_pattern切分
    上半段是开放日 下半段是临时开放日
    """

    def predict_schema_answer(self, elements):
        ret = []
        parent_answer_results = super(SplitByReg, self).predict_schema_answer(elements)
        answer_location = self.config.get("answer_location", "after")
        split_pattern = PatternCollection(self.config.get("split_pattern", []))
        if not parent_answer_results:
            return ret
        for answer_result in parent_answer_results:
            column = answer_result.key_path[-1]
            text = clean_txt(answer_result.text)
            if not split_pattern.nexts(text):
                ret.append(answer_result)
                continue
            element_result = answer_result.element_results[0]
            all_elements = element_result.origin_elements or []
            after_element_index = all_elements[-1]["index"]
            after_element_index = self.get_split_index(all_elements, after_element_index, split_pattern)
            if answer_location == "after":
                new_answer_elements = [element for element in all_elements if element["index"] > after_element_index]
            else:
                new_answer_elements = [element for element in all_elements if element["index"] < after_element_index]
            if not new_answer_elements:
                return answer_result
            para_range = {"range": (new_answer_elements[0]["index"], new_answer_elements[-1]["index"] + 1)}
            answer_result = self.gen_answer(new_answer_elements, para_range, column)
            ret.append(answer_result)
        return ret

    def gen_answer(self, new_answer_elements, para_range, column):
        page_box = PdfinsightSyllabus.syl_outline(
            para_range, self.pdfinsight, include_title=self.config.get("include_title", True)
        )
        element_results = [
            OutlineResult(page_box=page_box, element=new_answer_elements[0], origin_elements=new_answer_elements)
        ]
        answer_result = self.create_result(element_results, column=column)
        return answer_result

    @staticmethod
    def get_split_index(all_elements, split_index, pattern):
        for element in all_elements:
            if element["class"] != "PARAGRAPH":
                continue
            if pattern.nexts(clean_txt(element["text"])):
                split_index = element["index"]
                break
        return split_index
