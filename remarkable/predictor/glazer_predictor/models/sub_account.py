import re

from utensils.util import clean_txt

from remarkable.common.pattern import MatchMulti, NeglectPattern, PatternCollection
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.predict.common import is_table_elt
from remarkable.plugins.predict.models.sse.other_related_agencies import clean_text
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import CharResult, OutlineResult

P_FIX = re.compile(r"\^")
P_FIX_1 = re.compile(r"\$")

NEGLECT_SYLLABUS_PATTERNS = NeglectPattern(
    match=MatchMulti.compile(
        "有息(负债|债务)(分析|情况)$",
        operator=any,
    ),
    unmatch=MatchMulti.compile(
        r"^$",
        operator=any,
    ),
)

NEGLECT_PATTERNS = NeglectPattern(
    match=MatchMulti.compile(
        "募集说明书$",
        operator=any,
    ),
    unmatch=MatchMulti.compile(
        r"^$",
        operator=any,
    ),
)


class SubAccount(BaseModel):
    def __init__(self, options, schema, predictor=None):
        super().__init__(options, schema, predictor=predictor)
        self.sub_patterns = PatternCollection(self.get_config("sub_patterns", []))
        self.sub_total_patterns = self.get_config("sub_total_patterns", [])

    def train(self, dataset, **kwargs):
        pass

    def predict_schema_answer(self, elements):
        answer_results = []

        unique_elements = []
        unique_element_index = set()
        invalid_index = []
        for ele in elements:
            if NEGLECT_SYLLABUS_PATTERNS.search(clear_syl_title(ele["text"])):
                sub_syllabuses = self.pdfinsight.find_syllabuses_by_index(ele["index"])
                if sub_syllabuses:
                    start, end = sub_syllabuses[-1]["range"]
                    invalid_index.extend(list(range(start, end)))
                    continue

            if ele["index"] in invalid_index:
                continue

            if NEGLECT_PATTERNS.search(clean_txt(ele["text"])):
                continue

            if ele["index"] not in unique_element_index:
                unique_elements.append(ele)
                unique_element_index.add(ele["index"])

        if len(unique_elements) < 2:
            return answer_results
        self.find_sub_and_content(unique_elements, answer_results)
        if not answer_results:
            self.find_sub_and_content_in_one_element(unique_elements, answer_results)

        return answer_results

    def find_sub_and_content(self, elements, answer_results):
        sub_element, rest_elements = self.find_sub_element(elements)
        if not sub_element or not rest_elements:
            return
        content_elements, rest_elements = self.find_content_elements(sub_element, rest_elements)
        if content_elements:
            answer_results.append(
                {
                    "科目名称": [self.build_answer([sub_element], "科目名称")],
                    "分析内容": [self.build_answer(content_elements, "分析内容")],
                }
            )
        if rest_elements and rest_elements != elements:
            self.find_sub_and_content(rest_elements, answer_results)

    def find_sub_element(self, elements):
        for idx, element in enumerate(elements):
            if is_table_elt(element):
                continue
            if self.sub_patterns.nexts(clear_syl_title(element["text"])):
                content_patterns = [P_FIX.sub("", x) for x in self.sub_patterns.patterns]
                return self.get_element_with_content_chars(element, content_patterns), elements[idx + 1 :]
        return [], elements

    def find_content_elements(self, sub_element, elements):
        content_elements = []

        sub_syllabuses = self.pdfinsight.find_syllabuses_by_index(sub_element["index"])
        elements_range = []
        if sub_syllabuses:
            start, end = sub_syllabuses[-1]["range"]
            elements_range = list(range(start, end))

        for idx, element in enumerate(elements):
            if is_table_elt(element):
                content_elements.append(element)
                continue
            text = clear_syl_title(element["text"])
            if self.sub_patterns.nexts(text):
                if element["index"] in elements_range:
                    content_elements.append(element)
                    continue

                return content_elements, elements[idx:]
            if self.sub_total_patterns.search(clean_txt(element["text"])):
                return content_elements, elements[idx:]
            content_elements.append(element)
        return content_elements, []

    def build_answer(self, elements, column):
        page_box = self.pdfinsight.elements_outline(elements)
        element_results = [OutlineResult(page_box=page_box, element=elements[0], origin_elements=elements)]
        answer_result = self.create_result(element_results, column=column)
        return answer_result

    def find_sub_and_content_in_one_element(self, elements, answer_results):
        patterns = PatternCollection([P_FIX_1.sub("[:：](?P<dst>.*)", x) for x in self.sub_patterns.patterns])

        for element in elements:
            if is_table_elt(element):
                continue
            text = clean_text(element["text"])
            matcher = patterns.nexts(text)
            if not matcher:
                continue
            sub_chars = self.get_dst_chars_from_matcher(matcher, element, group_key="content")
            content_chars = self.get_dst_chars_from_matcher(matcher, element)

            answer_results.append(
                {
                    "科目名称": [self.create_result([CharResult(element, sub_chars)], column="科目名称")],
                    "分析内容": [self.create_result([CharResult(element, content_chars)], column="分析内容")],
                }
            )
        return answer_results
