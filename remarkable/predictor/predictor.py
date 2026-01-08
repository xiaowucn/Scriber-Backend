# -*- coding: utf-8 -*-
import copy
import glob
import itertools
import json
import logging
import pickle
import time
from collections import defaultdict
from copy import deepcopy
from difflib import SequenceMatcher
from inspect import signature
from itertools import groupby
from typing import Callable, TypeVar

from remarkable.common.exceptions import ConfigurationError
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt, group_cells, import_class_by_path
from remarkable.config import get_config
from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.predict.common import get_element_candidates
from remarkable.predictor.dataset import DatasetItem
from remarkable.predictor.models.auto import AutoModel
from remarkable.predictor.models.base_model import (
    find_currency_element_result,
    find_unit_by_element_result,
)
from remarkable.predictor.models.cell_partial_text import CellPartialText, KvPartialText
from remarkable.predictor.models.chapter import Chapter
from remarkable.predictor.models.chatgpt import ChatGPT
from remarkable.predictor.models.collect_elements_based import ElementsCollectorBased
from remarkable.predictor.models.default_answer import DefaultAnswer
from remarkable.predictor.models.elements_condition import ElementsCondition
from remarkable.predictor.models.elements_from_depends import ElementsFromDepends
from remarkable.predictor.models.empty_answer import EmptyAnswer
from remarkable.predictor.models.enum_value import EnumValue
from remarkable.predictor.models.fixed_position import FixedPosition
from remarkable.predictor.models.kmeans_classification import KmeansClassification
from remarkable.predictor.models.llm import LLModel
from remarkable.predictor.models.middle_paras import MiddleParas
from remarkable.predictor.models.para_match import ParaMatch
from remarkable.predictor.models.partial_text import PartialText
from remarkable.predictor.models.reference import Reference
from remarkable.predictor.models.regex_pattern import RegexPattern
from remarkable.predictor.models.relation_entity import RelationEntity
from remarkable.predictor.models.row_match import RowMatch
from remarkable.predictor.models.score_filter import ScoreFilter
from remarkable.predictor.models.shape_titles import ShapeTitle
from remarkable.predictor.models.syllabus_based import SyllabusBased
from remarkable.predictor.models.syllabus_elt import SyllabusElt
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.models.table_ai import AITable
from remarkable.predictor.models.table_column_content import TableColumnContent
from remarkable.predictor.models.table_kv import KeyValueTable
from remarkable.predictor.models.table_kv_for_custom import CustomKeyValueTable
from remarkable.predictor.models.table_row import TableRow
from remarkable.predictor.models.table_titles import TableTitle
from remarkable.predictor.models.table_tuple import TupleTable
from remarkable.predictor.models.table_tuple_select import TupleTableSelect
from remarkable.predictor.schema_answer import PredictorResult, PredictorResultGroup
from remarkable.predictor.utils import SafeFileName, calc_distance, get_box_distance
from remarkable.service.user import gen_salt

logger = logging.getLogger(__name__)

predictor_models = {
    "auto": AutoModel,
    "partial_text": PartialText,
    "empty": EmptyAnswer,
    "default": DefaultAnswer,
    "regex_pattern": RegexPattern,
    "score_filter": ScoreFilter,
    "table_column_content": TableColumnContent,
    "segment_info": EmptyAnswer,
    "table_tuple_select": TupleTableSelect,
    "fixed_position": FixedPosition,
    "enum_value": EnumValue,
    "syllabus_elt": SyllabusElt,
    "syllabus_elt_v2": SyllabusEltV2,
    "para_match": ParaMatch,
    "relation_entity": RelationEntity,
    "row_match": RowMatch,
    "table_row": TableRow,
    "table_kv": KeyValueTable,
    "custom_table_kv": CustomKeyValueTable,
    "table_tuple": TupleTable,
    "table_ai": AITable,
    "syllabus_based": SyllabusBased,
    "chapter": Chapter,
    "middle_paras": MiddleParas,
    "elements_collector_based": ElementsCollectorBased,
    "cell_partial_text": CellPartialText,
    "kv_partial_text": KvPartialText,
    "chatgpt": ChatGPT,
    "llm": LLModel,
    "kmeans_classification": KmeansClassification,
    "table_titles": TableTitle,
    "shape_titles": ShapeTitle,
    "elements_from_depends": ElementsFromDepends,
    "reference": Reference,
    "elements_condition": ElementsCondition,
}


class EnumPredictor:
    def predict(self, predictor_result, schema):
        raise NotImplementedError


T_ENUM_ANSWERS = TypeVar("T_ENUM_ANSWERS", dict[str, str], dict[str, list[str]])


class JudgeByRegex(EnumPredictor):
    col_patterns: dict[str, list[str]] | Callable = {}
    multi_answer_col_patterns: dict[str, list[str]] | Callable = {}
    neglect_multi_answer_col_patterns: dict[str, list[str]] = {}

    def __init__(self):
        self.enum_answers: T_ENUM_ANSWERS = {}

    def predict(self, predictor_result, schema, clean_func=clean_txt):
        clean_text = clean_func(predictor_result.text)
        result = {}

        if enum_patterns := self.col_patterns.get(schema.name, {}):
            if isinstance(enum_patterns, dict):
                for enum, patterns in enum_patterns.items():
                    if PatternCollection(patterns).nexts(clean_text):
                        self.enum_answers[schema.path_key] = enum
                        logger.debug(f"column: {schema.name}, enum value: {enum}")
                        break
                else:
                    logger.warning(f"column: {schema.name}, unknown value: {clean_text}")
            elif isinstance(enum_patterns, Callable):
                self.enum_answers[schema.path_key] = enum_patterns(self.enum_answers, clean_text)
            else:
                raise ValueError(f"unknown enum_patterns type: {type(enum_patterns)}")
            return self.enum_answers.get(schema.path_key) or None
        elif multi_enum_patterns := self.multi_answer_col_patterns.get(schema.name, {}):
            if isinstance(multi_enum_patterns, dict):
                default = multi_enum_patterns.get("default")
                for col, patterns in multi_enum_patterns.get("values", {}).items():
                    if PatternCollection(patterns).nexts(clean_text):
                        result.update({col: None})
                if not result and default:
                    result.update({default: None})
            elif isinstance(multi_enum_patterns, Callable):
                result = multi_enum_patterns(self.enum_answers, clean_text)
            else:
                raise ValueError(f"unknown multi_enum_patterns type: {type(multi_enum_patterns)}")

            if not result:
                logger.debug(f"column: {schema.name}, unknown value: {clean_text}")
        else:
            # 默认的枚举值配置, 若枚举值的选项和其正则表达式相同时, 则不需要配置
            if schema.mold_schema:
                schema_info = schema.mold_schema.get_enum_type(schema.type)
                if schema_info:
                    is_multi = schema_info.get("isMultiSelect")
                    for item in schema_info.get("values", {}):
                        value = item.get("name")
                        if value and PatternCollection(value).nexts(clean_text):
                            result.update({value: None})
                        if result and not is_multi:
                            break
        if result and (neglect_enum_patterns := self.neglect_multi_answer_col_patterns.get(schema.name, {})):
            for col, patterns in neglect_enum_patterns.get("values", {}).items():
                if PatternCollection(patterns).nexts(clean_text) and col in result:
                    logger.info(f"neglect column: {schema.name}, enum value: {col}")
                    result.pop(col)
        self.enum_answers[schema.path_key] = list(result)
        return self.enum_answers[schema.path_key] or None


def is_similar_content(content_a, content_b):
    if content_a is None or content_b is None:
        return content_a is None and content_b is None

    if content_a in content_b or content_b in content_a:
        return True
    return SequenceMatcher(None, content_a, content_b).ratio() > 0.4


class BasePredictor:
    def __init__(self, schema, config, prophet=None, primary_key=None, columns=None):
        self.schema = schema
        self.config = config
        self.prophet = prophet
        self.model_data = {}
        self.primary_key = primary_key
        self.columns = columns or list(set([self.schema.name] + (self.primary_key or [])))

        self.post_processors = self.create_post_processors()
        models = self.create_models()
        self.models = models["schema_models"]
        self.primary_models = models["primary_models"]

    @property
    def leaf(self):
        # NOTE: amount 字段在预测时视为叶子节点
        # 配置中可以加入 fake_leaf 使得该字段被当成叶子节点来处理 此时可以使用 PredictorResultGroup 手动进行分组 这时候不需要知道sub_primary_key
        return self.schema.is_leaf or self.schema.is_amount or self.config.get("fake_leaf")

    @property
    def model_options(self):
        if self.config.get("models"):
            model_options = self.config.get("models")
        else:
            model_options = [self.config.get("model")] if self.config.get("model") else []
        return model_options

    def train(self, **kwargs):
        raise NotImplementedError

    def predict(self):
        raise NotImplementedError

    def negotiate(
        self, schema_answers: list[dict[str, list[PredictorResult]]]
    ) -> list[dict[str, list[PredictorResult]]]:
        raise NotImplementedError

    def load_dataset(self):
        raise NotImplementedError

    def create_model(self, model_option, schema):
        """优先加载通用 model, 然后再加载各自特例 model"""
        packages = []
        multi_packages = get_config("prophet.multi_packages")
        if multi_packages:
            for package_name in multi_packages:
                package = f"remarkable.predictor.{package_name}.models.model_config"
                packages.append(package)
        else:
            package = f"remarkable.predictor.{get_config('prophet.package_name')}.models.model_config"
            packages.append(package)
        for package in packages:
            package_models = import_class_by_path(package) or {}
            predictor_models.update(package_models)
        model_class = predictor_models.get(model_option["name"])
        if not model_class:
            raise ConfigurationError(f"No model found: {model_option['name']}")
        return model_class(model_option, schema, predictor=self)

    def create_post_processors(self):
        # 获取后处理方法映射关系
        package = f"remarkable.predictor.{get_config('prophet.package_name')}.post_process.process_config"
        post_processors = import_class_by_path(package) or {}
        return post_processors

    def create_models(self):
        models = {"primary_models": [], "schema_models": []}
        for option in self.model_options:
            if isinstance(option, str):
                logger.warning("predictor config should be a dict")
                option = {"name": option}
            is_primary = option.get("is_primary", False)
            if is_primary:
                schema = self.prophet.mold_schema.find_schema_by_path(option["schema_path"])
                model = self.create_model(option, schema)
                models["primary_models"].append(model)
            else:
                model = self.create_model(option, self.schema)
                models["schema_models"].append(model)

        return models


class SchemaPredictor(BasePredictor):
    def __init__(self, schema, config, prophet=None, parent=None, columns=None):
        super().__init__(
            schema, config, prophet=prophet, primary_key=parent.sub_primary_key if parent else [], columns=columns
        )

        self.tree_answers = []
        self.answer_groups = {}
        self.answer_share_group = []
        self.answer_no_group = []
        self.parent = parent

        self.sub_predictors = self.create_sub_predictors()

        self._dataset = []

    def __str__(self):
        return f"SchemaPredictor<{self.schema_name}>"

    @property
    def root_config(self):
        return self.prophet.predictor_config

    @property
    def sub_primary_key(self):
        sub_primary_key = self.config.get("sub_primary_key", [])
        if sub_primary_key:
            return sub_primary_key
        if any(isinstance(model, LLModel) for model in self.models):
            return self.schema.orders
        has_table_row = any(isinstance(model, (TableRow, AutoModel)) for model in self.models)
        if not has_table_row:
            return sub_primary_key
        columns = self.schema.orders
        return columns

    @property
    def is_share_column(self):
        """是否共享字段，两种情况：
        1. 没有配置主键
        2. 配置 share_column = True
        """
        return self.config.get("share_column", False) or (not self.primary_key)

    @property
    def prophet_answer(self):
        return self.prophet.answer

    @property
    def pdfinsight(self):
        return self.prophet.reader

    @property
    def schema_level(self):
        return self.schema.level

    @property
    def schema_name(self):
        return self.schema.name

    @property
    def model_data_path(self):
        filename = SafeFileName.escape("_".join(self.config["path"]))
        return self.prophet.model_data_dir.joinpath(f"{filename}.pkl")

    @property
    def pdf_path(self):
        return self.prophet.metadata["pdf_path"]

    @property
    def merge_answers(self) -> bool:
        merge_answers = self.config.get("merge_answers")
        if merge_answers is None:
            return self.prophet.merge_schema_answers
        return bool(merge_answers)

    @property
    def divide_answers(self) -> bool:
        """
        [
            {
                "col_a": [predictor_result_0, predictor_result_1],
                "col_b": [predictor_result_2, predictor_result_3]
            }
        ]
        ===>>
        [
            {
                "col_a": [predictor_result_0],
                "col_b": [predictor_result_2],
            },
            {
                "col_a": [predictor_result_1],
                "col_b": [predictor_result_3],
            }
        ]
        :return:
        """
        return self.config.get("divide_answers")

    @property
    def depends(self):
        return self.prophet.depends.get(self.schema_name, [])

    @property
    def pick_answer_strategy(self):
        """Strategy to pick predicted answers by models

        :return: pick strategy: single, all
        :rtype: str
        """
        return self.config.get("pick_answer_strategy", "single")

    @property
    def model_relation(self):
        """鉴于pick_answer_strategy配置只能配置 single/all 两个配置项，
        根据配置关系来选择mold预测答案
        eg: [0, 1, (2,3),4]
        explain: 0 & 1 & (2|3) & 4
        其中数字为模型在配置的index
        """
        return self.config.get("model_relation", [])

    @property
    def strict_group(self):
        """Strict comparison when getting group name"""
        return self.config.get("strict_group", False)

    @property
    def unit_depend(self):
        return self.config.get("unit_depend", {})

    @property
    def primary_key_unit(self):
        return PatternCollection(self.config.get("primary_key_unit", []))

    @property
    def dataset(self):
        if not self._dataset:
            self._dataset = self.load_dataset()
        return self._dataset

    @dataset.setter
    def dataset(self, dataset):
        self._dataset = dataset

    def guess_group_name_handlers(self, source):
        handlers = {
            "element": self._guess_group_from_element,
            "syllabuses": self._guess_from_syllabuses,
            "context_elements": self._guess_group_from_context_elements,
        }
        return handlers[source]

    def train(self, **kwargs):
        logger.info(f"training model for schema: {json.loads(self.schema.path_key)}")

        # dataset = self.load_dataset()

        if self.leaf:
            start = time.time()
            models = self.models + self.primary_models
            for model in models:
                model.train(self.dataset, **kwargs)
                model.print_model()

            logger.info(f"finish training schema {self.schema.path_key}, cost {int(time.time() - start)}s")
        else:
            for predictor in self.sub_predictors:
                predictor.dataset = self.dataset
                predictor.train(**kwargs)

        self.dump_model_data()

    def load_dataset(self) -> list[DatasetItem]:
        dataset = []
        dataset_dir = self.prophet.dataset_dir

        if dataset_dir.exists():
            for pkl in glob.glob(f"{dataset_dir}/*.pkl"):
                with open(pkl, "rb") as dataset_fp:
                    dataset.append(pickle.load(dataset_fp))
        else:
            logger.warning(f"can't find dataset for schema: {json.loads(self.schema.path_key)}")

        return dataset

    def load_model_data(self):
        if self.model_data or not self.config:
            return
        if not self.model_data_path.exists():
            logger.warning(f"can't find model features: {self.model_data_path}")
        else:
            with open(self.model_data_path, "rb") as model_fp:
                self.model_data = pickle.load(model_fp)

    def dump_model_data(self):
        if self.config:
            model_data = {model.name: model.model_data for model in self.models}
            if self.primary_models:
                primary_model_data = {model.name: model.model_data for model in self.primary_models}
                for model_name in primary_model_data:
                    m_data = primary_model_data[model_name]
                    if model_name not in model_data:
                        model_data[model_name] = m_data
                    else:
                        model_data[model_name].update(m_data)
            with open(self.model_data_path, "wb") as model_fp:
                pickle.dump(model_data, model_fp)

        for sub_predictor in self.sub_predictors:
            sub_predictor.dump_model_data()

    def build_primary_key_str(self, dict_answer: dict[str, list[PredictorResult]]):
        primary_key_values = []
        for key in self.primary_key:
            results = dict_answer.get(key, [])
            for result in results:  # PredictorResult
                if result.primary_key:  # Manually assigned primary key
                    primary_key_values.append(result.primary_key)
                else:
                    for element_result in result.element_results:  # ElementResult
                        primary_key_values.append(element_result.text.strip())
        for model in self.models:
            if isinstance(model, TableRow) and model.force_group_by_row:
                primary_key_values.append(gen_salt())
                break
        logger.debug(f"{primary_key_values=}")
        return clean_txt("|".join(primary_key_values))

    def predict_groups(self, known_group_names: list[str] = None) -> dict[str, list[PredictorResult]]:
        schema_answers = None

        for group_name in known_group_names or []:
            if group_name not in self.answer_groups:
                self.answer_groups[group_name] = []

        # 1. 使用模型进行预测
        if self.models:
            self.load_model_data()
        elements = self.get_candidate_elements()
        schema_answers = self.predict_answer_from_models(elements)

        if schema_answers:
            schema_answers = self.negotiate(schema_answers)
            self.add_predicted_results(schema_answers)

        # 2. 处理未分组的情况 answer_no_group
        logger.debug(f"{len(self.answer_no_group)=}")
        if self.answer_no_group:
            if not self.primary_key:
                answer_group = self.answer_groups.setdefault("", [])
                for predictor_result in self.answer_no_group:
                    self.add_predicted_results(
                        [{predictor_result.schema.path_key[-1]: [predictor_result]}], selected_group=answer_group
                    )
            elif self.answer_groups:
                for predictor_result in self.answer_no_group:
                    group_name = self._guess_group_name(predictor_result)
                    if group_name is None:
                        continue
                    answer_group = self.select_answer_group(group_name)
                    if answer_group is not None:
                        self.add_predicted_results(
                            [{predictor_result.schema.path_key[-1]: [predictor_result]}], selected_group=answer_group
                        )

        # 3. 处理共享字段的情况 answer_share_group
        if not self.answer_groups:
            if self.answer_share_group:
                # 只有共享字段 或 不分组 的情况
                self.answer_groups[""] = deepcopy(self.answer_share_group)
        else:
            # 把 answer_share_group 更新到每一组答案中
            for group in self.answer_groups.values():
                group.extend(deepcopy(self.answer_share_group))

        # 4. 修正 answer_groups，并给答案添加 group index
        self.answer_groups = {key: self.revise_group_answer(group) for key, group in self.answer_groups.items()}
        # 5. TODO: 按原表格顺序(从左至右从上到下)对分组进行排序
        return self.answer_groups

    def predict(self):
        groups = self.predict_groups()
        return self.distribute_answers(list(groups.values()))

    @staticmethod
    def revise_group_answer(group: list[PredictorResult], method="merge") -> list[PredictorResult]:
        """修正 group 答案：
        1. 保证 group 中每个叶子节点只有一份 PredictorResult（否则会生成多个相同 path 的叶子节点）
           可能来源有: 本 predictor 输出、sub predictor 补充、share 字段合并
           修正方法："merge" or "overwrite"
        """
        group_dict = {}
        for item in group:
            key = "|".join(item.key_path)
            if key in group_dict:
                if method == "merge":
                    group_dict[key].merge(item)
                elif method == "overwrite":
                    group_dict[key] = item
                else:
                    raise ValueError("undefined revise method %s" % method)
            else:
                group_dict[key] = item
        return list(group_dict.values())

    def predict_value(self, result: PredictorResult):
        if not isinstance(result, PredictorResult):
            raise TypeError("result should be a instance of PredictorResult")
        return self.prophet.parse_value(result)

    def distribute_answers(self, groups: list[list[PredictorResult]]):
        """将嵌套的答案转为平铺的 Dict[path_key, List[PredictorResult]]"""
        tree_answer = defaultdict(list)
        for group_index, group_items in enumerate(groups):
            for item in group_items:
                item.push_group_index(group_index)
                if isinstance(item, PredictorResultGroup):
                    # 非叶子节点
                    for path_key, sub_items in self.distribute_answers(item.groups).items():
                        tree_answer[path_key].extend(sub_items)
                else:
                    # 叶子节点
                    tree_answer[item.key_path_str].append(item)
        return tree_answer

    def build_path_key(self, answer_data, index):
        path_key = []
        for schema_name in answer_data["key"]:
            if schema_name == self.schema_name:
                path_key.append(f"{schema_name}:{index}")
            else:
                path_key.append(f"{schema_name}:0")

        return json.dumps(path_key, ensure_ascii=False)

    @staticmethod
    def get_the_nearest(predictor_result, group_names):
        if not group_names:
            return None
        if len(group_names) == 1:
            return group_names[0]

        try:
            result_first_box = predictor_result.element_results[0].to_answer()["boxes"][0]
            result_page = result_first_box["page"]
            nearest_page = 0
            nearest_groups = []
            for name, group in group_names:
                group_first_box = group[0].element_results[0].to_answer()["boxes"][0]
                page = group_first_box["page"]
                nearest_page_gap = abs(nearest_page - result_page)
                page_gap = abs(page - result_page)
                if page_gap <= nearest_page_gap:
                    if page_gap < nearest_page_gap:
                        nearest_groups = []
                    nearest_page = page
                    distance = get_box_distance(result_first_box["box"], group_first_box["box"])
                    nearest_groups.append((name, group, distance))
        except Exception as exp:
            logger.exception(exp)
            return None

        nearest_groups = sorted(nearest_groups, key=lambda x: x[2])

        return nearest_groups[0]

    def _guess_group_from_element(self, predictor_result, element, element_text=None):
        group_names = []
        # 表格可能被get_paragraphs_from_table()构造成了段落
        if element["class"] == "TABLE" or element.get("origin_class") == "TABLE":
            cells_by_row, _ = group_cells(element["cells"])
            for cells in cells_by_row.values():
                for cell in cells.values():
                    content = clean_txt(cell.get("text", ""))
                    group_names.extend(
                        [(i, self.answer_groups[i]) for i in self.answer_groups if clean_txt(i) in content]
                    )
        else:
            if element_text is None:
                element_text = element.get("text")

            group_names = [(i, self.answer_groups[i]) for i in self.answer_groups if clean_txt(i) in element_text]
        if not group_names:
            return None

        nearest = self.get_the_nearest(predictor_result, group_names)
        if not nearest:
            nearest = group_names[0]

        return nearest[0]

    def _guess_group_from_context_elements(self, predictor_result, result_element):
        group_option = self.config.get("group")
        lookup_strategy = group_option.get("lookup_strategy", "lookahead")
        range_num = group_option.get("range_num", 5)
        if lookup_strategy == "lookahead":
            start = max(result_element["index"] - range_num, 0)
            element_range = range(result_element["index"] - 1, start, -1)
        else:
            if lookup_strategy == "lookbehind":
                start = result_element["index"] + 1
            else:
                start = max(result_element["index"] - 10, 0)
            max_index = max(i for i in self.pdfinsight.data["_index"])
            end = min(start + range_num, max_index)
            element_range = range(end, start, -1)

        for i in element_range:
            if i == result_element["index"]:
                continue

            elt_type, current_element = self.pdfinsight.find_element_by_index(i)
            if current_element is None:
                break

            if elt_type != "PARAGRAPH":
                continue

            group_name = self._guess_group_from_element(predictor_result, current_element)
            if group_name:
                return group_name

        return None

    def _guess_from_syllabuses(self, predictor_result, result_element):
        syllabus_id = result_element.get("syllabus")
        if not PdfinsightSyllabus.is_valid_syllabus(syllabus_id):
            return None

        group_names = self.answer_groups.keys()
        syllabuses = self.pdfinsight.get_parent_syllabuses(syllabus_id)
        group_name = None
        for syllabus in syllabuses[::-1]:
            matches = [
                name for name in group_names if clear_syl_title(name) in clear_syl_title(syllabus.get("title", ""))
            ]
            if matches:
                group_name = matches[0]
                break

        return group_name

    def _get_group_metas_base_element(self, result_element):
        name_distances = []
        for name, answer_results in self.answer_groups.items():
            for answer_result in answer_results:
                if answer_result.schema.name in self.primary_key:
                    group_element = answer_result.element_results[0].element
                    distance = calc_distance(result_element, group_element)
                    name_distances.append((name, distance, group_element))

        name_distances.sort(key=lambda x: abs(x[1]))
        return name_distances

    def _guess_group_name(self, predictor_result):
        # strategy: lookahead, lookbehind, both
        group_option = self.config.get("group")
        if not group_option:
            return None
        if not predictor_result.element_results:
            return None

        result_element = predictor_result.element_results[0].element
        for source in group_option.get("sources", ["element", "syllabuses", "context_elements"]):
            guess_func = self.guess_group_name_handlers(source)
            group_name = guess_func(predictor_result, result_element)
            if group_name is not None:
                logger.debug(f"{group_name}=")
                return group_name

        # result_element = predictor_result.relative_elements[0]
        # metas = self._get_group_metas_base_element(result_element)

        # lookup_strategy = group_option['lookup_strategy']
        # if lookup_strategy == 'lookahead':
        #     name_distance = min([i for i in metas if i[1] >= 0], key=lambda x: x[1])
        # elif lookup_strategy == 'lookbehind':
        #     name_distance = max([i for i in metas if i[1] <= 0], key=lambda x: x[1])
        # else:
        #     name_distance = min(metas, key=lambda x: abs(x[1]))

        # return name_distance[0]
        return None

    def select_answer_group(self, primary_key):
        if primary_key in self.answer_groups:
            return self.answer_groups[primary_key]

        for key, group in self.answer_groups.items():
            # FOR: `中原冶炼厂60.98%股权` and `中原冶炼厂`
            is_share_group = key == ""
            if is_share_group:
                continue
            if self.strict_group:
                if key == primary_key:
                    return group
            else:
                # 0.20% 与 0.2%
                if self.primary_key_unit:
                    primary_key = self.primary_key_unit.sub("", primary_key)
                    key = self.primary_key_unit.sub("", key)
                if key in primary_key or primary_key in key:
                    return group

        return None

    def add_predicted_results(self, schema_answers: list[dict[str, list[PredictorResult]]], selected_group=None):
        """把模型输出 PredictorResult 按照 primary_key 添加到相应的分组中"""
        if not schema_answers:
            return

        for group in schema_answers:
            is_new_group = None
            primary_key_value = self.build_primary_key_str(group)
            if selected_group is not None:
                answer_group = selected_group
            elif self.is_share_column:
                answer_group = self.answer_share_group
            elif primary_key_value:
                answer_group = self.select_answer_group(primary_key_value)
                if answer_group is None:
                    answer_group = self.answer_groups.setdefault(primary_key_value, [])
                    is_new_group = True
                else:
                    is_new_group = False
            else:
                answer_group = self.answer_no_group

            for col, items in group.items():
                if is_new_group is False and col in self.primary_key:
                    # 不重复添加主键
                    continue
                for item in items:
                    answer_result = self.build_schema_answer(item)
                    answer_result.primary_key = primary_key_value
                    answer_group.append(answer_result)

    def post_process(self, answers):
        # 执行后处理
        if post_process_name := self.config.get("post_process"):
            if post_process_func := self.post_processors.get(post_process_name):
                if not callable(post_process_func):
                    raise ValueError("post_process must be a callable function")
                sig = signature(post_process_func)
                required_params_count = len(sig.parameters) - sum(
                    p.default is not p.empty for p in sig.parameters.values()
                )
                if required_params_count != 2:
                    raise ValueError(
                        f"post_process function must have 2 required parameters, but {required_params_count} found"
                    )
                return post_process_func(answers, pdfinsight_reader=self.pdfinsight)
        return answers

    def predict_answer_from_models(self, elements) -> list[dict[str, list[PredictorResult]]]:
        answers = []
        primary_answers = []
        if not self.leaf:
            groups = defaultdict(list)
            for sub in self.sub_predictors:
                res = sub.predict_groups(known_group_names=groups.keys())
                for group_name, items in res.items():
                    groups[group_name].extend(items)
            answers = [
                {self.schema_name: [PredictorResultGroup([group], schema=self.schema)]} for group in groups.values()
            ]
        elif self.config.get("auto_select", False):
            for element in elements:
                model = self.select_model(element)
                if model:
                    if model.base_all_elements:
                        candidate_elements = elements
                    else:
                        candidate_elements = [element]
                    model_answers = model.predict(candidate_elements)
                    valid_answers = [self.is_valid(i) for i in model_answers]
                    answers.extend(valid_answers)
        else:
            logger.debug(f"predict_answer_from_models, for schema {self.schema_name}")
            answer_index_mapping = {}
            for index, model in enumerate(self.models):
                if not isinstance(model, EmptyAnswer):
                    logger.debug(f"model: {model.name}")
                    model_answers = model.predict(elements)
                    valid_answers = [i for i in model_answers if self.is_valid(i)]
                    answers.extend(valid_answers)
                    if self.model_relation and valid_answers:
                        answer_index_mapping[index] = valid_answers
                    elif self.pick_answer_strategy == "single" and valid_answers:
                        break
            if self.model_relation:
                fix_answers = []
                for item in self.model_relation:
                    if isinstance(item, int):
                        if data := answer_index_mapping.get(item):
                            fix_answers.extend(data)
                    elif isinstance(item, (tuple, list)):
                        for index in item:
                            if data := answer_index_mapping.get(index):
                                fix_answers.extend(data)
                                break
                answers = fix_answers
            if not answers:
                for model in self.models:
                    if isinstance(model, EmptyAnswer):
                        logger.debug(f"model: {model.name}")
                        model_answers = model.predict(elements)
                        valid_answers = [i for i in model_answers if self.is_valid(i)]
                        answers.extend(valid_answers)

        answers = self._unify_output_from_models(answers)
        answers = self.post_process(answers)

        # 因目前不支持把 primary models 和 schema models 预测出来的答案重新分配
        # 故 primary models 不应该和期望产出多个 groups 的模型(如 table_row)一起使用
        if not self.is_share_column and self.primary_models:
            for model in self.primary_models:
                # primary model should use custom predict method
                model_answers = model.predict(elements, answers)
                valid_answers = [i for i in model_answers if self.is_valid(i)]
                primary_answers.extend(valid_answers)
                if self.pick_answer_strategy == "single" and valid_answers:
                    break

        if primary_answers:
            primary_answers = self._unify_output_from_models(primary_answers)
            for answer in answers:
                answer.update(primary_answers[0])

        return answers

    @staticmethod
    def _unify_output_from_models(answers):
        # 转换：兼容 [PredictorResult] 格式的模型输出
        return [{i.schema.name: [i]} if isinstance(i, PredictorResult) else i for i in answers]

    @staticmethod
    def is_valid(answer):
        return True

    def select_model(self, element):
        grouped_models = self.group_models()
        element_type = element["class"].lower()
        models = grouped_models.get(element_type)
        if models:
            return self.select_model_base_features(element_type, models)
        return None

    @staticmethod
    def select_model_base_features(element_type, models):
        if element_type == "paragraph":
            return models[0]
        if element_type == "table":
            return models[0]
        return None

    def group_models(self):
        grouped_models = defaultdict(list)
        for element_type, items in groupby(self.models, key=lambda x: x.target_element):
            for model in items:
                grouped_models[element_type].append(model)

        return grouped_models

    @staticmethod
    def merge_answer_data(answers):
        first = answers[0]
        for item in answers[1:]:
            first.merge(item)

        return first

    def get_candidate_elements(self, key_path: list[str] = None) -> list:
        # 某一节点没有配置模型，path是不存在的，所以需要get方法取
        crude_answer_path = key_path or self.config.get("crude_answer_path") or self.config.get("path") or []
        if crude_answer_path and crude_answer_path[-1] == "PARENT_SUBSTITUE":
            crude_answer_path.pop(-1)
        candidates = get_element_candidates(
            self.prophet.crude_answer,
            crude_answer_path,
            priors=self.config.get("element_candidate_priors", []),
            limit=self.config.get("element_candidate_count", 10),
        )
        candidate_elements = []
        location_threshold = self.config.get("location_threshold") or 0
        for item in candidates:
            _, ele = self.pdfinsight.find_element_by_index(item["element_index"])
            if not ele or item["score"] < location_threshold:
                continue
            ele = copy.copy(ele)
            ele["score"] = item["score"]
            if self.config.get("anchor_regs") and not self.match_anchor(ele):
                continue
            candidate_elements.append(ele)
        return candidate_elements

    def match_anchor(self, elt):
        near_by = {"step": -1, "amount": 3, "aim_types": ["PARAGRAPH"]}
        prev_elts = self.pdfinsight.find_elements_near_by(elt["index"], **near_by)
        anchor_pattern = PatternCollection(self.config.get("anchor_regs", []))
        if any(anchor_pattern.search("".join([clean_txt(i["text"]) for i in prev_elts[::-1]]))):
            return True
        return False

    def find_sub_predictor(self, schema_name):
        predictors = [i for i in self.sub_predictors if i.schema_name == schema_name]
        return predictors[0]

    def find_child_schema(self, schema_name):
        for column in self.schema.children:
            if column.name == schema_name:
                return column
            for item in column.children:
                if item.name == schema_name:
                    return item
        return None

    def get_depending_answers(self):
        depends = self.config.get("depends", [])
        answers = []
        entry_predictor = self.find_entry_predictor()
        for schema_name in depends:
            path = self.schema.path[:-1] + [schema_name]
            answer = entry_predictor.get_sub_answer(json.dumps(path, ensure_ascii=False))
            answers.extend(answer)
        return answers

    def find_entry_predictor(self):
        if self.parent.schema_level == 2:
            return self.parent
        return self.parent.find_entry_predictor()

    def get_sub_answer(self, path_key):
        return self.tree_answers[path_key]

    def get_enum_values(self, schema_type):
        return self.prophet.mold_schema.get_enum_values(schema_type)

    @staticmethod
    def build_schema_answer(answer_result):
        return answer_result

    def negotiate(
        self, schema_answers: list[dict[str, list[PredictorResult]]]
    ) -> list[dict[str, list[PredictorResult]]]:
        """模型输出答案处理：
        1. 多组合并
        2. 同一element的多个PredictorResult拆为多组
        3. 数量字段加单位、币种
        """
        # 多组合并
        if self.merge_answers:
            for group in schema_answers:
                for column, items in group.items():
                    if len(items) > 1:
                        group[column] = [self.merge_answer_data(items)]

        # 同一element的多个PredictorResult拆为多组
        if self.divide_answers:
            column_answers = defaultdict(list)
            for group in schema_answers:
                for column, items in group.items():
                    column_answers[column].extend(items)
            split_schema_answers = []
            columns = list(column_answers.keys())
            for items in itertools.zip_longest(*column_answers.values()):
                group = {}
                for index, item in enumerate(items):
                    group[columns[index]] = [item] if item else []
                split_schema_answers.append(group)

            schema_answers = split_schema_answers

        # 补充单位
        for group in schema_answers:
            for column, items in group.items():
                column_schema_path = self.schema.sibling_path(column)
                column_schema = self.schema.mold_schema.find_schema_by_path(column_schema_path[1:])
                if column_schema.is_amount:
                    group[column] = [self.predict_amount_column(item) for item in items]

        for col, unit_col in self.unit_depend.items():
            for answer_result in schema_answers:
                predictor_result = answer_result.get(col)
                if not predictor_result:
                    continue
                units = []
                for result in predictor_result:
                    for i in result.element_results:
                        unit = find_unit_by_element_result(i)
                        if unit:
                            units.append(unit)
                schema = self.parent.find_child_schema(unit_col)
                if units and schema:
                    answer_result[unit_col] = [PredictorResult([u for u in units if u], schema=schema)]

        return schema_answers

    def predict_amount_column(self, item: PredictorResult):
        """把数量答案 扩充为 数量+单位+币种 二级字段"""
        element_results = item.element_results
        column_answers = []
        for child_schema in item.schema.children:
            if child_schema.name in ["金额", "数值"]:
                column_answers.append(PredictorResult(element_results, schema=child_schema, meta=item.meta))
            elif child_schema.name == "单位":
                units = [find_unit_by_element_result(result) for result in element_results]
                column_answers.append(PredictorResult([u for u in units if u], schema=child_schema))
            elif child_schema.name == "币种":
                currencies = [find_currency_element_result(self.pdfinsight, result) for result in element_results]
                column_answers.append(PredictorResult([c for c in currencies if c], schema=child_schema))
        return PredictorResultGroup([column_answers], schema=item.schema, element_results=element_results)

    def create_sub_predictors(self):
        if self.leaf:
            return []
        sub_predictors = [
            self.create_sub_predictor(item, primary_key=self.config.get("sub_primary_key"))
            for item in self.schema.children
            if self._is_configured_schema(item)
        ]
        children_predictor = self.create_children_predictor()
        if children_predictor:
            sub_predictors.insert(0, children_predictor)

        # NOTE: children_predictor 只是选了第一个字段名，可能对排序有问题
        high_priority_names = (self.sub_primary_key or [])[:]
        for sub_predictor in sub_predictors:
            if sub_predictor.depends:
                high_priority_names.extend(sub_predictor.depends)
        sub_predictors.sort(key=lambda x: 0 if x.schema_name in high_priority_names else 100)
        return sub_predictors

    def create_children_predictor(self):
        if self.leaf:
            return None
        all_children_names = [
            child.name
            for child in self.schema.children
            if not self._is_configured_schema(child) or child.name in self.sub_primary_key
        ]
        if not all_children_names:
            return None
        children_deputy_name = self.sub_primary_key[0] if self.sub_primary_key else all_children_names[0]
        children_deputy_schema = next(
            (child for child in self.schema.children if child.name == children_deputy_name), None
        )
        children_deputy_config = deepcopy(self.config)
        children_deputy_config.pop("sub_primary_key", None)
        children_deputy_config["path"] = self.config["path"] + ["PARENT_SUBSTITUE"]
        return SchemaPredictor(
            children_deputy_schema,
            children_deputy_config,
            prophet=self.prophet,
            parent=self,
            columns=all_children_names,
        )

    def _is_configured_schema(self, item):
        schemas_path = [json.loads(path_key) for path_key in self.root_config]
        for schema_path in schemas_path:
            if all(x in schema_path for x in item.path):
                return True
        return False

    def create_sub_predictor(self, schema, primary_key):
        predictor_config = self.root_config.get(schema.path_key, {"path": schema.path[:]})
        return SchemaPredictor(schema, predictor_config, prophet=self.prophet, parent=self)
