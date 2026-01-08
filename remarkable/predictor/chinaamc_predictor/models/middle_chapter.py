from difflib import SequenceMatcher

from remarkable.common.pattern import PatternCollection
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.predict.common import (
    build_feature_pattern,
)
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2


class MiddleSyllabus(SyllabusEltV2):
    def __init__(self, options, schema, predictor=None):
        super().__init__(options, schema, predictor=predictor)
        self.top_chapter_anchor_pattern = PatternCollection(
            self.get_config("top_chapter_anchor_regs", [])
        )  # 顶部章节锚点正则
        self.bottom_chapter_anchor_pattern = PatternCollection(
            self.get_config("bottom_chapter_anchor_regs", [])
        )  # 底部章节锚点正则

    def get_top_bottom_index(self):
        top_chapter_index, bottom_chapter_index = None, None
        if self.top_chapter_anchor_pattern and self.bottom_chapter_anchor_pattern:
            # 按章节查找
            top_chapter = self.pdfinsight.find_sylls_by_pattern(self.top_chapter_anchor_pattern.pattern_objects)
            if top_chapter:
                top_chapter_index = top_chapter[0]["index"]
            bottom_chapter = self.pdfinsight.find_sylls_by_pattern(self.bottom_chapter_anchor_pattern.pattern_objects)
            if bottom_chapter:
                bottom_chapter_index = bottom_chapter[0]["index"]
            # 全文按段落查找
            if top_chapter_index is None or bottom_chapter_index is None:
                # TODO
                pass

        return top_chapter_index, bottom_chapter_index

    def get_aim_syllabus(self, model_data, min_level=0, max_level=99999, syllabus_black_list=None):
        top_chapter_index, bottom_chapter_index = self.get_top_bottom_index()
        aimed_items = {}
        for lvl, feature_counter in self.group_feature_by_level(model_data):
            if lvl < min_level or lvl > max_level:
                continue
            for feature, _ in feature_counter.most_common():
                patterns = build_feature_pattern(feature, self.match_method)
                if not patterns:
                    continue
                if any(self.neglect_patterns.nexts(pattern.pattern) for pattern in patterns):
                    continue
                syllabuses = self.pdfinsight.find_sylls_by_pattern(
                    patterns,
                    order=self.order_by,
                    reverse=self.reverse,
                    clean_func=clear_syl_title,
                )

                if top_chapter_index is not None:
                    if bottom_chapter_index is not None:
                        syllabuses = [s for s in syllabuses if top_chapter_index <= s["index"] <= bottom_chapter_index]
                    else:
                        syllabuses = [s for s in syllabuses if top_chapter_index <= s["index"]]
                    if not syllabuses:
                        continue

                syllabuses = [s for s in syllabuses if min_level <= s["level"] <= max_level]
                if not syllabuses:
                    continue
                if self.match_method == "similarity":
                    # 按相似度排序
                    syllabuses.sort(
                        key=lambda x: max(SequenceMatcher(None, p.pattern, x["title"]).ratio() for p in patterns),
                        reverse=True,
                    )
                syllabuses = syllabuses[:1] if self.one_result_per_feature else syllabuses
                for syllabus in syllabuses:
                    if syllabus_black_list and syllabus_black_list.nexts(clear_syl_title(syllabus["title"])):
                        continue
                    aimed_items[syllabus["index"]] = syllabus
                if aimed_items and not self.multi:
                    break
            if aimed_items and not self.multi_level:
                break
        return list(aimed_items.values())
