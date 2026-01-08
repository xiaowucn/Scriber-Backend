# -*- coding: utf-8 -*-
import itertools
import logging
import re

from remarkable.common.util import clean_txt
from remarkable.plugins.predict.common import get_element_candidates
from remarkable.plugins.predict.models.model_base import PredictModelBase
from remarkable.predictor.predict import ResultOfPredictor, build_element_result


class BasePredictor:
    def __init__(self, predict_result=None, is_positive=True):
        self.is_positive = is_positive
        self.predict_result = predict_result

    def predict(self, predict_answer):
        raise NotImplementedError


class RegPredictor(BasePredictor):
    def __init__(self, pattern, predict_result, is_positive=True, include_non_paragraph=True):
        super(RegPredictor, self).__init__(predict_result, is_positive)
        self.pattern = pattern
        self.include_non_paragraph = include_non_paragraph

    def predict(self, predict_answer):
        paragraph_elements = []
        other_elements = []
        for key, value in itertools.groupby(predict_answer["elements"], lambda x: x["element_type"].lower()):
            if key == "paragraph":
                paragraph_elements.extend(value)
            else:
                other_elements.extend(value)

        result = self.pick_matched(paragraph_elements)
        boolean_result = bool(result)
        passed = boolean_result if self.is_positive else not boolean_result
        if passed:
            if self.is_positive:
                if self.include_non_paragraph:
                    predict_answer["elements"] = result + other_elements
                else:
                    predict_answer["elements"] = result
            else:
                pass
        else:
            if not self.is_positive:
                predict_answer["elements"] = result
            else:
                predict_answer["elements"] = []
            predict_answer["predict_result"] = self.predict_result

        return passed

    def pick_matched(self, paragraph_elements, size=1):
        copied_elements = paragraph_elements[:]
        return [i for i in copied_elements[:size] if self.pattern.search(self.preprocess_text(i))]

    @staticmethod
    def filter_elements(elements):
        return [i for i in elements if i["element_type"] == "PARAGRAPH"]

    @staticmethod
    def preprocess_text(element):
        return clean_txt(element.get("text", ""))


class PartialRegPredictor(RegPredictor):
    def preprocess_text(self, element):
        text = clean_txt(element.get("text", ""))
        sentences = text.split(". ")
        filtered = [i for i in sentences if re.search(r"no significant changes?", i) is None]
        return ". ".join(filtered)


class ScorePredictor(BasePredictor):
    def __init__(self, threshold, predict_result):
        super(ScorePredictor, self).__init__(predict_result)
        self.threshold = threshold

    def predict(self, predict_answer):
        result = []
        for candidate in predict_answer["elements"]:
            element_type = candidate["element_type"].lower()
            if element_type in ["page_header", "page_footer"]:
                element_type = "paragraph"
            threshold = self.threshold[element_type]
            if candidate["score"] >= threshold:
                result.append(candidate)
        boolean_result = bool(result)
        passed = boolean_result if self.is_positive else not boolean_result
        predict_answer["elements"] = result
        if not passed:
            predict_answer["predict_result"] = self.predict_result
        return passed

    def update_threshold(self, threshold):
        self.threshold = threshold

    def __str__(self):
        return f"ScorePredictor<{self.threshold}>"


class RegexPattern(PredictModelBase):
    @classmethod
    def model_template(cls):
        pass

    need_training = False
    base_on_crude_element = True

    def __init__(self, *args, **kwargs):
        super(RegexPattern, self).__init__(*args, **kwargs)
        self.patterns = self.config["patterns"]

    def train(self, dataset, **kwargs):
        pass

    def print_model(self):
        pass

    def predict(self, elements, **kwargs):
        predict_answer = {"elements": elements, "predict_result": None}
        for pattern in self.patterns:
            passed = pattern.predict(predict_answer)
            if not passed:
                break
        else:
            predict_answer["predict_result"] = self.config["passed_result"]

        answers = self.build_answer(predict_answer)
        answer_element = predict_answer["elements"][0]["element"] if predict_answer["elements"] else None
        return [(answer_element, answers)]

    def build_answer(self, predict_answer):
        answers = []
        answer = {}
        for column in self.columns:
            column_answer = ResultOfPredictor([])
            if predict_answer["predict_result"] is not None:
                col = self.config.get("path")[-1]
                enum_values = self.schema.get_enum_values(self.config["path"][0], col)
                if enum_values:
                    column_answer.value = enum_values[predict_answer["predict_result"]]
            if predict_answer["elements"]:
                picked_elements = self.pick_elements(predict_answer["elements"])
                column_answer.data = [build_element_result(i["element"]) for i in picked_elements]
            answer[column] = column_answer
            answers.append(answer)
        return answers

    @staticmethod
    def pick_elements(elements):
        return elements

    def predict_with_elements(self, crude_answers, **kwargs):
        elements = get_element_candidates(
            crude_answers,
            self.config["path"],
            priors=self.config.get("element_candidate_priors", []),
            limit=self.config.get("element_candidate_count", 10),
        )
        valid_elements = []
        for i in elements:
            _, element = self.pdfinsight.find_element_by_index(i["element_index"])
            if element is not None:
                i["element"] = element
                valid_elements.append(i)
            else:
                logging.warning("Can't find pdfinsight element by element_index.")
        return self.predict(valid_elements)
