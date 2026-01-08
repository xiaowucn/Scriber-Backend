import re

from remarkable.common.util import clean_txt
from remarkable.predictor.predict import CharResult, ResultOfPredictor

from .model_base import PredictModelBase


class ParaMatch(PredictModelBase):
    model_intro = {
        "doc": "根据正则提取段落内容",
        "name": "段落提取",
        "hide": True,
    }

    def __init__(self, *args, **kwargs):
        super(ParaMatch, self).__init__(*args, **kwargs)
        self.need_training = False
        self.paragraph_pattern = self.config.get("paragraph_pattern", [])
        self.anchor_pattern = self.config.get("anchor_regs", [])
        self.content_pattern = self.config.get("content_pattern", [])

    @classmethod
    def model_template(cls):
        template = {}
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    def train(self, dataset, **kwargs):
        self.model = {}

    def predict(self, elements, **kwargs):
        elements = elements or []
        answer = {}
        for element in elements:
            if element["class"] != "PARAGRAPH":
                continue

            text = clean_txt(element["text"])
            for col in self.columns:
                if not any(re.search(reg, text) for reg in self.paragraph_pattern):
                    continue
                data = []
                if self.content_pattern:
                    for reg in self.content_pattern:
                        matched = re.search(reg, text)
                        if matched:
                            start, end = matched.span("content")
                            chars = element["chars"][start:end]
                            data.append(CharResult(chars, text=matched.group("content"), elt=element))
                            break
                else:
                    data.append(CharResult(element["chars"], text=text, elt=element))
                if not data:
                    continue
                enum_val = self.parse_enum(data)
                answer[col] = ResultOfPredictor(data, value=enum_val)
        return [
            answer,
        ]

    def parse_enum(self, data):
        enum_val = None
        enum = self.config.get("enum")
        if not enum:
            return enum_val
        enum_val = enum.get("default")
        for result in data:
            for val, regs in enum.get("regs", []):
                if any(re.search(reg, result.text) for reg in regs):
                    enum_val = val
                if enum_val:
                    break
        return enum_val
