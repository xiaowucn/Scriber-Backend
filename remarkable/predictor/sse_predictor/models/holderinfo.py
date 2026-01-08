import logging
import re
from collections import Counter
from copy import deepcopy

from remarkable.common.util import clean_txt
from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import PredictorResult


class HolderInfo(SyllabusEltV2):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        from remarkable.predictor.predictor import SchemaPredictor

        super(HolderInfo, self).__init__(options, schema, predictor=predictor)

        syll_options = deepcopy(options)
        syll_options["keep_parent"] = True
        syll_options["multi"] = True
        self.syll_model = SyllabusEltV2(syll_options, schema, predictor=self.predictor)

        self.child_models = {}
        for child in self.schema.parent.children:
            child_predictor_config = {
                "path": child.path[1:],
                "models": [
                    {
                        "name": "auto" if child.name != "标题名称" else "score_filter",
                        "threadhold": 0.1,  # only for score_filter
                    },
                ],
            }
            child_predictor = SchemaPredictor(
                child, child_predictor_config, predictor.prophet, predictor, columns=[child.name]
            )
            # child_model = AutoModel(child_predictor_config["models"][0], child, child_predictor)
            child_model = child_predictor.create_models()["schema_models"][0]
            self.child_models[child.name] = child_model

    def load_model_data(self):
        for col, model in self.child_models.items():
            model.model_data = self.get_model_data(column=col)

    def predict_schema_answer(self, elements):
        """取到章节后调用 automodel 进行提取"""
        self.load_model_data()
        answer_results = []

        holder_ranges = []
        syll_model_data = self.get_model_data(column="syllabus")[self.schema.name]
        aim_syllabuses = self.get_aim_syllabus(syll_model_data)
        for syll in aim_syllabuses:
            holder_ranges.extend(self.parse_holder_info_region(syll, self.pdfinsight.syllabus_dict))

        for start, end in holder_ranges:
            holder_info = self.extract_one_holder(start, end)
            if holder_info:
                answer_results.append(holder_info)
        return answer_results

    @staticmethod
    def parse_holder_info_region(syll, syll_dict):
        regions = []
        if syll["children"]:
            # 每节是一个 holder
            for subsyll in (syll_dict[c] for c in syll["children"]):
                regions.append(subsyll["range"])
        else:
            # 每段是一个 holder
            start, end = syll["range"]
            if end - start < 50:
                for i in range(start, end):
                    regions.append((i, i + 1))
        return regions

    def extract_one_holder(self, start: int, end: int) -> dict[str, list[PredictorResult]]:
        holder_info = {}
        for child_schema in self.schema.parent.children:
            col = child_schema.name
            model = self.child_models.get(col)
            if not model:
                continue
            candi_elements = self.predictor.get_candidate_elements(key_path=child_schema.path[1:])
            aim_elements = [e for e in candi_elements if start <= e["index"] < end]
            for answer in model.predict(aim_elements):
                if isinstance(answer, dict):
                    holder_info.setdefault(col, []).extend(answer.get(col, []))
                elif isinstance(answer, PredictorResult):
                    holder_info.setdefault(col, []).append(answer)

        self.fill_name_by_title(holder_info)
        self.fill_holder_type(holder_info)
        return holder_info

    def fill_name_by_title(self, holder_info):
        if "名称" in holder_info:
            return
        if "标题名称" not in holder_info:
            return
        if len(holder_info) < 2:
            return

        title_answer = holder_info["标题名称"][0]
        name_answer = self.create_result(title_answer.element_results, column="名称")
        holder_info["名称"] = [name_answer]

    def fill_holder_type(self, holder_info):
        if "股东类型" in holder_info:
            return
        if "名称" not in holder_info:
            return

        name_answer = holder_info["名称"][0]
        name_text = clean_txt(name_answer.text)
        if "合伙" in name_text:
            type_value = "合伙企业"
        elif "公司" in name_text:
            type_value = "法人"
        elif any(k.endswith("（法人）") for k in holder_info):
            type_value = "法人"
        elif any(k.endswith("（自然人）") for k in holder_info):
            type_value = "自然人"
        elif any(k.endswith("（合伙企业）") for k in holder_info):
            type_value = "合伙企业"
        elif len(name_text) <= 3:
            type_value = "自然人"
        else:
            type_value = "法人"

        type_answer = self.create_result(name_answer.element_results, value=type_value, column="股东类型")
        holder_info["股东类型"] = [type_answer]

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
                        entity_names = []
                        if "标题名称" in node.parent:
                            entity_names.extend([n.data.plain_text for n in node.parent["标题名称"].values()])
                        if "名称" in node.parent:
                            entity_names.extend([n.data.plain_text for n in node.parent["名称"].values()])
                        feature = self.get_feature(syllabus, syl_reader.syllabus_dict, known_names=entity_names)
                        features.add(feature)
                model_data.setdefault(self.schema.name, Counter()).update(features)
        return model_data

    def find_main_syll(self, syllabus, syllabus_dict, known_names=None):
        def is_sub(syll):
            title = clear_syl_title(syll["title"])
            if syll["parent"] == -1:
                return False
            if len(title) <= 4:
                return True
            if title.endswith("公司"):
                return True
            if any(clear_syl_title(name) in title for name in known_names or []):
                return True
            check_pattern = self.config.get("aim_chapter_pattern")
            if check_pattern and not re.search(check_pattern, title):
                return True
            return False

        if syllabus["parent"] == -1:
            return syllabus
        parent = syllabus_dict[syllabus["parent"]]

        if is_sub(syllabus):
            return self.find_main_syll(parent, syllabus_dict, known_names=known_names)

        return syllabus

    def get_feature(self, syllabus, syllabus_dict, known_names=None):
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

        return "|".join([s["title"] for s in full_syllabuses])

    def train(self, dataset, **kwargs):
        # 章节定位
        self.model_data = {
            "syllabus": self.train_syll(dataset, **kwargs),
        }

        # 各字段提取
        for col, model in self.child_models.items():
            model.train(dataset, **kwargs)
            self.model_data[col] = model.model_data
