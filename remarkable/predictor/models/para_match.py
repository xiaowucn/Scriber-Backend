import collections
import logging
from typing import Iterable, Match

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt, index_in_space_string
from remarkable.predictor.eltype import ElementType
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import (
    CharResult,
    OutlineResult,
    ParagraphResult,
)
from remarkable.predictor.utils import make_pattern

logger = logging.getLogger(__name__)


class ParaMatch(BaseModel):
    target_element = ElementType.PARAGRAPH
    base_all_elements = True
    filter_elements_by_target = True

    def __init__(self, options, schema, predictor):
        super().__init__(options, schema, predictor)
        self.use_crude_answer = self.get_config("use_crude_answer", True)
        self.index_range = self.get_config("index_range", (0, 20))  # 指定元素块的范围
        self.combine_paragraphs = self.get_config("combine_paragraphs", False)  # 拼接多个段落为一个答案, 不分组
        self.split_pattern = self.get_config("split_pattern", None)  # 分隔符
        self.enum_from_multi_element = self.get_config("enum_from_multi_element", False)
        self.force_use_all_elements = self.get_config("force_use_all_elements", False)

    def train(self, dataset, **kwargs):
        pass

    def print_model(self):
        pass

    def target_elements_iter(self, elements) -> Iterable[dict]:
        if (not elements and not self.use_crude_answer) or self.force_use_all_elements:
            amount = self.index_range[1] - self.index_range[0]
            elements = self.pdfinsight.find_elements_near_by(self.index_range[0], amount=amount)
        return filter(self.is_target_element, elements)

    def create_content_result(self, element, matched=None, use_cleaned_text=False):
        chars = element.get("chars", [])
        if isinstance(matched, Match) and "content" in matched.groupdict():
            c_start, c_end = matched.span("content")
            if use_cleaned_text:
                start, end = index_in_space_string(element["text"], (c_start, c_end))
            else:
                start, end = c_start, c_end
            chars = chars[start:end]
            char_result = CharResult(element, chars)
            if self.split_pattern:
                return self.create_split_results(self.split_pattern, char_result)
            return [char_result]

        return [ParagraphResult(element, chars)]

    def match_result_by_prev_anchor(self, current_regs, anchor_regs, element):
        if not current_regs or not anchor_regs:
            return None

        prev_elements = self.pdfinsight.find_elements_near_by(
            element["index"], step=-1, amount=1, aim_types=["PARAGRAPH"]
        )
        if not prev_elements:
            return None
        prev_elt = prev_elements[0]
        if not make_pattern(anchor_regs).nexts(prev_elt.get("text", "")):
            return None

        next_paragraph_matched = make_pattern(current_regs).nexts(element["text"])
        if not next_paragraph_matched:
            return None

        return self.create_content_result(element, next_paragraph_matched)

    def predict_schema_answer(self, elements):
        answers = []
        answer_elements = collections.defaultdict(list)
        for element in elements:
            for col in self.columns:
                clean_text = clean_txt(element["text"])
                neglect_regs = PatternCollection(self.get_config("neglect_regs", column=col))
                anchor_regs = self.get_config("anchor_regs", column=col)
                # 配了current_regs时,锚点匹配在match_result_by_prev_anchor()里做,paragraph_pattern匹配到的答案忽略锚点正则
                current_regs = self.get_config("current_regs", column=col)
                paragraph_pattern = PatternCollection(self.get_config("paragraph_pattern", column=col))

                if neglect_regs.nexts(clean_text):
                    continue

                _result = self.match_result_by_prev_anchor(current_regs, anchor_regs, element)
                if _result:
                    answer_elements[col].extend(_result)
                    continue

                matched = paragraph_pattern.nexts(element["text"])
                cleaned_matched = paragraph_pattern.nexts(clean_text)
                use_cleaned_text = cleaned_matched and not matched
                matched = matched or cleaned_matched
                if matched is None:
                    continue
                element_results = []
                if anchor_regs and not current_regs:
                    prev_elts = self.pdfinsight.find_elements_near_by(
                        element["index"], step=-1, amount=1, aim_types=["PARAGRAPH"]
                    )
                    if not prev_elts:
                        continue
                    prev_elt = prev_elts[0]
                    if make_pattern(anchor_regs).nexts(prev_elt.get("text", "")):
                        if self.get_config("include_anchor", default=False, column=col):
                            element_results.extend(self.create_content_result(prev_elt))
                        element_results.extend(self.create_content_result(element, matched, use_cleaned_text))
                else:
                    element_results.extend(self.create_content_result(element, matched, use_cleaned_text))

                if element_results:
                    answer_elements[col].extend(element_results)

            if not self.multi_elements and answer_elements:  # 多元素块
                break
        for col, answer_element in answer_elements.items():
            if self.enum_from_multi_element:
                answer_element.sort(key=lambda x: x.element["index"])
                answer = {col: [self.create_result(answer_element, column=col)]}
                answers.append(answer)
            else:
                if self.combine_paragraphs:
                    # 拼接多个段落为一个答案, 不分组(适用于PDFinsight把一个段落拆成多个元素块的情况)
                    answers.append({col: [self.create_result([self.merge_paragraphs(answer_element)], column=col)]})
                    continue
                for i in answer_element:
                    answer = {col: [self.create_result([i], column=col)]}
                    answers.append(answer)
        return answers

    def merge_paragraphs(self, para_result: list[ParagraphResult | CharResult]):
        # 合并多个连续段落为整个框
        para_result = sorted(para_result, key=lambda x: x.element["index"])
        elements = []
        start = para_result[0].element["index"]
        end = para_result[-1].element["index"] + 1
        element_indexes = set()
        for idx in range(start, end):
            elt_type, elt = self.pdfinsight.find_element_by_index(idx)
            if elt and elt_type not in ["PAGE_HEADER", "PAGE_FOOTER"] and elt["index"] not in element_indexes:
                elements.append(elt)
                if elt.get("page_merged_paragraph"):
                    for elt_index in elt["page_merged_paragraph"]["paragraph_indices"]:
                        element_indexes.add(elt_index)
                else:
                    element_indexes.add(elt["index"])
        return OutlineResult(self.pdfinsight.elements_outline(elements), origin_elements=elements)
