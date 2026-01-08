import re

from remarkable.common.util import clean_txt
from remarkable.predictor.predict import ParaResult, ResultOfPredictor

from .model_base import PredictModelBase


class EnumValue(PredictModelBase):
    model_intro = {
        "doc": "枚举类型的选项预测",
        "name": "枚举选项",
        "hide": True,
    }

    def __init__(self, *args, **kwargs):
        super(EnumValue, self).__init__(*args, **kwargs)
        self.need_training = False

    @classmethod
    def model_template(cls):
        template = {
            "deny_regs": [r"(?P<dst>.*)"],
        }
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    def train(self, dataset, **kwargs):
        model = {}
        self.model = model

    def predict(self, elements, **kwargs):
        score = kwargs.get("score", 0)
        if score < self.config.get("threshold", 0.5):
            return []
        answers = []
        elements = elements or []
        for element in elements:
            answer = {}
            for col in self.columns:
                if element["class"] == "PARAGRAPH":
                    answer[col] = ResultOfPredictor([ParaResult(element["chars"], element)], score=element.get("score"))
            answers.append(answer)
        return answers

    def predict_with_elements(self, crude_answers, **kwargs):
        predict_results = []
        if self.same_elt_with_parent:
            candidates = kwargs.get("candidates", {})
        else:
            candidates = self._get_element_candidates(
                crude_answers,
                self.config["path"],
                priors=self.config.get("element_candidate_priors", []),
                limit=self.config.get("element_candidate_count", 10),
            )
        for item in candidates:
            etype, ele = self.pdfinsight.find_element_by_index(item["element_index"])
            answers = self.predict([ele], score=item.get("score", 0), **kwargs)
            if answers:
                predict_results.append((ele, answers))
        if not predict_results and self.config.get("default_value"):
            answer = {}
            for col in self.columns:
                answer[col] = ResultOfPredictor([])
            predict_results.append(
                (
                    None,
                    [
                        answer,
                    ],
                )
            )
        deny_regs = self.config.get("deny_regs", [])
        results = []
        col = self.config.get("path")[-1]
        enum_values = self.get_enum_values(self.config["path"][0], col)
        deny_value = enum_values[-1] if enum_values else "否"
        allow_value = enum_values[0] if enum_values else "是"
        for ele, answer in predict_results:
            if not ele:
                continue
            content = clean_txt(ele.get("text", ""))
            if any(re.search(reg, content) for reg in deny_regs):
                answer[0][col].value = deny_value
                results.append((ele, answer))
                break
        if not results and predict_results:
            allow_ele, answer = predict_results[0]
            answer[0][col].value = self.config["default_value"] if self.config.get("default_value") else allow_value
            results.append((allow_ele, answer))
        return results
