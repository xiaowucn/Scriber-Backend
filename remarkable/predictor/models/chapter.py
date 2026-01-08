import logging
import re
from collections import Counter, defaultdict

from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.predict.common import build_feature_pattern, clean_syllabus_feature
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.schema_answer import OutlineResult, ParagraphResult


class Chapter(BaseModel):
    """
    按章节提取标题和内容，适配 schema：
    {
        "标题": xxx,
        "内容": yyy,
    }
    """

    @property
    def title_column(self):
        return self.config.get("title_column")

    @property
    def content_column(self):
        return self.config.get("content_column")

    def train(self, dataset, **kwargs):
        """
        model 示意:
        Counter({
            "重大事项|对上市公司的影响": 21,
            "重大事项|控投股东提供财务资助对上市公司的影响": 7,
            ...
        })
        """
        if not self.title_column:
            logging.error("chapter model need title_column in config")
            return
        model_data = {"title": Counter()}
        for item in dataset:
            syllabuses = item.data.get("syllabuses", [])
            if not syllabuses:
                continue
            syl_reader = PdfinsightSyllabus(syllabuses)
            features = set()
            for node in self.find_answer_nodes(item, self.schema.sibling_path(self.title_column)):
                if node.data is None:
                    continue
                for answer_item_data in node.data["data"]:
                    syllabus = self.find_chapter_syllabus(answer_item_data, syl_reader)
                    if not syllabus:
                        logging.warning(f"can't find syllabus for answer item {answer_item_data}")
                        continue
                    feature = self.get_feature(syllabus, syl_reader.syllabus_dict)
                    features.add(feature)
            model_data["title"].update(features)
        self.model_data = model_data

    @staticmethod
    def get_feature(syllabus, syllabus_dict):
        """
        "根章节标题|子章节标题|子章节2标题|...|元素块所在(最近的子章节)章节"
        """
        return SyllabusEltV2.get_feature(syllabus, syllabus_dict)

    @staticmethod
    def find_chapter_syllabus(item, syl_reader):
        if not item.get("elements"):
            return None
        syllabus = syl_reader.find_by_elt_index(item["elements"][0])
        return syllabus[-1]

    def predict_schema_answer(self, elements):
        answer_results = []
        model_data = self.get_model_data("title")
        if not model_data:
            return answer_results
        aim_syllabuses = self.get_aim_syllabus(model_data)
        if not aim_syllabuses:
            return answer_results
        for aim_syl in sorted(aim_syllabuses, key=lambda s: s["index"]):
            answer_result = {}
            # title
            _, title_paragraph = self.pdfinsight.find_element_by_index(aim_syl["range"][0])
            if not title_paragraph:
                continue
            answer_result[self.title_column] = [
                self.create_result(
                    [ParagraphResult(title_paragraph, title_paragraph["chars"])], column=self.title_column
                )
            ]

            # content
            if self.content_column:
                pages = PdfinsightSyllabus.syl_outline(aim_syl, self.pdfinsight)
                text = "\n".join(i["text"] for i in pages)
                elements = []
                for page in pages:
                    elements.extend(page["elements"])
                element_results = [OutlineResult(page_box=pages, text=text)]
                answer_result[self.content_column] = [
                    self.create_result(element_results, text=text, column=self.content_column)
                ]
            answer_results.append(answer_result)
        return answer_results

    def get_aim_syllabus(self, model_data, min_level=0):
        aimed_items = {}
        model_data = clean_syllabus_feature(model_data)
        for lvl, feature_counter in self.group_feature_by_level(model_data):
            if lvl < min_level:
                continue
            for feature, _ in feature_counter.most_common():
                patterns = build_feature_pattern(feature)
                if not patterns:
                    continue
                if any(re.search(reg, patterns[-1].pattern) for reg in self.config.get("neglect_patterns", [])):
                    continue
                syllabuses = self.pdfinsight.find_sylls_by_pattern(
                    patterns,
                    order=self.get_config("order_by", "index"),
                    reverse=self.get_config("reverse", False),
                    clean_func=clear_syl_title,
                )
                if not syllabuses:
                    continue
                aimed_item = syllabuses[0]
                aimed_items[aimed_item["index"]] = aimed_item
                if aimed_items and not self.multi:
                    break
            if aimed_items and not self.config.get("multi_level", False):
                break
        return list(aimed_items.values())

    @staticmethod
    def group_feature_by_level(model_data):
        level_features = defaultdict(Counter)
        for feature, cnt in model_data.items():
            level = len(feature.split("|"))
            level_features[level].update({feature: cnt})
        return sorted(level_features.items(), key=lambda p: p[0], reverse=True)
