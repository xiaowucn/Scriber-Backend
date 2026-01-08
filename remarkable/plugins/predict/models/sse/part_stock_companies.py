import re
from collections import Counter

from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.predict.common import is_table_elt
from remarkable.plugins.predict.models.sse.group_extract_base import GroupExtractBase
from remarkable.plugins.predict.models.table_kv import KeyValueTable
from remarkable.predictor.utils import filter_table_cross_page


class PartStockCompanies(GroupExtractBase):
    model_intro = {
        "doc": "从指定章节的kv表格中提取参股公司信息",
        "name": "发行人基本情况-参股公司基本情况",
        "hide": True,
    }

    def __init__(self, mold, config, **kwargs):
        table_model = KeyValueTable(mold, config, **kwargs)
        super(PartStockCompanies, self).__init__(mold, config, table_model, **kwargs)

    def extract_chapter_feature(self, dataset, **kwargs):
        """
        统计level最大的`参股`章节标题
        demo:
            发行人基本情况 > 发行人控股子公司及参股公司情况 > 发行人的参股公司情况 > A公司 > 基本情况
            发行人基本情况 > 发行人控股子公司及参股公司情况 > 发行人的参股公司情况 > A公司
            发行人基本情况 > 发行人控股子公司及参股公司情况 > 发行人的参股公司情况
        """
        counter = Counter()
        for item in dataset:
            syll_reader = PdfinsightSyllabus(item.data.get("syllabuses", []))
            for key_col in item.answer.get("公司名称", {}).values():
                for eidx in key_col.relative_element_indexes:
                    element = item.data.get("elements", {}).get(eidx)
                    if not element or not element.get("syllabus"):
                        continue
                    syllabuses = syll_reader.find_by_index(element["syllabus"])
                    for syllabus in syllabuses[::-1]:
                        if re.search(r"参股", syllabus["title"]):
                            counter.update([clear_syl_title(syllabus["title"])])
                            break
        return counter

    def train(self, dataset, **kwargs):
        chapter_counter = self.extract_chapter_feature(dataset, **kwargs)
        self.main_table_model.train(dataset, **kwargs)
        self._model = {
            "chapter": chapter_counter,
            "main_table_model": self.main_table_model.model,
            "main_partial_text": None,
        }

    def predict_with_elements(self, crude_answers, **kwargs):
        results = []
        chapter_features = self.model.get("chapter")
        if not chapter_features:
            return results
        for title, _ in chapter_features.most_common():
            syllabuses = self.pdfinsight.syllabus_reader.find_by_clear_title(
                title, order_by="level", reverse=True, multi=True, equal_mode=True
            )
            if not syllabuses:
                continue
            aim_syllabus = syllabuses[0]
            results.extend(self.predict_with_section(crude_answers, aim_syllabus, [], **kwargs))
        return results

    def predict_with_section(self, crude_answers, syllabus, processed_elts, **kwargs):
        results = []
        tables = []
        for idx in range(*syllabus["range"]):
            etype, elt = self.pdfinsight.find_element_by_index(idx)
            if not elt:
                continue
            if not is_table_elt(elt):
                continue
            tables.append(elt)

        tables = filter_table_cross_page(tables)
        for table in tables:
            predict_res = self.main_table_model.predict([table], **kwargs)
            for result in predict_res:
                if all(x in result for x in ["公司名称"]):  # 必填字段
                    results.append((table, [result]))
        return results
