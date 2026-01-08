import re
from collections import Counter

from remarkable.common.util import group_cells
from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.predict.common import is_paragraph_elt, is_syl_elt, is_table_elt
from remarkable.plugins.predict.models.sse.group_extract_base import GroupExtractBase
from remarkable.plugins.predict.models.table_kv import KeyValueTable
from remarkable.predictor.predict import CharResult, ResultOfPredictor

syllabus_pattern = re.compile(r"持[有股](发行人|公司)?\s?5%以上股份.*?股东|公司控股股东基本|实际控制人的?基本情况")
pass_syllabus_pattern = re.compile(r"发行人基本情况|[^司构东人一二三四五六七八九十][、及:]|（\d）")
share_holder_patterns = [re.compile(r"[为、](?P<dst>.*?)(?=[、。])")]


class ShareHoldersGt5(GroupExtractBase):
    model_intro = {
        "doc": "根据目录模型进行分组，每组元素块利用其它模型进行提取",
        "name": "持有5%以上股份的股东",
        "hide": True,
    }

    def __init__(self, mold, config, **kwargs):
        table_model = KeyValueTable(mold, config, **kwargs)
        super(ShareHoldersGt5, self).__init__(mold, config, table_model, **kwargs)

    def find_syllabuses(self):
        temp = {}
        for title, _ in self.model["chapter"].most_common():
            sylls = self.pdfinsight.syllabus_reader.find_by_clear_title(
                title, order_by="level", reverse=True, equal_mode=True
            )
            if sylls:
                temp.setdefault(sylls[0]["index"], sylls[0])
        syllabuses = {}
        for syl in temp.values():
            if not syl["children"]:
                syllabuses.setdefault(syl["index"], syl)
            else:
                for child_idx in syl["children"]:
                    children_syllabus = self.pdfinsight.syllabus_reader.syllabus_dict[child_idx]
                    syllabuses.setdefault(children_syllabus["index"], children_syllabus)
        syllabuses = sorted(syllabuses.values(), key=lambda x: x["index"])
        return syllabuses

    def predict_with_elements(self, crude_answers, **kwargs):
        results = []
        processed_elts = []
        syllabuses = self.find_syllabuses()
        for syl in syllabuses:
            results.extend(self.predict_with_section(crude_answers, syl, processed_elts, **kwargs))
        return results

    def predict_with_section(self, crude_answers, syllabus, processed_elts, **kwargs):
        results = []
        kwargs["ranges"] = [syllabus["range"]]
        # 从标题的下一个段落中提取
        post_elts = self.pdfinsight.find_elements_near_by(
            syllabus["element"], amount=3, aim_types=["TABLE", "PARAGRAPH"]
        )
        for post_elt in post_elts:
            if post_elt["index"] not in range(*syllabus["range"]):
                continue
            if post_elt["index"] in processed_elts:
                continue
            processed_elts.append(post_elt["index"])
            answers = []
            if post_elt["class"] == "PARAGRAPH":
                answers = self.main_partial_text.predict([post_elt], **kwargs)
            elif post_elt["class"] == "TABLE":
                answers = self.main_table_model.predict([post_elt], **kwargs)
            answers = [x for x in answers if "持股5%以上股东名称" in x]  # 过滤无效答案
            if answers:
                # 每个叶子节点只取第一个
                for answer in answers:
                    for result in answer.values():
                        if len(result.data) > 1:
                            result.data = result.data[:1]
                results.append((post_elt, answers))
                break
        # 标题作为股东名称的情况
        if not results:
            results = self.syl_as_title(syllabus)

        return results

    def syl_as_title(self, syllabus):
        results = []
        next_elts = self.pdfinsight.find_elements_near_by(
            syllabus["element"], amount=1, aim_types=["TABLE", "PARAGRAPH"]
        )
        if next_elts and not is_table_elt(next_elts[0]):
            return results
        # todo: 表格的特征
        cells_by_row, _ = group_cells(next_elts[0]["cells"])
        if len([cell for cell in cells_by_row.get("0", {}).values() if not cell.get("dummy")]) == 2:
            _, elt = self.pdfinsight.find_element_by_index(syllabus["element"])
            if elt and is_paragraph_elt(elt):
                answers = [
                    {
                        "持股5%以上股东名称": ResultOfPredictor(
                            [CharResult(elt["chars"], text=clear_syl_title(elt["text"]), elt=elt)]
                        )
                    }
                ]
                results.append((elt, answers))
        return results

    def extract_chapter_feature(self, dataset, **kwargs):
        counter = Counter()
        titles = set()
        for item in dataset:
            syll_reader = PdfinsightSyllabus(item.data.get("syllabuses", []))
            for key_col in item.answer.get("持股5%以上股东名称", {}).values():
                for eidx in key_col.relative_element_indexes:
                    element = item.data.get("elements", {}).get(eidx)
                    if not element:
                        continue
                    syllabuses = syll_reader.find_by_index(element["syllabus"])
                    if not syllabuses or len(syllabuses) < 2:
                        continue
                    # 标注的是标题本身则统计上一级标题，否则统计当前层级
                    aim_syl = syllabuses[-2] if is_syl_elt(element, syll_reader.syllabus_dict) else syllabuses[-1]
                    titles.add(clear_syl_title(aim_syl["title"]))
        counter.update(titles)
        return counter
