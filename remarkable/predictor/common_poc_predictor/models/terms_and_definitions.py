"""
术语和定义
"""

from copy import deepcopy
from itertools import zip_longest

from remarkable.common.box_util import get_bound_box
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.eltype import ElementClassifier
from remarkable.predictor.models.partial_text import PartialText
from remarkable.predictor.schema_answer import CharResult, OutlineResult, ParagraphResult

P_TERM = PatternCollection(
    [
        r"^\d\s*?术语[和、]定义(?!及缩略语)",
        r"^\d\.\d\s*?术语[和、]定义",
        r"^下列术语和定义适用于本标准",
    ]
)

P_TERM_BREAK = PatternCollection(
    [
        r"^4\s*?(?P<dst>[\u4e00-\u9fa5（）()!]+)",  # 总体要求|缩略语|技术要求|系统架构|建设要求
        r"^\d\.\d\s*?缩略语",
        r"^3\s*?总体要求",
    ]
)

P_SECTION = PatternCollection(
    [
        r"^3\.\d",
        r"^2\.\d",
    ]
)

P_TERM_DESC = PatternCollection(
    [
        r"(?P<dst>[\u4e00-\u9fa5（）()]+)",
    ]
)

P_DEFINITION_DESC = PatternCollection(
    [
        r"^GB/T\s\d+",
    ]
)


P_SPLIT = PatternCollection(
    [
        r"[\u4e00-\u9fa5（）()。]+(?P<dst>3\.\d)$",
        r"[\u4e00-\u9fa5（）()。]+[a-zA-Z\s]+(?P<dst>[\u4e00-\u9fa5（）()。]+)$",
    ]
)

P_SHAPE_SPLIT = PatternCollection(
    [
        r"(?P<serial>3\.\d(\.\d)?)\s?(?P<term>[\u4e00-\u9fa5]+[a-zA-Z\s]+)\s?(?P<definition>[\u4e00-\u9fa5，。（）()、]+)",
    ]
)


class TermsDefinitions(PartialText):
    def predict_schema_answer(self, elements):
        answer_results = []
        keyword_element = self.find_keyword()
        if not keyword_element:
            return []
        if syllabus := self.pdfinsight_syllabus.elt_syllabus_dict.get(keyword_element["index"]):
            if sub_syllabuses := syllabus["children"]:
                for sub_syllabus_idx in sub_syllabuses:
                    sub_syllabus = self.pdfinsight_syllabus.syllabus_dict[sub_syllabus_idx]
                    syllabus_elements = self.find_elements_by_syllabus(sub_syllabus)
                    results = self.parse_answer_from_section(syllabus_elements)
                    answer_results.extend(results)
            else:
                # syllabus_elements = self.find_elements_by_syllabus(syllabus)  # id 364 目录识别错误
                syllabus_elements = self.find_elements_from_all_para()
                groups = self.parse_sections(syllabus_elements)
                for group in groups:
                    results = self.parse_answer_from_section(group)
                    answer_results.extend(results)
        else:
            elements = self.find_elements_from_all_para()
            groups = self.parse_sections(elements)
            for group in groups:
                results = self.parse_answer_from_section(group)
                answer_results.extend(results)
        return answer_results

    def find_keyword(self):
        para_elements = self.get_special_elements(element_types=["PARAGRAPH"])
        for element in para_elements:
            clean_text = clean_txt(element["text"])
            if P_TERM.nexts(clean_text):
                if self.is_contents(clean_text):
                    continue
                return element
        return None

    def parse_answer_from_section(self, group):
        if len(group) < 2:
            return []
        term_para = group[0]
        matcher = P_TERM_DESC.nexts(clean_txt(term_para["text"]))
        if matcher:
            dst_chars = self.get_dst_chars_from_matcher(matcher, term_para)
            term_element_results = [CharResult(term_para, dst_chars)]
        else:
            term_element_results = [ParagraphResult(term_para, term_para["chars"])]
        term_answer_result = self.create_result(term_element_results, column="术语")

        definition_elements = self.filter_definition_element(group[1:])
        page_box = self.pdfinsight.elements_outline(definition_elements)
        definition_element_results = [
            OutlineResult(page_box=page_box, element=definition_elements[0], origin_elements=definition_elements)
        ]
        definition_answer_result = self.create_result(definition_element_results, column="定义")

        answer_result = {
            "术语": [term_answer_result],
            "定义": [definition_answer_result],
        }
        return [answer_result]

    @staticmethod
    def filter_definition_element(elements):
        elements = [element for element in elements if not P_DEFINITION_DESC.nexts(clean_txt(element["text"]))]
        return elements

    @staticmethod
    def parse_sections(elements):
        groups = []
        section_index = []
        for idx, element in enumerate(elements):
            if not ElementClassifier.like_paragraph(element):
                continue
            clean_text = clean_txt(element["text"])
            if P_SECTION.nexts(clean_text):
                section_index.append(idx)

        for start, end in zip_longest(section_index, section_index[1:], fillvalue=len(elements)):
            groups.append(elements[start + 1 : end])  # 忽略章节
        return groups

    def find_elements_by_syllabus(self, syllabus):
        ret = []
        if P_TERM_BREAK.nexts(syllabus["title"]):
            return ret
        start, end = syllabus["range"]
        element_indexes = set()
        for idx in range(start, end):
            elt_type, elt = self.pdfinsight.find_element_by_index(idx)
            if not elt:
                continue
            if elt and elt_type not in ["PAGE_HEADER", "PAGE_FOOTER"] and elt["index"] not in element_indexes:
                ret.append(elt)
                if elt.get("page_merged_paragraph"):
                    for elt_index in elt["page_merged_paragraph"]["paragraph_indices"]:
                        element_indexes.add(elt_index)
                else:
                    element_indexes.add(elt["index"])

        return ret

    def find_elements_from_all_para(self):
        ret = []
        is_start, is_end = False, False
        for elements in self.pdfinsight.element_dict.values():
            for element in elements:
                elt_type, element = self.pdfinsight.find_element_by_index(element.data["index"])
                if not element:
                    continue
                if not ElementClassifier.like_paragraph(element):
                    continue
                if elt_type in ["PAGE_HEADER", "PAGE_FOOTER"]:
                    continue
                clean_text = clean_txt(element["text"])
                if P_TERM.nexts(clean_text):
                    if self.is_contents(clean_text):
                        continue
                    is_start = True
                if is_start and P_TERM_BREAK.nexts(clean_text):
                    is_end = True
                if is_start and not is_end:
                    splited_elements = self.split_element(element)
                    if elt_type == "SHAPE":
                        splited_elements = self.split_shape(element)
                    ret.extend(splited_elements)
                if is_end:
                    break
        return ret

    @staticmethod
    def is_contents(text):
        if text.count(".") > 30:
            return True
        if text.count("…") > 10:
            return True
        return False

    def split_element(self, element):
        """
        因为元素块识别问题 这里需要将一个element拆成两个
        """
        clean_text = clean_txt(element["text"])
        matcher = P_SPLIT.nexts(clean_text)
        if not matcher:
            return [element]
        dst_chars = self.get_dst_chars_from_matcher(matcher, element)
        # start, end = matcher.span("dst")
        first_half_element = deepcopy(element)
        second_half_element = deepcopy(element)
        first_half_element["chars"] = element["chars"][: -len(dst_chars)]
        first_half_element["text"] = element["text"][: -len(dst_chars)]
        first_half_element["outline"] = get_bound_box([char["box"] for char in first_half_element["chars"]])

        second_half_element["chars"] = dst_chars
        second_half_element["text"] = "".join([i["text"] for i in dst_chars])
        second_half_element["index"] = element["index"] + 0.5
        second_half_element["outline"] = get_bound_box([char["box"] for char in dst_chars])

        return [first_half_element, second_half_element]

    def split_shape(self, element):
        ret = []
        clean_text = clean_txt(element["text"])
        matchers = list(P_SHAPE_SPLIT.finditer(clean_text))
        if not matchers:
            return [element]
        for idx, matcher in enumerate(matchers):
            for key in ("serial", "term", "definition"):
                value = matcher.groupdict().get(key, None)
                dst_chars = self.get_chars(element["text"], value, element["chars"], matcher.span(key))
                fake_element = deepcopy(element)
                fake_element["index"] = element["index"] + idx / 100
                fake_element["text"] = "".join([i["text"] for i in dst_chars])
                fake_element["chars"] = dst_chars
                fake_element["outline"] = get_bound_box([char["box"] for char in dst_chars])
                ret.append(fake_element)
        return ret
