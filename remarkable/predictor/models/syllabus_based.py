import logging
from collections import Counter
from copy import deepcopy

from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.predict.common import clean_syllabus_feature
from remarkable.predictor.eltype import ElementClassifier, ElementType
from remarkable.predictor.models.empty_answer import EmptyAnswer
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import PredictorResult


class SyllabusBased(SyllabusEltV2):
    filter_elements_by_target = True

    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(SyllabusBased, self).__init__(options, schema, predictor=predictor)

        syllabus_options = deepcopy(options)
        syllabus_options["keep_parent"] = True
        syllabus_options["multi"] = True
        self.syllabus_model = SyllabusEltV2(syllabus_options, schema, predictor=self.predictor)
        self.only_inject_features = self.get_config("only_inject_features")  # 只使用注入的特征
        self.max_syllabus_range = self.get_config("max_syllabus_range", 50)  # 允许单章节最多包含的元素块
        self.ignore_syllabus_range = self.get_config("ignore_syllabus_range", False)  # 忽略单章节最多包含元素块的限制
        self.ignore_syllabus_children = self.get_config("ignore_syllabus_children")  # 忽略子章节
        self.use_crude_answer = self.get_config("use_crude_answer")  # 是否使用初步定位的答案
        self.extract_from = self.get_config("extract_from", "section")  # 提取模式 section/same_type_elements
        self.skip_merged_para = self.get_config("skip_merged_para")  # 是否跳过合并的段落
        self.include_title = self.get_config("include_title", True)  # 是否包含标题

        self.para_model_name = self.get_config("paragraph_model", "partial_text")  # 段落提取模型
        self.para_config = self.get_config("para_config", {})  # 段落提取模型配置
        self.para_model = self.gen_model(self.para_model_name, self.para_config)

        self.table_regarded_as_paras = self.get_config("table_regarded_as_paras")
        self.cell_separator = self.get_config("cell_separator", "")
        self.table_model_name = self.get_config("table_model", "table_tuple")  # 表格提取模型
        self.table_config = self.get_config("table_config", {})  # 表格提取模型配置
        self.table_model = self.gen_model(self.table_model_name, self.table_config)

        self.general_model_name = self.get_config("general_model", "")  # 通用提取模型,不区分段落/表格
        self.general_config = self.get_config("general_config", {})  # 通用提取模型配置
        self.general_model = self.gen_model(self.general_model_name, self.general_config)

        self.shape_as_table = self.get_config("shape_as_table", False)

    def gen_model(self, model_name, model_config):
        from remarkable.predictor.predictor import predictor_models

        options = deepcopy(self.config)
        options["name"] = model_name
        options.update(model_config)

        model_class = predictor_models.get(model_name, EmptyAnswer)
        return model_class(options, self.schema, predictor=self.predictor)

    def train(self, dataset, **kwargs):
        self.model_data["syllabus"] = self.train_syll(dataset, **kwargs)
        self.para_model.train(dataset, **kwargs)
        self.model_data["paragraph"] = self.para_model.model_data
        self.table_model.train(dataset, **kwargs)
        self.model_data["table"] = self.table_model.model_data
        self.general_model.train(dataset, **kwargs)
        self.model_data["general"] = self.general_model.model_data

    def load_model_data(self):
        self.model_data = self.predictor.model_data.get(self.name, {})
        self.para_model.model_data = self.model_data.get("paragraph")
        self.table_model.model_data = self.model_data.get("table")
        self.general_model.model_data = self.model_data.get("general")

        syllabus_model_data = self.model_data.get("syllabus", {}).get(self.schema.name, Counter())
        if not self.model_data.get("syllabus"):
            self.model_data["syllabus"] = {}
        syllabus_model_data = clean_syllabus_feature(syllabus_model_data)
        self.model_data["syllabus"][self.schema.name] = self.inject_model(syllabus_model_data)

    def predict_schema_answer(self, elements):
        self.load_model_data()
        answer_results = []
        sections = []
        syllabus_model_data = self.model_data.get("syllabus", {})[self.schema.name]
        aim_syllabuses = self.get_aim_syllabus(
            syllabus_model_data, min_level=self.min_level, max_level=self.syllabus_level
        )
        for syllabus in aim_syllabuses:
            sections.extend(self.parse_sections(syllabus, self.pdfinsight.syllabus_dict))
        if self.use_crude_answer and not sections:
            for element in elements:
                if ElementClassifier.get_type(element) == ElementType.PARAGRAPH:
                    answer_results.extend(self.para_model.predict([element]))
                elif ElementClassifier.get_type(element) in [
                    ElementType.TABLE_TUPLE,
                    ElementType.TABLE_ROW,
                    ElementType.TABLE_KV,
                ]:
                    answer_results.extend(self.table_model.predict([element]))

                if answer_results and not self.multi_elements:
                    break
            return answer_results

        if self.extract_from == "section":
            answer_results = self.extract_from_section(sections)
        elif self.extract_from == "same_type_elements":
            answer_results = self.extract_from_same_type_elements(sections)

        return answer_results

    def extract_from_section(self, sections: list[tuple[int]]) -> list[PredictorResult]:
        answer_results = []
        for start, end in sections:
            for i in range(start, end):
                ele_type, element = self.pdfinsight.find_element_by_index(i)
                if ele_type == "SHAPE" and self.shape_as_table:
                    answer_results.extend(self.table_model.predict([element]))
                elif ele_type == "PARAGRAPH":
                    if self.skip_merged_para:
                        paragraph_indices = (element["page_merged_paragraph"] or {}).get("paragraph_indices", [])
                        if paragraph_indices and element["index"] != paragraph_indices[0]:
                            continue
                    answer_results.extend(self.para_model.predict([element]))
                elif ele_type == "TABLE":
                    if self.table_regarded_as_paras:
                        for para in self.get_paragraphs_from_table(element, self.cell_separator):
                            answer_results.extend(self.para_model.predict([para]))
                    else:
                        answer_results.extend(self.table_model.predict([element]))
        return answer_results

    def extract_from_same_type_elements(self, sections: list[tuple[int]]) -> list[PredictorResult]:
        answer_results = []
        elements = []
        pre_elt_type = None
        for start, end in sections:
            for i in range(start, end):
                ele_type, element = self.pdfinsight.find_element_by_index(i)
                if ele_type not in ["PARAGRAPH", "TABLE"]:
                    continue
                if pre_elt_type and pre_elt_type != ele_type:
                    if pre_elt_type == "PARAGRAPH":
                        answer_results.extend(self.para_model.predict(elements))
                    elif pre_elt_type == "TABLE":
                        answer_results.extend(self.table_model.predict(elements))
                    elements = []
                elements.append(element)
                pre_elt_type = ele_type

        if pre_elt_type == "PARAGRAPH":
            answer_results.extend(self.para_model.predict(elements))
        elif pre_elt_type == "TABLE":
            answer_results.extend(self.table_model.predict(elements))

        return answer_results

    def parse_sections(self, syllabus, syllabus_dict):
        sections = []
        start, end = syllabus["range"]
        if not self.include_title:
            start = start + 1
        if not syllabus["children"] or self.ignore_syllabus_children:
            # 每段是一个 section
            if end - start < self.max_syllabus_range or self.ignore_syllabus_range:
                for i in range(start, end):
                    sections.append((i, i + 1))
        else:
            # 添加章节标题到子章节之间的内容
            children = syllabus["children"]
            first_children = children[0]
            first_children_syllabus = syllabus_dict[first_children]
            end = first_children_syllabus["element"]
            sections.append([start, end])
            # 每节是一个 section
            for sub_syllabus in (syllabus_dict[c] for c in syllabus["children"]):
                sections.append(sub_syllabus["range"])
        return sections

    def train_syll(self, dataset, **kwargs):
        """训练定位章节特征"""
        model_data = {self.schema.name: Counter()}
        if self.only_inject_features:
            return model_data

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
                        feature = self.get_feature(syllabus, syl_reader.syllabus_dict, level=self.syllabus_level)
                        features.add(feature)
                model_data[self.schema.name].update(features)
        return model_data

    def find_main_syll(self, syllabus, syllabus_dict, known_names=None):
        def is_sub(syll):
            title = clear_syl_title(syll["title"])
            if syll["parent"] == -1:
                return False
            if len(title) <= 4:
                return True
            if any(clear_syl_title(name) in title for name in known_names or []):
                return True
            return False

        if syllabus["parent"] == -1:
            return syllabus
        parent = syllabus_dict[syllabus["parent"]]

        if is_sub(syllabus):
            return self.find_main_syll(parent, syllabus_dict, known_names=known_names)

        return syllabus

    def get_feature(self, syllabus, syllabus_dict, known_names=None, level=None):
        """
        "根章节标题|子章节标题|子章节2标题|...|元素块所在(最近的子章节)章节"
        """
        syllabus = self.find_main_syll(syllabus, syllabus_dict, known_names=known_names)
        full_syllabuses = [syllabus]
        pid = syllabus["parent"]
        while pid != -1:
            _syll = syllabus_dict[pid]
            full_syllabuses.insert(0, _syll)
            pid = _syll["parent"]

        if level:
            full_syllabuses = [i for i in full_syllabuses if i["level"] <= level]
        return "|".join([s["title"] for s in full_syllabuses])
