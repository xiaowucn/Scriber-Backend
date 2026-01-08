from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.models.partial_text import PartialText
from remarkable.predictor.schema_answer import CharResult

FULL_NAME_PATTERNS = [r"(?P<dst>\w*)，?\s?([男女]士?|先生)", r"(?P<dst>\w*)[：:]\d{4}年.*出?生人?"]
DIRECTOR_INFO_PATTERN = [r"(?P<dst>董事|监事|高级?管[理人员]*|核心(技术)?人员)"]
SPECIAL_FULL_NAME_PATTERNS = [r"(?P<dst>\w*)[:：]"]
INVALID_FULL_NAME_PATTERNS = [r"\d{4}\s*?年出生"]


class DirectorInformation(PartialText):
    """
    董监高核人员信息
    """

    def predict_schema_answer(self, elements):
        elements = self.fix_elements(elements)
        answer_results = super(DirectorInformation, self).predict_schema_answer(elements)
        # 从标题中对[董监高身份]进行补充
        ret = []
        for answer_result in answer_results:
            fix_column = "董监高身份"
            if "姓名" in answer_result:
                name = self.fix_name_answer(answer_result.get("姓名"))
                if not name:
                    continue
                answer_result["姓名"] = name
                if fix_column not in answer_result:
                    element = name[0].relative_elements[0]
                    matcher, syllabus_element = self.find_from_title_element(element, DIRECTOR_INFO_PATTERN, step=2)
                    if matcher:
                        chars = self.get_dst_chars_from_matcher(matcher, syllabus_element)
                        element_results = [CharResult(syllabus_element, chars)]
                        answer_result[fix_column] = [self.create_result(element_results, column=fix_column)]
            ret.append(answer_result)

        return ret

    def fix_name_answer(self, name_answers):
        ret = []
        for answer in name_answers:
            element = answer.relative_elements[0]
            if PatternCollection(INVALID_FULL_NAME_PATTERNS).nexts(clean_txt(answer.text)):
                continue
            matcher = PatternCollection(SPECIAL_FULL_NAME_PATTERNS).nexts(answer.text)
            if not matcher:
                ret.append(answer)
                continue
            answer_text = matcher.groupdict()["dst"]
            span = matcher.span("dst")
            chars = self.get_dst_chars_from_text(answer_text, element, span)
            if not chars:
                continue
            ret.append(self.create_result([CharResult(element, chars)], column="姓名"))

        return ret

    def find_from_title_element(self, element, patterns, step=1):
        if step <= 0:
            return None, None
        title_element = self.get_title_element(element)
        if not title_element:
            return None, None
        match = PatternCollection(patterns).nexts(clean_txt(title_element["text"]))
        if match:
            return match, title_element

        return self.find_from_title_element(title_element, patterns, step - 1)

    def fix_elements(self, elements):
        """
        对初步定位得到的elements进行修正
        :param elements:
        :return:
        """
        sylls = set()
        distinct_index = set()
        for e in elements:
            sylls.add(e["syllabus"])
            distinct_index.add(e["index"])

        sylls = sorted(sylls)
        for syll in sylls:
            syll_dict = self.pdfinsight_syllabus.syllabus_dict.get(syll)
            if not syll_dict:
                continue
            for index in range(*syll_dict["range"]):
                etype, ele = self.pdfinsight.find_element_by_index(index)
                if not ele:
                    continue
                element_index = ele["index"]
                if etype != "PARAGRAPH" or element_index in distinct_index:
                    continue
                if PatternCollection(FULL_NAME_PATTERNS).nexts(clean_txt(ele["text"])):
                    elements.append(ele)
                    distinct_index.add(element_index)

        elements = sorted(elements, key=lambda x: x["index"])
        return elements
