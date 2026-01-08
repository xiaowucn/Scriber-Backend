import re

from remarkable.plugins.predict.models.model_base import PredictModelBase
from remarkable.plugins.predict.models.partial_text_v3 import PartialTextV3

syllabus_pattern = re.compile(r"持[有股](发行人|公司)?\s?5%以上股份.*?股东|公司控股股东基本|实际控制人的?基本情况")
pass_syllabus_pattern = re.compile(r"发行人基本情况|[^司构东人一二三四五六七八九十][、及:]|（\d）")
share_holder_patterns = [
    re.compile(r"[为、](?P<dst>.*?)(?=[、。])"),
]


class GroupExtractBase(PredictModelBase):
    def __init__(self, mold, config, table_model, **kwargs):
        self.main_table_model = table_model
        self.main_partial_text = PartialTextV3(mold, config, **kwargs)
        self._model = {}
        super(GroupExtractBase, self).__init__(mold, config, **kwargs)
        self.config.update({"need_syl": True})

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, data):
        self._model = data
        self.main_table_model.model = data.get("main_table_model")
        self.main_partial_text.model = data.get("main_partial_text")

    def train(self, dataset, **kwargs):
        chapter_counter = self.extract_chapter_feature(dataset, **kwargs)
        self.main_table_model.train(dataset, **kwargs)
        self.main_partial_text.train(dataset, **kwargs)
        self._model = {
            "chapter": chapter_counter,
            "main_table_model": self.main_table_model.model,
            "main_partial_text": self.main_partial_text.model,
        }

    @classmethod
    def model_template(cls):
        pass

    def predict_with_elements(self, crude_answers, **kwargs):
        results = []
        processed_elts = []
        chapter_features = self.model.get("chapter")
        if not chapter_features:
            return results
        for key in [k for k, v in chapter_features.most_common()]:
            syllabuses = self.pdfinsight.syllabus_reader.find_sylls_by_name(key.split("|"))
            if not syllabuses:
                continue
            aim_syllabus = syllabuses[-1]
            if aim_syllabus.get("children"):
                for child_idx in aim_syllabus["children"]:
                    syllabus = self.pdfinsight.syllabus_reader.syllabus_dict[child_idx]
                    results.extend(self.predict_with_section(crude_answers, syllabus, processed_elts, **kwargs))
            else:
                results.extend(self.predict_with_section(crude_answers, aim_syllabus, processed_elts, **kwargs))
        return results

    def predict_with_section(self, crude_answers, syllabus, processed_elts, **kwargs):
        raise NotImplementedError

    def extract_chapter_feature(self, dataset, **kwargs):
        raise NotImplementedError
