"""远程调用预测 API
输入：
pdfinsight, 完整 schema, path

输出：
[
    {
        A: [answer_item, ]
        B: [
            {
                C: [answer_item, ],
                D: [answer_item, ],
            }
        ]
    },
    ...
]

answer_item:
{
    "boxes": [
        {
            "text": "",
            "page": page,
            "outline": (top, left, bottom, right),
        }
    ],
    "enum": "",
}

"""

import json
import logging

import requests

from remarkable.predictor.predict import CharResult, ResultOfPredictor

from .model_base import PredictModelBase


class RemoteCall(PredictModelBase):
    model_intro = {
        "doc": """
        远程调用外部分析接口
        """,
        "name": "远程调用模型",
    }

    def __init__(self, *args, **kwargs):
        super(RemoteCall, self).__init__(*args, **kwargs)
        self.base_on_crude_element = False
        self.need_training = False

    @classmethod
    def model_template(cls):
        template = {
            "api": "",
        }
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    def train(self, dataset, **kwargs):
        return

    def predict(self, elements, **kwargs):
        answers = []
        try:
            api = self.config.get("api")
            if not self.config.get("api"):
                raise Exception("can't find api address in config")
            data = {
                "schema": json.dumps(self.mold.data),
                "path": json.dumps(self.config["path"]),
            }
            with open(self.pdfinsight.path, "rb") as file_obj:
                files = {
                    "pdfinsight": file_obj,
                }
                response = requests.post(api, data, files=files)
            if not response.ok:
                raise Exception("remote call return %s, with body: %s" % (response.status_code, response.text))
            answers = self.build_answer_from_data(response.json())
        except Exception as ex:
            logging.error(ex)
        return self.unify_output(answers)

    def unify_output(self, answers):
        if self.leaf:
            return [{self.columns[0]: answer} for answer in answers]
        return answers

    @staticmethod
    def is_answer_item(item):
        return isinstance(item, dict) and "boxes" in item

    def build_answer_from_data(self, data):
        answers = []
        for item in data:
            if self.is_answer_item(item):
                _answer = self.build_answer_item(item)
            elif isinstance(item, dict):
                _answer = self.build_answer_group(item)
            else:
                _answer = None
            if _answer:
                answers.append(_answer)
        return answers

    def build_answer_group(self, group):
        answer = {}
        for key, data in group.items():
            answer[key] = self.build_answer_from_data(data)
        return answer if any(answer.values()) else None

    def build_answer_item(self, item):
        if not item.get("boxes"):
            return None
        chars = []
        texts = []
        for box in item["boxes"]:
            ele, _chars = self.pdfinsight.find_chars_by_outline(box["page"], box["outline"])
            chars.extend(_chars)
            texts.append(box["text"])
        return ResultOfPredictor([CharResult(chars, text="\n".join(texts))], value=item.get("enum"))
