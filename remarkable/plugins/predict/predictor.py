import gc
import logging
import os
import pickle
import re
import shutil
from collections import OrderedDict
from copy import deepcopy
from functools import partial
from pathlib import Path

from remarkable.common.multiprocess import run_in_multiprocess
from remarkable.common.schema import Schema
from remarkable.common.storage import localstorage
from remarkable.common.util import clean_txt
from remarkable.config import get_config
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.predict.models.enum_value import EnumValue
from remarkable.plugins.predict.models.fixed_postion import FixedPosition
from remarkable.plugins.predict.models.multi_paras import MultiParas
from remarkable.plugins.predict.models.para_match import ParaMatch
from remarkable.plugins.predict.models.resume import Resume
from remarkable.plugins.predict.models.similar_section import SimilarSection
from remarkable.plugins.predict.models.sse.actual_controller import ActualController
from remarkable.plugins.predict.models.sse.consistent_actioner import ConsistentActioner
from remarkable.plugins.predict.models.sse.equity_pledge import EquityPledge
from remarkable.plugins.predict.models.sse.motion import Motion
from remarkable.plugins.predict.models.sse.other_related_agencies import OtherRelatedAgencies
from remarkable.plugins.predict.models.sse.part_stock_companies import PartStockCompanies
from remarkable.plugins.predict.models.sse.professional_qualifications import ProfessionalQualifications
from remarkable.plugins.predict.models.sse.shareholdersgt5 import ShareHoldersGt5
from remarkable.plugins.predict.models.syllabus_elt import SyllabusElt
from remarkable.plugins.predict.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.plugins.predict.models.table_row_filter import RowTableFilter
from remarkable.plugins.predict.models.title_content_group import TitleContentGroup
from remarkable.predictor.predict import AnswerPredictor, MoldSchema
from remarkable.pw_models.question import NewQuestion

from .answer import AnswerReader
from .models.chart_in_syl import ChartInSyllabus
from .models.model_base import EmptyPredictor
from .models.nearby_elt import NearbyElt

# from .models.partial_text_v2 import PartialTextV2
from .models.partial_text_v3 import PartialTextV3
from .models.remote_call import RemoteCall
from .models.score_filter import ScoreFilter
from .models.sse.associated_ralation import Correlation
from .models.sse.shareholder_relation import RelationshipOfShareholder
from .models.sse.subcompany import SSESubCompany
from .models.table_ai import AITable
from .models.table_kv import KeyValueTable
from .models.table_row import RowTable
from .models.table_row_3d import RowTable3D
from .models.table_tuple import TupleTable


def registered_classed():
    data = [
        ("empty", EmptyPredictor),
        ("fixed_position", FixedPosition),
        ("score_filter", ScoreFilter),
        ("partial_text", PartialTextV3),
        ("table_kv", KeyValueTable),
        ("table_row", RowTable),
        ("table_row_filter", RowTableFilter),
        ("table_tuple", TupleTable),
        ("table_row_3d", RowTable3D),
        ("table_ai", AITable),
        ("enum_value", EnumValue),
        ("multi_paras", MultiParas),
        ("syllabus_elt", SyllabusElt),
        ("syllabus_elt_v2", SyllabusEltV2),
        ("nearby_elt", NearbyElt),
        ("para_match", ParaMatch),
        ("title_content_group", TitleContentGroup),
        ("resume", Resume),
        ("similar_section", SimilarSection),
        ("chart_in_syl", ChartInSyllabus),
        ("share_holders", ShareHoldersGt5),
        ("sse_subcompany", SSESubCompany),
        ("shareholder_relation", RelationshipOfShareholder),  # 股东关系
        ("correlation", Correlation),  # 关联方及关联关系
        ("professional_qualifications", ProfessionalQualifications),  # 业务与技术-专业资质情况
        ("actual_controller", ActualController),  # 发行人基本情况-实际控制人
        ("consistent_actioner", ConsistentActioner),  # 发行人基本情况-实际控制人的一致行动人
        ("other_related_agencies", OtherRelatedAgencies),  # 本次发行概况-其他相关机构
        ("equity_pledge", EquityPledge),  # 发行人基本情况-控股股东、实际控制人股权质押情况
        ("motion", Motion),  # 议案名称和表决结果
        ("part_stock_companies", PartStockCompanies),  # 参股公司
    ]
    if get_config("web.enable_remote_model"):
        data.append(("remote_call", RemoteCall))
    _registered_classes = OrderedDict()
    for name, clz in data:
        _registered_classes.setdefault(name, clz)

    return _registered_classes


def model_class(name):
    _registered_classes = registered_classed()
    return _registered_classes.get(name)


def dump_path(schema_id, vid, *folders, filename=None, create_if_not_exist=True):
    if filename:
        filename = filename.replace("/", "|")
    _dir = os.path.join(get_config("training_cache_dir"), str(schema_id), str(vid), *folders)
    if create_if_not_exist and not os.path.exists(_dir):
        try:
            os.makedirs(_dir)
        except Exception as exp:
            logging.warning(exp)
    _path = _dir if not filename else os.path.join(_dir, filename)
    return _path


class BaseConductor:
    def __init__(self, mold, vid, file, config, pdfinsight, columns, sub_predictors, leaf):
        self.mold = mold
        self.schema = Schema(mold.data)
        self.vid = vid
        self.file = file
        self.config = config
        key = "_".join(config["path"])
        self.dump_path = dump_path(mold.id, self.vid, "predictors", filename="%s.pkl" % key)
        self.pdfinsight = pdfinsight
        self.columns = columns
        self.sub_predictors = sub_predictors
        self.leaf = leaf
        self.model_names = self.config.get("model", [])
        if isinstance(self.model_names, str):
            self.model_names = [self.model_names]
        self.models = OrderedDict()
        for name in self.model_names:
            _class = model_class(name)
            if _class:
                self.models[name] = _class(
                    self.mold,
                    self.config,
                    dump_path=self.dump_path,
                    pdfinsight=self.pdfinsight,
                    columns=self.columns,
                    sub_predictors=self.sub_predictors,
                    leaf=self.leaf,
                    file=self.file,
                )

    def load(self):
        model_info = {}
        if not os.path.exists(self.dump_path):
            logging.warning("can't find model features: %s", self.dump_path)
        else:
            with open(self.dump_path, "rb") as model_fp:
                model_info = pickle.load(model_fp)

        for name in self.models:
            self.models[name].model = model_info.get(name) or {}

        for sub in self.sub_predictors.values():
            sub.load()

    def run_train(self, **kwargs):
        """
        递归训练某个属性
        加载标注答案信息：data/training_cache/<mold_id>/answers/xxx.pkl
        模型存放于:data/training_data/<mold_id>/predictors/xxx.pkl
        """
        # if not any(x in self.config['path'] for x in ('05 监事会决议公告', '监事会召开日期')):
        #         #     return []
        # print('-------- run_train', self.config)
        key = "_".join(self.config["path"])
        # if os.path.exists(self.dump_path):
        #     logging.debug("%s pkl file exits, pass", key)
        #     return
        dataset = []
        logging.info("training model for column: %s", key)
        dataset_dir = Path(dump_path(self.mold.id, self.vid, "answers", str(key)))
        if dataset_dir.exists():
            for pkl in dataset_dir.glob("*.pkl"):
                with open(pkl, "rb") as dataset_fp:
                    dataset.extend(pickle.load(dataset_fp))
        else:
            dataset = None
        for model in self.models.values():
            model.train(dataset, **kwargs)
            model.print_model()
        for sub_predictor in self.sub_predictors.values():
            sub_predictor.run_train(**kwargs)
        self.dump()

    def dump(self):
        model_info = {name: m.model for name, m in self.models.items()}
        with open(self.dump_path, "wb") as model_fp:
            pickle.dump(model_info, model_fp)
        for sub_predictor in self.sub_predictors.values():
            sub_predictor.dump()

    def run_predict(self, crude_answers, **kwargs):
        # if self.config['path'] != ['05 监事会决议公告'] or '（二级）' not in self.config['path']:
        #     return []
        # print('-------- run_predict', self.config, self.columns)
        vaild_answers = []
        for _, model in self.models.items():
            results = model.run_predict(crude_answers, **kwargs)
            for ele, answers in results:
                for answer in answers:
                    # 补充子模型提取结果
                    # TODO: 根据 answer 主键来进行匹配
                    if model.run_sub_predictors:
                        for col, sub_predictor in self.sub_predictors.items():
                            kwargs.update({"candidates": [ele], "parent_answer": answer})
                            sub_answers = sub_predictor.run_predict(crude_answers, **kwargs)
                            if sub_answers:
                                if sub_predictor.leaf:
                                    answer[col] = [item[col] for item in sub_answers if col in item]
                                else:
                                    answer[col] = sub_answers

                vaild_answers.extend([item for item in answers if self.vaild_answer(item)])
                if not self.config.get("multi_elements", False) and vaild_answers:
                    break
            if vaild_answers and not self.config.get("multi_model", True):
                break
        for answer in vaild_answers:  # 补充枚举值
            for col, item in answer.items():
                enum_values = self.get_enum_values(self.config["path"][0], col)
                if not (item and enum_values):
                    continue
                for result in item if isinstance(item, list) else [item]:
                    if not result.value:
                        result.value = self.parse_enum(result)
        return vaild_answers

    def parse_enum(self, result):
        # todo：多选枚举值
        enum = self.config.get("enum", {})
        for res in result.data:
            text = getattr(res, "text", "") or getattr(res, "elt", {"text": ""}).get("text", "")
            text = clean_txt(text)
            if not text:
                continue
            for enum_val, regs in enum.get("regs", []):
                if any(re.search(reg, text) for reg in regs):
                    return enum_val
        return enum.get("default")

    def get_enum_values(self, parent_name, child_name):
        """
        获取子属性枚举值
        :param parent_name: str, 父节点
        :param child_name: str, 子节点
        :return: ['是', '否'] 非枚举值返回空list
        """
        values = []
        try:
            root_name = self.schema.schemas[0]["name"]
            _type = self.schema.schema_dict[root_name]["schema"][parent_name]["type"]
            if _type not in self.schema.enum_dict.keys():
                _type = self.schema.schema_dict[_type]["schema"][child_name]["type"]
            values = self.schema.enum_dict[_type]["values"]
        except KeyError:
            logging.debug("%s - %s 非枚举值", parent_name, child_name)
        return [value["name"] for value in values] if values else values

    def vaild_answer(self, item):
        """检查是否是有效的答案条目
        默认实现是填充了 1/4 以上的字段
        也可定义某些项目必填, 或者排除 `合计` 等条目
        """
        vaild_config = self.config.get("valid", {})
        if isinstance(item, dict):
            column_length = vaild_config.get("length", {})
            for key, val in item.items():
                if key in column_length:
                    filtered_idx = []
                    for idx, data in enumerate(val.data):
                        if len(data.text) not in range(*column_length[key]):
                            filtered_idx.append(idx)
                    for idx in sorted(filtered_idx, reverse=True):
                        val.data.pop(idx)
                    if not val.data:
                        item[key] = None

            acceptable_fullfill_percent = vaild_config.get("fullfill", 0)
            if not self.config.get("just_table"):
                _fullfill_percent = len([col for col in self.columns if item.get(col)]) / len(self.columns)
                if _fullfill_percent <= acceptable_fullfill_percent:
                    return False

            need_columns = vaild_config.get("needs", [])
            if any(col for col in need_columns if not item.get("col")):
                return False
        return True

    def print_model(self):
        for name, model in self.models.items():
            print("\n↓↓↓ MODEL:" + name + " ↓↓↓")
            model.print_model()


def get_model_object(
    mold,
    vid,
    config,
    create_new=False,
    pdfinsight=None,
    sub_schema_iter=None,
    predictor_config=None,
    default_model="score_filter",
    file=None,
):
    _columns = []
    _sub_predictors = OrderedDict()
    leaf = False
    if sub_schema_iter:
        for col_path, sub_iter in sub_schema_iter:
            col_name = col_path[-1]
            _columns.append(col_name)
            col_predictor_config = _find_predictor_config(col_path[1:], predictor_config)
            if not col_predictor_config:
                if sub_iter:
                    # 非叶子节点默认模型为 empty
                    col_predictor_config = {"path": col_path[1:], "model": "empty"}
                elif config.get("model") == "empty":
                    # empty 的叶子节点设为 default_model
                    col_predictor_config = {"path": col_path[1:], "model": default_model}
            if col_predictor_config:
                _sub_predictors[col_name] = get_model_object(
                    mold,
                    vid,
                    col_predictor_config,
                    create_new,
                    pdfinsight,
                    sub_iter,
                    predictor_config=predictor_config,
                    default_model=default_model,
                    file=file,
                )
    else:
        _columns.append(config["path"][-1])
        leaf = True

    config.setdefault("model", default_model)
    model_conductor = get_conductor_object(mold, vid, config, pdfinsight, _columns, _sub_predictors, leaf, file)
    return model_conductor


registered_conductor = {"base": BaseConductor}


def get_conductor_object(mold, vid, config, pdfinsight, _columns, _sub_predictors, leaf, file):
    conductor_name = config.get("conductor", "base")
    clazz = registered_conductor[conductor_name]
    return clazz(mold, vid, file, config, pdfinsight, _columns, _sub_predictors, leaf)


def _find_predictor_config(path, configs):
    for item in configs:
        if path == item["path"]:
            return item
    return None


def _dump_dataset(predictors, mold, meta):
    logging.info("loading file: %s, qid: %s", meta["fid"], meta["qid"])
    answer_reader = AnswerReader(meta["answer"])
    pdfinsight = PdfinsightReader(meta["pdfinsight_path"])
    for predictor in predictors:
        aim_path = predictor["path"]
        key, items = "_".join(aim_path), []
        for node in answer_reader.find_nodes(aim_path):
            elements = {}
            if node.isleaf():
                elements.update(_find_item_elements(pdfinsight, node.data))
            else:
                for leaf_node in node.descendants(only_leaf=True):
                    elements.update(_find_item_elements(pdfinsight, leaf_node.data))
            # data item 定义， 输入: elements dict, 输出: node
            data_item = DataItem(aim_path, {"elements": elements}, node, insight_path=meta["pdfinsight_path"])
            if predictor.get("need_syl"):  # 此模型需要目录信息
                data_item.data.setdefault("syllabuses", pdfinsight.syllabuses)
            items.append(data_item)
        pickle_path = dump_path(
            mold, meta["vid"], "answers", key, filename=f"{meta['qid']}.pkl", create_if_not_exist=True
        )
        with open(pickle_path, "wb") as file_obj:
            pickle.dump(items, file_obj)
    logging.info("dataset saved: %s, qid: %s", meta["fid"], meta["qid"])


async def dump_dataset(mold, start, end, predictor, tree_l=None, vid=0):
    """准备用于训练和评估的数据集
    dataset = [ DataItem, ...]
    DataItem {
        data: {},  # input
        predict: AnswerNode,  # output
        path: ["xx", "yy"]  # train data
        answer: AnswerNode,  # train data
        ...
    }
    """
    predictor_config = []
    trained_files = []

    def _load_predictor_config(item):
        if any(m.need_training for m in item.models.values()):
            predictor_config.append(item.config)
        for sub in item.sub_predictors.values():
            _load_predictor_config(sub)

    async def make_tasks():
        nonlocal trained_files
        tasks = []
        files = await NewFile.list_by_range(mold, start, end, tree_l=tree_l)
        for idx, _file in enumerate(files):
            logging.info("loading file: %s", _file.id)
            question = await NewQuestion.find_by_fid_mid(_file.id, mold)
            if not question.answer or not _file or not _file.pdfinsight_path():
                logging.warning("No answer found in file: %s, skip qid: %s", _file.id, question.id)
                continue
            meta = {
                "fid": _file.id,
                "qid": question.id,
                "vid": vid,
                "answer": question.answer,
                "pdfinsight_path": localstorage.mount(_file.pdfinsight_path()),
            }
            trained_files.append(_file.id)
            tasks.append(meta)
            # 50 个文档推一次, 清空 tasks, 释放内存
            if (idx + 1) % 50 == 0:
                run_in_multiprocess(partial(_dump_dataset, predictor_config, mold), tasks)
                del tasks
                gc.collect()
                tasks = []
        if tasks:
            run_in_multiprocess(partial(_dump_dataset, predictor_config, mold), tasks)

    # 加载实际的模型配置
    _load_predictor_config(predictor)

    await make_tasks()
    return trained_files


def _find_item_elements(_pdfinsight, item):
    _elements = {}
    for data in item["data"]:
        data.setdefault("elements", [])
        for box in data["boxes"]:
            outline = (box["box"]["box_left"], box["box"]["box_top"], box["box"]["box_right"], box["box"]["box_bottom"])
            for _, ele in _pdfinsight.find_elements_by_outline(box["page"], outline):
                _elements[ele["index"]] = ele
                data["elements"].append(ele["index"])
    return _elements


class DataItem:
    def __init__(self, path, data, answer, predict_answer=None, insight_path=None):
        self.path = path
        self.data = data
        self.answer = answer
        self.predict = predict_answer
        self.insight_path = insight_path


class AIAnswerPredictor(AnswerPredictor):
    def __init__(self, mold, *args, **kwargs):
        super().__init__(mold, *args, **kwargs)
        self.vid = kwargs.get("vid", 0)
        # self.load_predictor_config(mold, kwargs.get("predictors", []))
        self.predictor_config = kwargs.get("predictors", [])
        self.default_model = kwargs.get("default_model", "score_filter")
        self.predictor = self.build_predictor()
        self.model_loaded = False
        self.model_results = {}

    def build_predictor(self):
        # TODO: merge common.Schema and prompter.Schema
        schema = Schema(self.mold.data)
        return get_model_object(
            self.mold,
            self.vid,
            {"path": [self.mold.name], "model": "empty", "same_elt_with_parent": False},
            pdfinsight=self.reader,
            predictor_config=self.predictor_config,
            sub_schema_iter=schema.iter_hierarchy(),
            default_model=self.default_model,
            file=self.file,
        )

    def load_model(self):
        if not self.model_loaded:
            self.predictor.load()
            self.model_loaded = True

    def train(self):
        self.clear_model()
        self.predictor.run_train()

    def clear_model(self):
        predictor_dir = dump_path(self.mold.id, self.vid, "predictors", create_if_not_exist=False)
        if os.path.exists(predictor_dir):
            shutil.rmtree(predictor_dir)
        dump_path(self.mold.id, self.vid, "predictors")

    def measure(self):
        self.predictor.run_measure()

    # def predict(self, crude_answers):
    #     self.load()
    #     result_of_predictor = self.predictor.run_predict(crude_answers)
    #     return result_of_predictor[0] if result_of_predictor else {}

    def predict_answer(self):
        self.load_model()
        predictor_results = self.predictor.run_predict(self.crude_answer)
        if predictor_results:
            self.model_results = predictor_results[0]
        if self.answer_version < "2.2":
            raise NotImplementedError("not implement for answer version under 2.2")
        return self.answer_v_2_2()

    def analysis_v_2_2(self):
        def build_schema(schema_info):
            data = {
                "type": schema_info.get("type"),
                "label": schema_info.get("name"),
                "words": schema_info.get("words", ""),
                "multi": schema_info.get("multi"),
                "required": schema_info.get("required"),
            }
            if data["label"] == self.root_schema_name:  # 根结点没有这两项
                del data["multi"]
                del data["required"]
            return {"data": data}

        def build_col_data(schema_data, result):
            items = []
            for res_obj in result:
                func_name = "_".join(["build", res_obj.elt_typ])
                if hasattr(self, func_name):
                    func = getattr(self, func_name)
                    item = func(res_obj)
                    if item:
                        items.append(item)
                    else:
                        logging.debug("can't build col for result: %s", result)
            return items

        def build_col(schema_info, path):
            schema = build_schema(schema_info)

            col = {
                "schema": schema,
                "score": -1,
                "data": [],
                "key": "[%s]" % ",".join(['"%s:%s"' % (key, idx) for key, idx in path]),
            }
            return col

        def build_result(schema, result, path):
            cols = []
            for col_name in schema["orders"]:
                col_attributes = deepcopy(schema["schema"][col_name])
                col_attributes.update({"name": col_name})
                col_res = result.get(col_name, [])
                # 这里做了兼容， 字段的结果是 ResultOfPredictor 或者 [ResultOfPredictor, ...] 都可以
                for idx, item in enumerate(col_res if isinstance(col_res, list) else [col_res]):
                    col_path = path + [(col_name, idx)]
                    col = build_col(col_attributes, col_path)
                    if col_attributes["type"] in MoldSchema.basic_types:  # 基本类型
                        if item and item.data is not None:
                            col["data"] = build_col_data(col_attributes, item.data)
                            if not col["data"]:
                                continue
                            col["score"] = item.score
                            cols.append(col)
                    elif col_attributes["type"] in self.schema_type_dict:  # 枚举
                        if item and item.data is not None:
                            col["data"] = build_col_data(col_attributes, item.data)
                            col["value"] = item.value
                            col["score"] = item.score
                            cols.append(col)
                    elif col_attributes["type"] in self.schema_dict:  # 子类型
                        sub_schema = self.schema_dict[col_attributes["type"]]
                        cols.extend(build_result(sub_schema, item, col_path))
            return cols

        return build_result(self.schema_dict[self.root_schema_name], self.model_results, [(self.root_schema_name, 0)])
