import re
from collections import Counter

from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.plugins.predict.models.model_base import PredictModelBase
from remarkable.plugins.predict.models.partial_text_v3 import PartialTextV3
from remarkable.plugins.predict.models.table_kv import KeyValueTable

split_title_p = re.compile(r":|：")


def clean_text(text):
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"^[\d\(（一二三四五六七八九十]+[:：、\-—\.]", "", text)  # 去掉标号
    return text


class OtherRelatedAgencies(PredictModelBase):
    """
    本次发行概况-其他相关机构
        1. 学习章节特征，根据章节进行结合crude answer定位表格（大多数情况下都是一张大表）
        2. 包含 table_kv 和 partial_text 两个模型，应对表格和段落
        3. 调用子 predictor 预测三级字段
    """

    model_intro = {"doc": "本次发行概况-其他相关机构", "name": "本次发行概况-其他相关机构", "hide": True}

    def __init__(self, mold, config, **kwargs):
        self.main_table_kv = KeyValueTable(mold, config, **kwargs)
        self.main_partial_text = PartialTextV3(mold, config, **kwargs)
        self._model = {}
        super(OtherRelatedAgencies, self).__init__(mold, config, **kwargs)
        self.run_sub_predictors = False

    @classmethod
    def model_template(cls):
        template = {}
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, data):
        self._model = data
        self.main_table_kv.model = data.get("main_table_kv")
        self.main_partial_text.model = data.get("main_partial_text")

    def train(self, dataset, **kwargs):
        self.main_table_kv.train(dataset, **kwargs)
        self.main_partial_text.train(dataset, **kwargs)
        self._model = {
            "syllabus": Counter(),
            "main_table_kv": self.main_table_kv.model,
            "main_partial_text": self.main_partial_text.model,
        }
        for item in dataset:
            sylls = item.data.get("syllabuses")
            if not sylls:
                continue
            syll_reader = PdfinsightSyllabus(sylls)
            for _, node in item.answer.items():
                for idx in node.relative_element_indexes:
                    elt = item.data.get("elements", {}).get(idx)
                    if not elt or not elt.get("syllabus"):
                        continue
                    for syll in syll_reader.find_by_index(elt["syllabus"]):
                        if syll["level"] > 1:
                            text = split_title_p.split(syll["title"])[0]
                            self._model["syllabus"].update([clean_text(text)])

    def predict_with_elements(self, crude_answers, **kwargs):
        results = []
        syll_features = self.model.get("syllabus", Counter())
        for key in [k for k, v in syll_features.most_common() if v > 1]:
            sylls = self.pdfinsight.find_sylls_by_pattern([re.compile(key)])
            sylls = [syll for syll in sylls if syll["level"] > 1]
            if not sylls:
                continue
            for child_idx in sylls[-1]["children"]:
                syll = self.pdfinsight.syllabus_dict[child_idx]
                results.extend(self.predict_with_section(crude_answers, syll, **kwargs))
        return results

    def predict_with_section(self, crude_answers, syll, **kwargs):
        answers = []
        candidates = self._get_element_candidates(
            crude_answers,
            self.config["path"],
            priors=self.config.get("element_candidate_priors", []),
            ranges=[syll["range"]],
        )

        answer = {}
        for item in candidates:
            etype, ele = self.pdfinsight.find_element_by_index(item["element_index"])
            if etype == "TABLE":
                predict_res = self.main_table_kv.predict([ele], **kwargs)
            else:
                predict_res = self.main_partial_text.predict([ele], **kwargs)
            for result in predict_res:
                for k, v in result.items():
                    # FIXME: 三级字段提取的位置有问题
                    answer.setdefault(k, []).append(v)
        for col, sub_predictor in self.sub_predictors.items():
            sub_answers = sub_predictor.run_predict(crude_answers, ranges=[syll["range"]], **kwargs)
            if sub_predictor.leaf:
                answer[col] = [item[col] for item in sub_answers if col in item]
            else:
                answer[col] = sub_answers
        # TODO: 大表格中应该提出多组答案，现在只有一组
        answers.append((None, [answer]))
        return answers
