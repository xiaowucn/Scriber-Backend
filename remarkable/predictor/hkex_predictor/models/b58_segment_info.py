# -*- coding: utf-8 -*-
import re
from collections import Counter

from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import ParagraphResult, TableCellsResult

keywords_pattern = r"information|segment information|segments"

negative_pattern = re.compile(
    rf"No(?! further)[\w\s]*? ({keywords_pattern})[\w\s]* (is|are|be)[\w\s]* (presented|disclosed)", re.I
)
positive_pattern = re.compile(r"reportable|operating|segments?|provides?|competitive|remuneration|enhance", re.I)
list_like_pattern = re.compile(r"([•—–]\s*|\(?[1-9a-zA-Z]{1,3}\s?\)|\d(?=[.\s])|\.\s|(\w+\s)*segment)")
segment_separator_pattern = re.compile(r"\s+(–|—)\s+")


class SegmentInfo(BaseModel):
    base_all_elements = True

    def predict_schema_answer(self, elements):
        elements = [i for i in elements if i["score"] > self.config.get("min_score", 0.1)]
        if not elements:
            return []

        if elements[0]["class"] == "TABLE":
            table_element = elements[0]
            table_cols = {int(i.split("_")[1]) for i in table_element["cells"]}
            max_col = max(table_cols)
            cell_index_list = {c_key for c_key in table_element["cells"] if int(c_key.split("_")[1]) < max_col}
            element_results = [TableCellsResult(table_element, cell_index_list)]
            answer_result = self.create_result(element_results, self.get_answer_value(0))
            return [answer_result]

        paragraphs = [i for i in elements if i["class"] == "PARAGRAPH"]
        negative_paragraphs = self.filter_negative_paragraphs(paragraphs)
        if negative_paragraphs:
            paragraph_results = [ParagraphResult(i, i["chars"]) for i in negative_paragraphs]
            answer_result = self.create_result(paragraph_results, self.get_answer_value(1))
            return [answer_result]

        answer_results = []
        list_like_paragraphs = [i for i in paragraphs[:3] if self.is_like_list(i["text"])]
        positive_paragraphs = [i for i in paragraphs if positive_pattern.search(i["text"])]
        if list_like_paragraphs:
            page = self.pick_page(list_like_paragraphs)
            paragraphs = [i for i in paragraphs if self.is_like_list(i["text"]) and abs(i["page"] - page) <= 1]
            answer = self.build_answer(paragraphs, 0)
        elif positive_paragraphs:
            answer = self.build_answer(positive_paragraphs, 0)
        elif len(paragraphs) == 1:
            if re.search(keywords_pattern, paragraphs[0]["text"]):
                answer = self.build_answer(paragraphs, 0)
            else:
                answer = self.build_answer([], 2)
        else:
            answer = self.build_answer([], 2)
        answer_results.append(answer)
        return answer_results

    def build_answer(self, paragraphs, index):
        value = self.get_answer_value(index)
        paragraph_results = [ParagraphResult(i, i["chars"]) for i in paragraphs]
        return self.create_result(paragraph_results, value=value)

    @staticmethod
    def pick_page(paragraphs):
        counter = Counter(i["page"] for i in paragraphs)
        page, count = counter.most_common(1)[0]
        return page

    @staticmethod
    def filter_negative_paragraphs(paragraphs):
        paragraphs = [i for i in paragraphs if negative_pattern.search(i["text"])]
        return paragraphs

    @staticmethod
    def is_like_list(paragraph):
        return list_like_pattern.match(paragraph) or segment_separator_pattern.search(paragraph)

    def train(self, dataset, **kwargs):
        pass

    def print_model(self):
        pass

    def get_answer_value(self, index=0):
        enum_values = self.predictor.get_enum_values(self.schema.type)
        return enum_values[index]
