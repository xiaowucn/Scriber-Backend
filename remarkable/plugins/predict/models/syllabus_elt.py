"""
提取整个章节的内容
模型：统计答案对应的章节标题
特殊情况：暂无

model 示意:
{
    "对上市公司的影响": Counter({
        "对上市公司的影响": 21,
        "控投股东提供财务资助对上市公司的影响": 7,
        ...
    }),
    ...
}

"""

import re
from collections import Counter

from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.predict.common import find_syl_by_elt_index
from remarkable.predictor.predict import CharResult, ResultOfPredictor

from .model_base import PredictModelBase


def text2pattern(text):
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"^[\d一二三四五六七八九十:、]+", "", text)  # 去掉标号
    return text


class SyllabusElt(PredictModelBase):
    model_intro = {"doc": "按章节提取整个内容", "name": "整个章节"}

    def __init__(self, *args, **kwargs):
        super(SyllabusElt, self).__init__(*args, **kwargs)
        self.base_on_crude_element = False

    @classmethod
    def model_template(cls):
        template = {}
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    @staticmethod
    def extract_feature(anser_item, answer):
        sylls = anser_item.data.get("syllabuses", [])
        features = Counter()
        for answer_data in answer["data"]:
            if not answer_data["elements"]:
                continue
            aim_syls = find_syl_by_elt_index(answer_data["elements"][0], sylls)
            if aim_syls:
                clear_syl = clear_syl_title(aim_syls[-1]["title"])
                features.update(
                    [
                        clear_syl,
                    ]
                )
        return features

    def train(self, dataset, **kwargs):
        model = {}
        # print('~~~~~', self.config, self.columns)
        for item in dataset:
            # 章节标题
            for col in self.columns:
                leaves = item.answer.get(col, {}).values() if not self.leaf else [item.answer]
                for leaf in leaves:
                    if leaf.data is None:
                        continue
                    _features = self.extract_feature(item, leaf.data)
                    model.setdefault(col, Counter()).update(_features)
        self.model = model

    def predict(self, elements, **kwargs):
        # print('~~~~~', self.config, self.columns)
        answer = {}
        for col in self.columns:
            _model = self.model.get(col)
            if not _model:
                continue
            aim_syl = None
            for _title, _cnt in _model.most_common():
                syls = self.pdfinsight.find_sylls_by_pattern(
                    [
                        re.compile(_title),
                    ]
                )
                aim_syl = syls[0] if syls else None
                if aim_syl:
                    break
            # print('******', col, aim_syl)
            if not aim_syl:
                continue
            chars = []
            start, end = aim_syl["range"]
            for idx in range(start + 1, end):
                elt_typ, elt = self.pdfinsight.find_element_by_index(idx)
                if elt_typ == "PARAGRAPH":
                    chars.extend(elt["chars"])
            if chars:
                answer[col] = ResultOfPredictor([CharResult(chars)], score=1)
        return [answer]
