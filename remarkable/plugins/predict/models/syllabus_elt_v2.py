import re
from collections import Counter

from remarkable.common.util import clean_txt
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.predict.common import find_syl_by_elt_index
from remarkable.predictor.predict import CharResult, ResultOfPredictor

from .model_base import PredictModelBase


class SyllabusEltV2(PredictModelBase):
    model_intro = {"doc": "按章节提取整个内容", "name": "整个章节", "hide": True}

    def __init__(self, *args, **kwargs):
        super(SyllabusEltV2, self).__init__(*args, **kwargs)
        self.base_on_crude_element = False
        self.order_by = self.config.get("order_by", "index")
        self.reverse = self.config.get("reverse", False)
        self.equal_mode = self.config.get("equal_mode", False)

    @classmethod
    def model_template(cls):
        template = {}
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    def train(self, dataset, **kwargs):
        model = {}
        dataset = dataset or []
        for item in dataset:
            for col in self.columns:
                leaves = item.answer.get(col, {}).values() if not self.leaf else [item.answer]
                for leaf in leaves:
                    if leaf.data is None:
                        continue
                    _features = self.extract_feature(item, leaf.data)
                    model.setdefault(col, Counter()).update(_features)
        self.model = model

    @staticmethod
    def extract_feature(anwser_item, answer):
        """
        统计标注内容对应的章节标题
        """
        features = Counter()
        for answer_data in answer["data"]:
            if not answer_data["elements"]:
                continue
            for elt_idx in answer_data["elements"]:
                syllabuses = find_syl_by_elt_index(elt_idx, anwser_item.data.get("syllabuses", []))
                if not syllabuses:
                    continue
                aim_syl = syllabuses[-1]
                clear_syl = clear_syl_title(aim_syl["title"])
                features.update(
                    [
                        clear_syl,
                    ]
                )
        return features

    def predict(self, elements, **kwargs):
        answer = {}
        for col in self.columns:
            model = self.model.get(col)
            if not model:
                continue
            aim_syl = None
            for title, _ in model.most_common():
                syls = self.pdfinsight.find_sylls_by_clear_title(
                    title, order_by=self.order_by, reverse=self.reverse, equal_mode=self.equal_mode
                )
                if syls:
                    aim_syl = syls[0]
                    break
            if not aim_syl:
                continue
            chars, content_l = [], []
            for idx in range(*aim_syl["range"]):
                elt_typ, elt = self.pdfinsight.find_element_by_index(idx)
                if not elt:
                    continue
                if elt_typ == "PARAGRAPH":
                    chars.extend(elt["chars"])
                    content_l.append(clean_txt(elt["text"]))

            if chars:
                data = [
                    CharResult(chars, text="".join(content_l)),
                ]
                answer[col] = ResultOfPredictor(
                    data=data,
                    value=self.parse_enum(
                        data,
                    ),
                    score=1,
                )
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
