import re
from collections import Counter

from remarkable.common.util import clean_txt
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.predict.common import find_syl_by_elt_index
from remarkable.plugins.predict.models.model_base import PredictModelBase
from remarkable.predictor.predict import CharResult, ResultOfPredictor


class EquityPledge(PredictModelBase):
    model_intro = {
        "doc": "",
        "name": "控股股东、实际控制人股权质押情况",
        "hide": True,
    }

    def __init__(self, *args, **kwargs):
        super(EquityPledge, self).__init__(*args, **kwargs)
        self.base_on_crude_element = False

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

    def predict(self, elements, **kwargs):
        answer = {}
        for col in self.columns:
            col_model = self.model.get(col)
            if not col_model:
                continue
            aim_syl = []
            for title, _ in col_model.most_common():
                syls = self.pdfinsight.find_sylls_by_clear_title(title, order_by="level", reverse=True, equal_mode=True)
                if not syls:
                    continue
                aim_syl.append(syls[0])
            data = []
            for syl in aim_syl:
                res = self.section(syl)
                if res:
                    data.append(res)
            enum_val = self.parse_enum(data)
            answer[col] = ResultOfPredictor(data, value=enum_val, score=1)
        return [
            answer,
        ]

    def section(self, syl):
        chars_l, content_l = [], []
        keywords = ["质押"]
        if any(kw in clean_txt(syl["title"]) for kw in keywords):
            for idx in range(*syl["range"]):
                elt_typ, elt = self.pdfinsight.find_element_by_index(idx)
                if elt_typ == "PARAGRAPH":
                    chars_l.extend(elt["chars"])
                    content_l.append(clean_txt(elt["text"]))
        else:
            for idx in range(*syl["range"]):
                elt_typ, elt = self.pdfinsight.find_element_by_index(idx)
                if elt_typ == "PARAGRAPH":
                    if any(kw in clean_txt(elt["text"]) for kw in keywords):
                        chars_l.extend(elt["chars"])
                        content_l.append(clean_txt(elt["text"]))
        result = CharResult(chars_l, text="".join(content_l)) if chars_l else None
        return result

    @staticmethod
    def parse_enum(data):
        regs = [r"(不存在|没有).*质押"]
        enum_val = "是"
        for result in data:
            if any(re.search(reg, result.text) for reg in regs):
                enum_val = "否"
        return enum_val

    @staticmethod
    def extract_feature(anser_item, answer):
        """
        统计标注内容对应的章节标题
        """
        features = Counter()
        for answer_data in answer["data"]:
            if not answer_data["elements"]:
                continue
            for elt_idx in answer_data["elements"]:
                syllabuses = find_syl_by_elt_index(elt_idx, anser_item.data.get("syllabuses", []))
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
