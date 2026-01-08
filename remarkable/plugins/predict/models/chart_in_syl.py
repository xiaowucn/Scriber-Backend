from collections import Counter

from remarkable.common.image_util import outline_base64_str
from remarkable.common.storage import localstorage
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.predict.common import find_nearest_syl
from remarkable.predictor.predict import OutlineResult, ResultOfPredictor

from .model_base import PredictModelBase


class ChartInSyllabus(PredictModelBase):
    model_intro = {
        "doc": """
        提取指定章节下的图表
        """,
        "name": "章节中的图表",
        "hide": True,
    }

    def __init__(self, *args, **kwargs):
        super(ChartInSyllabus, self).__init__(*args, **kwargs)
        self.base_on_crude_element = False
        # 是否输出多个答案
        self.multi_elements = self.config.get("multi_elements", True)

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
    def extract_feature(anser_item, answer):
        sylls = anser_item.data.get("syllabuses", [])
        features = Counter()
        for answer_data in answer["data"]:
            if not answer_data["elements"]:
                continue
            aim_syl = find_nearest_syl(answer_data["elements"][0], sylls)
            if aim_syl:
                clear_title = clear_syl_title(aim_syl["title"])
                features.update(
                    [
                        clear_title,
                    ]
                )
        return features

    def predict(self, elements, **kwargs):
        answers = []
        for col in self.columns:
            features = self.model.get(col) or Counter()
            aim_syl = self.find_aim_syll_by_features(features)
            if not aim_syl:
                aim_syl = self.patch_aim_syl(col)
            if not aim_syl:
                continue
            data = []
            answer = {}
            for idx in range(*aim_syl["range"]):
                elt_typ, elt = self.pdfinsight.find_element_by_index(idx)
                if not elt:
                    continue
                if elt_typ in ("SHAPE", "IMAGE"):
                    _text = elt.get("text")
                    if not _text:
                        _text = "图表" if elt_typ == "SHAPE" else "图片"
                    if col == "发行人股权结构图":
                        pdf_path = localstorage.mount(self.file.path())
                        _text = outline_base64_str(pdf_path, elt["page"], elt["outline"], scale=1.0)
                        if len(_text) <= 1000:  # todo：过滤页眉页脚
                            continue
                    data.append(OutlineResult(elt["page"], elt["outline"], text=_text))
                    if not self.multi_elements:
                        break
            if data:
                answer[col] = ResultOfPredictor(data, score=1)
                answers.append(answer)
                if not self.multi_elements:
                    break
        return answers

    def find_aim_syll_by_features(self, features):
        for clear_title, _ in features.most_common():
            syls = self.pdfinsight.find_sylls_by_clear_title(
                clear_title, order_by="level", reverse=True, equal_mode=True
            )
            if syls:
                return syls[0]
        return None

    def patch_aim_syl(self, col):
        patch = {
            "发行人股权结构图": [r"(发行人|公司)的?股权结构图?"],
        }
        for reg in patch.get(col, []):
            syls = self.pdfinsight.find_sylls_by_clear_title(reg, order_by="level", reverse=True, equal_mode=False)
            if syls:
                return syls[0]
        return None
