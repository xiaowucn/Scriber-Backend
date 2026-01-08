import re
from collections import Counter

from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.plugins.predict.models.model_base import PredictModelBase
from remarkable.plugins.predict.models.partial_text_v3 import PartialTextV3
from remarkable.plugins.predict.models.table_kv import KeyValueTable
from remarkable.predictor.predict import CharResult, ResultOfPredictor

passed_title_pattern = re.compile("基本|情况")
main_title_pattern = re.compile("子公司|参股公司|控股公司")


class SSESubCompany(PredictModelBase):
    """子公司基本信息
    1. 学习章节特征，根据章节进行分组预测
    2. 包含 table_kv 和 partial_text 两个模型，应对表格和段落
    3. 公司名称 未找到时，用标题来补充
    4. 调用子 predictor 预测三级字段 （或在 conductor 中完成）
    """

    model_intro = {"doc": "", "name": "", "hide": True}

    def __init__(self, mold, config, **kwargs):
        self.main_table_kv = KeyValueTable(mold, config, **kwargs)
        self.main_partial_text = PartialTextV3(mold, config, **kwargs)
        self._model = {}
        super(SSESubCompany, self).__init__(mold, config, **kwargs)
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
        chapter_counter = self.extract_chapter_feature(dataset, **kwargs)
        self.main_table_kv.train(dataset, **kwargs)
        self.main_partial_text.train(dataset, **kwargs)
        self._model = {
            "chapter": chapter_counter,
            "main_table_kv": self.main_table_kv.model,
            "main_partial_text": self.main_partial_text.model,
        }

    def predict_with_elements(self, crude_answers, **kwargs):
        results = []
        chapter_features = self.model.get("chapter", Counter())
        main_sylls = self.find_main_syll_from_crude_answer(crude_answers) or self.find_main_syll_by_feature(
            chapter_features
        )
        for sylls in main_sylls:
            aim_syls = self.find_sub_company_syll(sylls[-1])
            for syll in aim_syls:
                results.extend(self.predict_with_section(crude_answers, syll, **kwargs))
        return results

    def find_main_syll_by_feature(self, chapter_features):
        res = []
        for key in [k for k, v in chapter_features.most_common() if v > 1]:
            sylls = self.pdfinsight.syllabus_reader.find_sylls_by_name(key.split("|"))
            if not sylls or len(sylls) < 2:
                continue
            res.append(sylls)
        return res

    def find_main_syll_from_crude_answer(self, crude_answers):
        def _cut_syll_tail(sylls):
            if not sylls:
                return []
            if not main_title_pattern.search(sylls[-1]["title"]):
                return _cut_syll_tail(sylls[:-1])
            return sylls

        res = []
        candidates = self._get_element_candidates(
            crude_answers,
            self.config["path"],
        )
        for candi in candidates:
            sylls = self.pdfinsight.find_syllabuses_by_index(candi["element_index"])
            sylls = _cut_syll_tail(sylls)
            if sylls:
                # 初步定位太多，暂时只要一个
                res.append(sylls)
                break
        return res

    def find_sub_company_syll(self, parent_syl):
        res = []
        for child_idx in parent_syl["children"]:
            syll = self.pdfinsight.syllabus_reader.syllabus_dict[child_idx]
            if not passed_title_pattern.search(syll["title"]):
                res.append(syll)
            else:
                res.extend([self.pdfinsight.syllabus_reader.syllabus_dict[x] for x in syll["children"]])
        return res

    def predict_with_section(self, crude_answers, syll, **kwargs):
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
                    answer.setdefault(k, []).append(v)
        if "公司名称" not in answer:
            _, title_para = self.pdfinsight.find_element_by_index(syll["element"])
            answer.setdefault("公司名称", []).append(
                ResultOfPredictor([CharResult(title_para["chars"], elt=title_para)])
            )
        for col, sub_predictor in self.sub_predictors.items():
            sub_answers = sub_predictor.run_predict(crude_answers, ranges=[syll["range"]], **kwargs)
            if sub_predictor.leaf:
                answer[col] = [item[col] for item in sub_answers if col in item]
            else:
                answer[col] = sub_answers
        return [(None, [answer])]

    def extract_chapter_feature(self, dataset):
        """
        已实现：
        发行人基本情况 > 子公司情况 > A公司
        todo:
        发行人基本情况 > 子公司情况 > （境内/境外/控股/全资）子公司 > A公司
        发行人基本情况 > 子公司情况 > 表格
        """
        counter = Counter()
        for item in dataset:
            sylls = item.data.get("syllabuses")
            if not sylls:
                continue
            syll_reader = PdfinsightSyllabus(sylls)
            for key_col in item.answer.get("公司名称", {}).values():
                for eidx in key_col.relative_element_indexes:
                    element = item.data.get("elements", {}).get(eidx)
                    if not element or not element.get("syllabus"):
                        continue
                    sylls = syll_reader.find_by_index(element["syllabus"])
                    if not sylls or len(sylls) < 3:  # 发行人基本情况 > 子公司情况 > A公司
                        continue
                    if passed_title_pattern.search(sylls[-1]["title"]):
                        # 排除 5.九州生物 - (1)基本情况
                        sylls = sylls[:-2]
                    else:
                        # 排除 4.高能聚合
                        sylls = sylls[:-1]
                    syll_feature = "|".join([s["title"] for s in sylls])
                    counter.update([syll_feature])
        return counter
