from collections import Counter

from remarkable.common.pattern import PatternCollection
from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.predict.common import build_feature_pattern, clean_syllabus_feature
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import OutlineResult


class SyllabusElt(BaseModel):
    """
    提取整个章节的内容，适配 schema:
    {
        "第一章": xxx,
        "第二章": yyy,
    }
    """

    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(SyllabusElt, self).__init__(options, schema, predictor=predictor)
        self.threshold = self.get_config("threshold", 0.5)  # 阈值
        self.keep_parent = self.get_config("keep_parent")  # 保留父章节标题
        self.order_by = self.get_config("order_by", "index")  # 遍历章节的时的排序方式
        self.reverse = self.get_config("reverse", False)  # 遍历章节时的顺序
        self.only_first = self.get_config("only_first")  # 只取章节下的第一个元素块
        self.include_title = self.get_config("include_title")  # 包含标题的元素块
        self.neglect_patterns = PatternCollection(self.get_config("neglect_patterns"))  # 与feature_black_list重复

    def train(self, dataset, **kwargs):
        """
        model 示意:
        Counter({
            "对上市公司的影响": 21,
            "控投股东提供财务资助对上市公司的影响": 7,
            ...
        })
        """
        model_data = {}
        for col, col_path in self.columns_with_fullpath():
            for item in dataset:
                syllabuses = item.data.get("syllabuses", [])
                if not syllabuses:
                    continue
                syl_reader = PdfinsightSyllabus(syllabuses)
                features = Counter()
                for node in self.find_answer_nodes(item, col_path):
                    if node.data is None:
                        continue
                    for syllabus in self.find_syllabuses(node.data, syl_reader):
                        feature = self.get_feature(syllabus, syl_reader.syllabus_dict)
                        if feature and feature not in features:
                            features.update([feature])
                model_data.setdefault(col, Counter()).update(features)
        self.model_data = model_data

    def get_feature(self, syllabus, syllabus_dict):
        """
        "根章节标题|子章节标题|子章节2标题|...|元素块所在(最近的子章节)章节"
        """
        parent = syllabus_dict.get(syllabus["parent"])
        if not parent:
            parent = {"title": "", "parent": -1}
        if parent["parent"] == -1:
            return "|".join([s["title"] for s in (parent, syllabus)])

        return f"{self.get_feature(parent, syllabus_dict)}|{syllabus['title']}"

    @staticmethod
    def find_syllabuses(data_item, syl_reader):
        for item in data_item.data:
            for idx in item.get("elements", []):
                syllabuses = syl_reader.find_by_elt_index(idx)
                if not syllabuses:
                    continue
                yield syllabuses[-1]

    def crude_model_data(self, elements) -> Counter:
        """取初步定位元素块章节title作为feature"""
        model_data = Counter()
        for elt in [e for e in elements if e["score"] >= self.threshold]:
            syllabus = self.pdfinsight.syllabus_dict.get(elt.get("syllabus"))
            if syllabus:
                model_data.update([self.get_feature(syllabus, self.pdfinsight.syllabus_dict)])
        return model_data

    def revise_model(self, data):
        if self.keep_parent:
            return data
        ret = Counter()
        for key, count in data.items():
            new_key = key.split("|")[-1]
            ret.update({new_key: count})
        return ret

    def get_model_data(self, column=None):
        model_data = super(SyllabusElt, self).get_model_data(column=column) or Counter()

        # blacklist
        blacklist = self.get_config("feature_black_list", default=[], column=column)
        blacklist_features = [k for k in model_data if any(self.is_match(b, k) for b in blacklist)]
        for feature in blacklist_features:
            model_data.pop(feature)

        # whitelist
        if model_data:
            most_counter = model_data.most_common()[0][1]
        else:
            most_counter = 0
        for feature in self.get_config("feature_white_list", default=[], column=column):
            model_data.update({feature: most_counter + 1})

        return model_data

    def predict_schema_answer(self, elements):
        answer_results = []
        for col in self.columns:
            model_data = self.get_model_data(col)
            if not model_data:
                return answer_results
            aim_syllabuses = self.get_aim_syllabus(self.revise_model(model_data))
            if not aim_syllabuses:
                continue
            for aim_syl in aim_syllabuses:
                if self.only_first:
                    ele_type, aim_para = self.pdfinsight.find_element_by_index(aim_syl["element"] + 1)
                    if ele_type != "PARAGRAPH":
                        continue
                    aim_elements = []
                    if aim_para:
                        if self.include_title:
                            ele_type, aim_syl_para = self.pdfinsight.find_element_by_index(aim_syl["element"])
                            aim_elements.append(aim_syl_para)

                        aim_elements.append(aim_para)
                        outline_result = [
                            OutlineResult(self.pdfinsight.elements_outline(aim_elements), element=aim_elements[0])
                        ]
                        answer_result = self.create_result(outline_result, column=self.schema.name)
                        answer_results.append(answer_result)
                else:
                    page_box = PdfinsightSyllabus.syl_outline(
                        aim_syl, self.pdfinsight, include_title=self.include_title
                    )
                    text = "\n".join(i["text"] for i in page_box)
                    elements = []
                    for i in page_box:
                        elements.extend(i["elements"])
                    if not elements:
                        continue
                    element_results = [
                        OutlineResult(page_box=page_box, text=text, element=elements[0], origin_elements=elements)
                    ]
                    answer_result = self.create_result(element_results, text=text, column=col)
                    answer_results.append(answer_result)
        return answer_results

    def get_aim_syllabus(self, model_data):
        aimed_items = {}
        model_data = clean_syllabus_feature(model_data)
        for feature, _ in model_data.most_common():
            patterns = build_feature_pattern(feature, match_method="contain")
            if not patterns:
                continue
            if self.neglect_patterns.nexts(patterns[-1].pattern):
                continue
            syllabuses = self.pdfinsight.find_sylls_by_pattern(
                patterns,
                order=self.order_by,
                reverse=self.reverse,
                clean_func=clear_syl_title,
            )
            if not syllabuses:
                continue
            aimed_item = syllabuses[0]
            aimed_items[aimed_item["index"]] = aimed_item
            if aimed_items and not self.multi:
                break
        return aimed_items.values()
