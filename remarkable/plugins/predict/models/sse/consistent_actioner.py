import re
from collections import Counter

from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.plugins.predict.models.sse.group_extract_base import GroupExtractBase
from remarkable.plugins.predict.models.table_kv import KeyValueTable
from remarkable.predictor.predict import CharResult, ResultOfPredictor, TblResult

actioner_pattern = re.compile(r"一致行动人")


class ConsistentActioner(GroupExtractBase):
    model_intro = {
        "doc": "根据目录模型进行分组，每组元素块利用其它模型进行提取",
        "name": "发行人基本情况-实际控制人的一致行动人",
        "hide": True,
    }

    def __init__(self, mold, config, **kwargs):
        table_model = KeyValueTable(mold, config, **kwargs)
        super(ConsistentActioner, self).__init__(mold, config, table_model, **kwargs)

    def predict_with_section(self, crude_answers, syllabus, processed_elts, **kwargs):
        results = []
        candidates = self._get_element_candidates(
            crude_answers,
            self.config["path"],
            priors=self.config.get("element_candidate_priors", []),
            ranges=[syllabus["range"]],
        )
        exist_name = []
        for item in candidates:
            answer = {}
            etype, ele = self.pdfinsight.find_element_by_index(item["element_index"])
            if etype == "TABLE":
                predict_res = self.main_table_model.predict([ele], **kwargs)
            else:
                predict_res = self.main_partial_text.predict([ele], **kwargs)
            for result in predict_res:
                for k, v in result.items():
                    answer.setdefault(k, []).append(v)
            # 补充原文等字段
            results.extend(self.complete_answer(answer, exist_name, ele))
        return results

    @staticmethod
    def complete_answer(answer, exist_name, ele):
        results = []
        name_answers = []
        for name_answer_predictor in answer.get("一致行动人名称", []):
            for data in name_answer_predictor.data:
                if isinstance(data, TblResult):
                    cell_idx = data.cells[0] if data.cells else ""
                    actioner_name = data.elt["cells"][cell_idx]["text"]
                else:
                    actioner_name = data.text
                if actioner_name in exist_name or any((i in actioner_name for i in exist_name)):
                    continue
                name_answers.append({"一致行动人名称": [ResultOfPredictor([data])]})
                exist_name.append(actioner_name)
        for proportion, name_answer in zip(answer.get("一致行动人持股占比", []), name_answers):
            name_answer.update({"一致行动人持股占比": proportion})
        for name_answer in name_answers:
            if "一致行动人基本情况（原文）" not in name_answer and ele["class"] == "PARAGRAPH":
                # todo 处理表格的原文
                name_answer.setdefault("一致行动人基本情况（原文）", []).append(
                    ResultOfPredictor([CharResult(ele["chars"], elt=ele)])
                )
            results.append((ele, [name_answer]))
        return results

    def extract_chapter_feature(self, dataset, **kwargs):
        counter = Counter()
        for item in dataset:
            syll_reader = PdfinsightSyllabus(item.data.get("syllabuses", []))
            for key_col in item.answer.get("一致行动人名称", {}).values():
                for eidx in key_col.relative_element_indexes:
                    element = item.data.get("elements", {}).get(eidx)
                    if not element or not element.get("syllabus"):
                        continue
                    syllabuses = syll_reader.find_by_index(element["syllabus"])
                    syllabus_titles = []
                    # 获取最后一个带有'一致行动人'的标题
                    for syllabus in syllabuses:
                        if actioner_pattern.search(syllabus["title"]):
                            syllabus_titles.append(syllabus["title"])
                            break
                        else:
                            syllabus_titles.append(syllabus["title"])
                    syllabus_feature = "|".join(syllabus_titles)
                    counter.update([syllabus_feature])
        return counter
