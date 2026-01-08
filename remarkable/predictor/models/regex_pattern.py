# -*- coding: utf-8 -*-
import itertools
import re

from remarkable.common.util import clean_txt
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import build_element_result


class BaseMatcher:
    def __init__(self, stop_value=None, is_positive=True):
        self.is_positive = is_positive
        self.stop_value = stop_value
        self.stopped = False

    def match(self, elements):
        raise NotImplementedError


class RegexMatcher(BaseMatcher):
    def __init__(self, pattern, stop_value, is_positive=True, include_non_paragraph=True):
        super(RegexMatcher, self).__init__(stop_value, is_positive)
        self.pattern = pattern
        self.include_non_paragraph = include_non_paragraph

    def match(self, elements):
        paragraph_elements = []
        other_elements = []
        for key, value in itertools.groupby(elements, lambda x: x["class"].lower()):
            if key == "paragraph":
                paragraph_elements.extend(value)
            else:
                other_elements.extend(value)

        result = self.pick_matched(paragraph_elements)
        boolean_result = bool(result)
        stopped = not boolean_result if self.is_positive else boolean_result
        if stopped:
            self.stopped = True
            if not self.is_positive:
                return result
            return []
        if self.is_positive:
            if self.include_non_paragraph:
                return elements
            return result
        return elements

    def pick_matched(self, paragraph_elements, size=1):
        copied_elements = paragraph_elements[:]
        return [i for i in copied_elements[:size] if self.pattern.search(self.preprocess_text(i))]

    @staticmethod
    def filter_elements(elements):
        return [i for i in elements if i["class"] == "PARAGRAPH"]

    @staticmethod
    def preprocess_text(element):
        return clean_txt(element.get("text", ""))


class PartialRegexMatcher(RegexMatcher):
    def preprocess_text(self, element):
        text = clean_txt(element.get("text", ""))
        sentences = text.split(". ")
        filtered = [i for i in sentences if re.search(r"no significant changes?", i) is None]
        return ". ".join(filtered)


class RegexPattern(BaseModel):
    target_element = "paragraph"
    base_all_elements = True

    def __init__(self, options, schema, predictor):
        super(RegexPattern, self).__init__(options, schema, predictor)
        self.matchers = self.create_matchers()
        self.passed_result = self._options["passed_result"]
        self.predict_result = self._options["predict_result"]

    def train(self, dataset, **kwargs):
        pass

    def print_model(self):
        pass

    def predict_schema_answer(self, elements):
        answer_elements = elements
        for matcher in self.matchers:
            answer_elements = matcher.match(answer_elements)
            if matcher.stopped:
                self.predict_result = self.passed_result
                break
        else:
            self.predict_result = self.passed_result

        element_results = [build_element_result(i) for i in answer_elements]
        answer_result = self.create_result(element_results, value=self.get_answer_value())

        return [answer_result]

    def create_matchers(self):
        matchers = []
        for option in self._options["matchers"]:
            matcher = RegexMatcher(option["pattern"], option["stop_value"], is_positive=option["is_positive"])
            matchers.append(matcher)
        return matchers

    def get_answer_value(self):
        if self.predict_result is None:
            return None

        enum_values = self.predictor.get_enum_values(self.schema.type)
        return enum_values[self.predict_result]
