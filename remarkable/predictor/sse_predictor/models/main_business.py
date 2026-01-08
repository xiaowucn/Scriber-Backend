import logging
from collections import Counter
from copy import deepcopy

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.models.table_row import TableRow
from remarkable.predictor.models.table_tuple import TupleTable
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import PredictorResult


class MainBusiness(SyllabusEltV2):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(MainBusiness, self).__init__(options, schema, predictor=predictor)

        syll_options = deepcopy(options)
        syll_options["keep_parent"] = True
        syll_options["multi"] = True
        self.syll_model = SyllabusEltV2(syll_options, schema, predictor=self.predictor)

        table_options = deepcopy(options)
        table_clz = (
            TableRow if table_options.get("table_type", TableType.ROW.value) == TableType.ROW.value else TupleTable
        )
        self.table_model = table_clz(options, self.schema, predictor=self.predictor)

    def load_model_data(self):
        self.model_data = self.predictor.model_data.get(self.name, {})
        self.get_model_data("syllabus").get(self.schema.name, Counter()).update(
            self.get_config("inject_syllabus_features", default=[])
        )
        self.table_model.model_data = self.model_data.get("table", {})
        for path in self.table_model.model_data:
            self.table_model.get_model_data(path).update(
                self.get_config("inject_table_features", default={}).get(path, [])
            )

    def predict_schema_answer(self, elements):
        """取到章节后调用 table 模型进行提取"""
        self.load_model_data()
        answer_results = []

        holder_ranges = []
        syll_model_data = self.get_model_data(column="syllabus")[self.schema.name]
        aim_syllabuses = self.syll_model.get_aim_syllabus(syll_model_data)
        for syll in aim_syllabuses:
            holder_ranges.append(syll["range"])

        for start, end in holder_ranges:
            results = self.predict_table_element(start, end)
            if results:
                answer_results.extend(results)
        return answer_results

    def predict_table_element(self, start: int, end: int) -> list[dict[str, list[PredictorResult]]]:
        neg_pattern_collection = PatternCollection(self.get_config("neglect_title_patterns"))
        elements = []
        for i in range(start, end):
            ele_type, elt = self.pdfinsight.find_element_by_index(i)
            # 目前给定文档信息全在表格中
            if ele_type == "TABLE" and not neg_pattern_collection.nexts(clear_syl_title(elt.get("title", ""))):
                elements.append(elt)

        # 优先取指定title的表格
        prefer_title_patterns = self.get_config("prefer_table_title_patterns")
        if prefer_title_patterns:
            elements = [
                e for e in elements if PatternCollection(prefer_title_patterns).nexts(clear_syl_title(e["title"]))
            ] or elements

        answers = self.table_model.predict(self.pdfinsight.filter_table_cross_page(elements))

        # 所有cols都必须取到值
        answers = [ans for ans in answers if len(ans) == len(self.columns)]
        if not self.get_config("multi", False) and answers:
            return [answers[0]]
        return answers

    def train_syll(self, dataset, **kwargs):
        """训练定位章节特征"""
        model_data = {}
        for _, col_path in self.columns_with_fullpath():
            for item in dataset:
                syllabuses = item.data.get("syllabuses", [])
                if not syllabuses:
                    continue
                syl_reader = PdfinsightSyllabus(syllabuses)
                features = set()
                for node in self.find_answer_nodes(item, col_path):
                    if node.data is None:
                        continue
                    for answer_item_data in node.data["data"]:
                        syllabus = self.find_chapter_syllabus(answer_item_data, syl_reader)
                        if not syllabus:
                            logging.warning(f"can't find syllabus for answer item {answer_item_data}")
                            continue
                        feature = self.get_feature(syllabus, syl_reader.syllabus_dict)
                        features.add(feature)
                model_data.setdefault(self.schema.name, Counter()).update(features)
        return model_data

    def train(self, dataset, **kwargs):
        self.table_model.train(dataset, **kwargs)
        self.model_data = {
            "syllabus": self.train_syll(dataset, **kwargs),
            "table": self.table_model.model_data,
        }
