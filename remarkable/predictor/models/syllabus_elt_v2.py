import logging
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from typing import Pattern

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.predict.common import (
    build_feature_pattern,
    clean_syllabus_feature,
)
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import OutlineResult, PredictorResult

P_NUM_START = re.compile(r"^[(（]?\d[\d.)）]+\s?")


class SyllabusEltV2(BaseModel):
    """
    提取整个章节的内容，适配 schema:
    {
        "第一章": xxx,
        "第二章": yyy,
    }


    与 SyllabusElt 区别在于，标注框视为一个章节, 只用框里的第一个元素块(SyllabusElt是用所有元素块）的标题作为特征

    config template:
    {
        'name': 'syllabus_elt_v2',
        'keep_parent': True,
        'match_method': 'similarity'  # extract
    }
    """

    filter_elements_by_target = True

    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super().__init__(options, schema, predictor=predictor)
        self.keep_parent = self.get_config("keep_parent")  # 保留父章节标题
        self.order_by = self.get_config("order_by", "index")  # 遍历章节的时的排序方式
        self.reverse = self.get_config("reverse", False)  # 遍历章节时的顺序
        self.only_first = self.get_config("only_first")  # 只取章节下的第一个元素块
        self.include_title = self.get_config("include_title")  # 包含标题的元素块
        self.neglect_patterns = PatternCollection(self.get_config("neglect_patterns"))  # 特征的黑名单
        self.match_method = self.get_config("match_method", "extract")  # 寻找目标标题时的匹配方式
        self.multi_level = self.get_config("multi_level", False)  # 是否支持多级章节
        self.syllabus_level = self.get_config("syllabus_level", 99999)  # 最大章节层级
        self.min_level = self.get_config("min_level", 0)  # 最小章节层级
        self.one_result_per_feature = self.get_config("one_result_per_feature", True)  # 每个特征匹配出的章节只保留一个
        self.ignore_pattern = PatternCollection(self.get_config("ignore_pattern", []))
        self.break_para_pattern = PatternCollection(self.get_config("break_para_pattern", []))
        self.include_break_para = self.get_config("include_break_para", False)
        self.include_sub_title = self.get_config("include_sub_title", True)
        self.skip_table = self.get_config("skip_table", False)
        self.skip_types = self.get_config("skip_types", [])
        self.valid_types = self.get_config("valid_types", [])
        self.remove_para_begin_number = self.get_config("remove_para_begin_number", False)  # 删除段落开头的章节序号
        self.page_header_patterns = PatternCollection(self.get_config("page_header_patterns", []))

    def get_config(self, key, default=None, column=None):
        config = self.config.get("syllabus_elt_v2")
        if not config:
            return super().get_config(key, default, column)
        if column in config and key in config[column]:
            return config[column][key]
        return config[key] if key in config else super().get_config(key, default, column)

    @property
    def only_before_first_chapter(self):
        # 截取章节标题和第一个子标题之间的内容
        return self.get_config("only_before_first_chapter", False)

    def train(self, dataset, **kwargs):
        """
        model 示意:
        Counter({
            "重大事项|对上市公司的影响": 21,
            "重大事项|控投股东提供财务资助对上市公司的影响": 7,
            ...
        })
        """
        model_data = {}
        for col, col_path in self.columns_with_fullpath():
            if self.get_config("only_inject_features", column=col):
                continue
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
                model_data.setdefault(col, Counter()).update(features)
        self.model_data = model_data

    @staticmethod
    def get_feature(syllabus, syllabus_dict):
        """
        "根章节标题|子章节标题|子章节2标题|...|元素块所在(最近的子章节)章节"
        """
        full_syllabuses = [syllabus]
        pid = syllabus["parent"]
        while pid != -1:
            _syll = syllabus_dict[pid]
            full_syllabuses.insert(0, _syll)
            pid = _syll["parent"]

        return "|".join([s["title"] for s in full_syllabuses])

    @staticmethod
    def find_chapter_syllabus(item, syl_reader):
        if not item.get("elements"):
            return None
        syllabus = syl_reader.find_by_elt_index(item["elements"][0], include_self=False)
        if not syllabus:
            return None
        return syllabus[-1]

    def revise_model(self, data) -> Counter:
        ret = Counter()
        if self.keep_parent:
            return data or ret

        if not data:
            return ret
        for key, count in data.items():
            new_key = key.split("|")[-1]
            ret[new_key] = ret[new_key] + count
        return ret

    def inject_model(self, data, col=None):
        if self.get_config("only_inject_features", column=col):
            data = Counter()
        most_counter = -1
        if data and self.get_config("inject_features_first", default=True, column=col):
            most_counter = data.most_common()[0][1]
        for feature in self.get_config("inject_syllabus_features", default=[], column=col):
            data.update({feature: most_counter + 1})

        # 仅适用于模型管理页面配置的正则
        for feature in self.get_config("inject_custom_patterns", default=[], column=col):
            feature = feature if feature.startswith("__regex__") else f"__regex__{feature}"
            data.update({feature: most_counter + 1})

        return data

    def load_model_data(self):
        for col in self.columns:
            model_data = self.get_model_data(col)
            model_data = self.revise_model(model_data)
            model_data = clean_syllabus_feature(model_data)
            model_data = self.inject_model(model_data, col)
            self.model_data[col] = model_data

    def predict_schema_answer(self, elements) -> list[PredictorResult]:
        self.load_model_data()
        answer_results = []
        for col in self.columns:
            model_data = self.get_model_data(col)
            if not model_data:
                continue
            aim_syllabuses = self.get_aim_syllabus(
                model_data,
                min_level=self.min_level,
                max_level=self.syllabus_level,
                syllabus_black_list=PatternCollection(self.get_config("syllabus_black_list", column=col)),
                invalid_parent_features=self.get_config("invalid_parent_features", column=col),
                invalid_child_features=self.get_config("invalid_child_features", column=col),
                child_features=self.get_config("child_features", column=col),
            )
            if not aim_syllabuses:
                continue
            for aim_syl in aim_syllabuses:
                if self.only_first:
                    aim_para = None
                    for index in range(1, 4):
                        ele_type, ele = self.pdfinsight.find_element_by_index(aim_syl["element"] + index)
                        if ele_type == "PARAGRAPH":
                            if self.ignore_pattern and self.ignore_pattern.nexts(clean_txt(ele.get("text") or "")):
                                continue
                            aim_para = ele
                            break
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
                        aim_syl,
                        self.pdfinsight,
                        include_title=self.include_title,
                        ignore_pattern=self.ignore_pattern,
                        only_before_first_chapter=self.only_before_first_chapter,
                        include_sub_title=self.include_sub_title,
                        break_para_pattern=self.break_para_pattern,
                        include_break_para=self.include_break_para,
                        skip_table=self.skip_table,
                        page_header_patterns=self.page_header_patterns,
                        skip_types=self.skip_types,
                        valid_types=self.valid_types,
                    )
                    if self.remove_para_begin_number and page_box:
                        text = re.sub(P_NUM_START, "", "\n".join(i["text"] for i in page_box).strip())
                        page_box[0]["text "] = text
                    else:
                        text = "\n".join(i["text"] for i in page_box)
                    # if not text:  Use self.ignore_pattern
                    #     continue
                    elements = self.get_elements_from_page_box(page_box)
                    elements = list(self.target_elements_iter(elements))
                    if not elements:
                        continue
                    element_results = [
                        OutlineResult(page_box=page_box, text=text, element=elements[0], origin_elements=elements)
                    ]
                    answer_result = self.create_result(element_results, text=text, column=col)
                    answer_results.append(answer_result)
        return answer_results

    @staticmethod
    def get_elements_from_page_box(page_box):
        elements = {}
        for i in page_box:
            for element in i["elements"]:
                page_merged_table = element.get("page_merged_table")
                # page_merged_table是int,说明该表已经包含在与其他表生成的MergedTable里
                if isinstance(page_merged_table, int) and page_merged_table in elements:
                    continue
                elements[element["index"]] = element
        return list(elements.values())

    def get_aim_syllabus(
        self,
        model_data,
        min_level=0,
        max_level=99999,
        syllabus_black_list=None,
        invalid_parent_features: list[Pattern | str] | None = None,
        invalid_child_features: list[Pattern | str] | None = None,
        child_features: list[Pattern | str] | None = None,
    ):
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
                syllabuses = [s for s in syllabuses if min_level <= s["level"] <= max_level]
                if not syllabuses:
                    continue
                if self.match_method == "similarity":
                    # 按相似度排序
                    syllabuses.sort(
                        key=lambda x: max(SequenceMatcher(None, p.pattern, x["title"]).ratio() for p in patterns),
                        reverse=True,
                    )
                if syllabus_black_list:
                    syllabuses = [x for x in syllabuses if not syllabus_black_list.nexts(clear_syl_title(x["title"]))]
                syllabuses = syllabuses[:1] if self.one_result_per_feature else syllabuses
                for syllabus in syllabuses:
                    if not self.check_parents_and_children(
                        syllabus, invalid_parent_features, invalid_child_features, child_features
                    ):
                        continue

                    aimed_items[syllabus["index"]] = syllabus
                if aimed_items and not self.multi:
                    break
            if aimed_items and not self.multi_level:
                break
        return list(self.filter_elements_by_syllabus_regs(aimed_items.values()))

    @staticmethod
    def group_feature_by_level(model_data):
        level_features = defaultdict(Counter)
        for feature, cnt in model_data.items():
            if "__regex__" in feature:
                level = len(list(filter(None, feature.split("__regex__"))))
            else:
                level = len(feature.split("|"))
            level_features[level].update({feature: cnt})
        return sorted(level_features.items(), key=lambda p: p[0], reverse=True)

    def check_parents_and_children(
        self, syllabus, invalid_parent_features, invalid_child_features, child_features
    ) -> bool:
        if not self.check_parents(syllabus, invalid_parent_features):
            return False
        if not self.check_children(syllabus, invalid_child_features, child_features):
            return False
        return True

    def check_parents(self, syllabus, invalid_parent_features) -> bool:
        if not invalid_parent_features:
            return True

        syllabuses = self.pdfinsight.get_parent_syllabuses(syllabus["index"])
        syllabuses = [x for x in syllabuses[::-1] if x["index"] != syllabus["index"]]
        for patterns in invalid_parent_features:
            if len(syllabuses) > len(patterns):
                continue
            patterns = [x for x in patterns.split("__regex__")[::-1] if x]
            for idx, pattern in enumerate(patterns):
                if not re.compile(pattern).match(clear_syl_title(syllabuses[idx]["title"])):
                    break
            else:
                return False
        return True

    def check_children(self, syllabus, invalid_child_features, child_features) -> bool:
        if not invalid_child_features and not child_features:
            return True
        if invalid_child_features and self.is_child_features_match(syllabus, invalid_child_features):
            return False
        if child_features and not self.is_child_features_match(syllabus, child_features):
            return False

        return True

    def is_child_features_match(self, syllabus, invalid_child_features):
        level = syllabus["level"]
        children = self.pdfinsight.syllabus_reader.get_child_syllabus(syllabus)
        for patterns in invalid_child_features:
            patterns = [x for x in patterns.split("__regex__") if x]
            level_offset = 1
            pattern = re.compile(patterns[level_offset - 1])

            for child in children:
                if child["level"] < level + level_offset:
                    break
                if child["level"] != level + level_offset:
                    continue
                if pattern.match(clear_syl_title(child["title"])):
                    if level_offset == len(patterns):
                        return True

                    level_offset += 1
                    pattern = re.compile(patterns[level_offset - 1])

        return False
