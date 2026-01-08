import re
from collections import Counter

from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.predict.common import is_paragraph_elt
from remarkable.plugins.predict.models.sse.group_extract_base import GroupExtractBase
from remarkable.plugins.predict.models.table_kv import KeyValueTable
from remarkable.predictor.predict import CharResult, ResultOfPredictor


class ActualController(GroupExtractBase):
    model_intro = {
        "doc": "实际控制人",
        "name": "发行人基本情况-实际控制人",
        "hide": True,
    }

    def __init__(self, mold, config, **kwargs):
        table_model = KeyValueTable(mold, config, **kwargs)
        self.columns = ["实际控制人名称"]
        super(ActualController, self).__init__(mold, config, table_model, **kwargs)

    def extract_chapter_feature(self, dataset, **kwargs):
        counter = Counter()
        for item in dataset:
            syll_reader = PdfinsightSyllabus(item.data.get("syllabuses", []))
            for key_col in item.answer.get("实际控制人情况原文段落", {}).values():
                for eidx in key_col.relative_element_indexes:
                    element = item.data.get("elements", {}).get(eidx)
                    if not element or not element.get("syllabus"):
                        continue
                    syllabuses = syll_reader.find_by_index(element["syllabus"])
                    for syllabus in syllabuses[::-1]:  # 统计最近的'实际控制人'标题
                        if re.search(r"实际控制人", syllabus["title"]):
                            counter.update([clear_syl_title(syllabus["title"])])
                            break
        return counter

    def train(self, dataset, **kwargs):
        chapter_counter = self.extract_chapter_feature(dataset, **kwargs)
        self.main_partial_text.train(dataset, **kwargs)
        self._model = {
            "chapter": chapter_counter,
            "main_table_model": None,
            "main_partial_text": self.main_partial_text.model,
        }

    def predict_with_elements(self, crude_answers, **kwargs):
        processed_elts = []
        chapter_features = self.model.get("chapter")
        if not chapter_features:
            return []
        syls = {}
        for title, _ in chapter_features.most_common():
            syllabuses = self.pdfinsight.syllabus_reader.find_by_clear_title(
                title, order_by="level", reverse=True, multi=True, equal_mode=True
            )
            if not syllabuses:
                continue
            aim_syllabus = syllabuses[0]
            syls.setdefault(aim_syllabus["index"], aim_syllabus)
        candidates = set()
        for syl in syls.values():
            candidate_elts = self._get_element_candidates(
                crude_answers,
                self.config["path"],
                priors=self.config.get("element_candidate_priors", []),
                ranges=[syl["range"]],
            )
            for candidate in candidate_elts:
                candidates.add(candidate["element_index"])

        results = self.predict_with_section(candidates, None, processed_elts, **kwargs)
        return results

    def predict_with_section(self, crude_answers, syllabus, processed_elts, **kwargs):
        results = []
        for elt_idx in crude_answers:
            etype, elt = self.pdfinsight.find_element_by_index(elt_idx)
            if not elt:
                continue
            if not is_paragraph_elt(elt):
                continue
            predict_res = self.main_partial_text.predict([elt], **kwargs)
            for result in predict_res:
                answer = {}
                for attr in ["实际控制人名称", "实际控制人持股数量", "实际控制人持股占比"]:
                    if result.get(attr):
                        answer.setdefault(attr, []).append(result.get(attr))
                if answer:
                    answer["实际控制人情况原文段落"] = [
                        ResultOfPredictor(data=[CharResult(elt.get("chars"), text=elt.get("text"), elt=elt)])
                    ]
                results.append((elt, [answer]))
        return results
