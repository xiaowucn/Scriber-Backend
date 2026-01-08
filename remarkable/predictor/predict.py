# pylint: skip-file
import datetime
import functools
import json
import logging
import os
import re
from collections import Counter, OrderedDict, defaultdict
from copy import deepcopy

from remarkable import config
from remarkable.common.box_util import get_bound_box
from remarkable.common.constants import AIStatus, LLMStatus, MoldType, SpecialAnswerType
from remarkable.common.enums import ClientName
from remarkable.common.exceptions import CmfChinaAPIError, InvalidAnswerError, NoEnabledModelError
from remarkable.common.pattern import (
    PATTERNS,
    lst_colon,
    pat_cell_filt,
    pat_col_title_esc,
    pat_conform_to_sylla,
    pat_mean,
)
from remarkable.common.schema import Schema
from remarkable.common.storage import localstorage
from remarkable.common.util import (
    DATE_PATTERN,
    ClassBakery,
    clean_txt,
    cut_text,
    generate_timestamp,
    group_cells,
    index_in_space_string,
    is_valid_answer,
    md5,
    outline_to_box,
)
from remarkable.data.answer_tools import load_key_path
from remarkable.db import pw_db
from remarkable.models.cmf_china import CmfModelUsageCount, CmfMoldModelRef
from remarkable.models.model_version import NewModelVersion
from remarkable.models.new_file import NewFile
from remarkable.models.new_model_answer import ModelAnswer
from remarkable.models.new_user import ADMIN
from remarkable.optools.table_util import TableUtil
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.fileapi.financial_attribute import FinancialAttribute
from remarkable.plugins.hkex.common import elt_text_list
from remarkable.predictor.mold_schema import MoldSchema
from remarkable.pw_models.model import NewMold, NewSpecialAnswer
from remarkable.pw_models.question import NewQuestion
from remarkable.schema.answer import UserAnswer
from remarkable.service.prompter import predict_crude_answer_delegate
from remarkable.utils.answer_util import AnswerUtil

DEFAULT_POOL_KEY = "default"
memory_dir = config.get_config("web.predict_from_memory.data_dir")


class AnswerPredictorFactory(ClassBakery):
    CLASSNAME_OVER_CONFIG = None
    cls_cache = {}
    config_entry = "web.classes.answer_predictor"

    @classmethod
    def create(cls, mold, *args, **kwargs):
        clazz = cls.get_class(mold.name)
        if not clazz:
            from remarkable.plugins.predict.config.common_predictor import CommonPredictor

            clazz = CommonPredictor
            # return None
        return clazz(mold, *args, **kwargs)


async def get_anno_mold(mold):
    convert_mapping = config.get_config("web.answer_convert") or {}
    anno_mold_name = None
    for source, aim in convert_mapping.items():
        if aim == mold.name:
            anno_mold_name = source
            break
    if not anno_mold_name:
        return None
    anno_mold = await NewMold.find_by_kwargs(name=anno_mold_name)
    return anno_mold


async def record_cmf_model_count(question: NewQuestion, success_or_fail: bool = True):
    if not (cmf_model := await CmfMoldModelRef.find_by_kwargs(mold_id=question.mold)):
        return
    date = int(
        datetime.datetime.combine(
            datetime.datetime.now(datetime.UTC), datetime.time(0, 0, 0, 0, datetime.UTC)
        ).timestamp()
    )
    model_count_ref = await CmfModelUsageCount.find_by_kwargs(model_id=cmf_model.model_id, date=date)
    if model_count_ref:
        if success_or_fail:
            model_count_ref.success_count += 1
        else:
            model_count_ref.failure_count += 1
        await pw_db.update(model_count_ref)
    else:
        if success_or_fail:
            await pw_db.create(
                CmfModelUsageCount, model_id=cmf_model.model_id, success_count=1, failure_count=0, date=date
            )
        else:
            await pw_db.create(
                CmfModelUsageCount, model_id=cmf_model.model_id, success_count=0, failure_count=1, date=date
            )


async def predict_answer(question, vid=None, special_rules=None, test_accuracy=False):
    """
    预测完答案之后,应该调用 question.set_answer() & NewQuestionService.post_pipe()
    """
    try:
        preset_answer, vid = await _predict_answer(question, vid, special_rules, test_accuracy=test_accuracy)
    except NoEnabledModelError:
        await question.update_record(exclusive_status=AIStatus.DISABLE)
        raise
    except CmfChinaAPIError:
        await question.update_record(exclusive_status=AIStatus.FAILED)
        await record_cmf_model_count(question, False)
        raise
    except Exception:
        await question.update_record(exclusive_status=AIStatus.FAILED)
        raise
    else:
        if ClientName.cmfchina == config.get_config("client.name"):
            await record_cmf_model_count(question, True)

    if not is_valid_answer(preset_answer):
        await question.update_record(exclusive_status=AIStatus.FAILED)
        raise InvalidAnswerError(f"Not a valid answer, fid: {question.fid}")
    if test_accuracy:
        await NewSpecialAnswer.update_or_create_crude(
            question.id, SpecialAnswerType.TEST_ACCURACY_PRESET.value, preset_answer
        )
        await question.update_record(exclusive_status=AIStatus.FINISH)
    else:
        await question.update_record(preset_answer=preset_answer, exclusive_status=AIStatus.FINISH)

    await ModelAnswer.update_or_create(vid, question.id, preset_answer)

    return preset_answer


async def _predict_answer(question: NewQuestion, vid=None, special_rules=None, test_accuracy=False):
    from remarkable.predictor.default_predictor.utils import DefaultProphet

    # schema
    answer = None
    question = await NewQuestion.find_by_id(question.id)  # QuestionWithFK' object has no attribute 'fetch_metadata
    mold = await NewMold.find_by_id(question.mold)
    file = await NewFile.find_by_id(question.fid)
    if file.is_excel and ClientName.cmfchina == config.get_config("client.name"):
        answer, vid = await _predict_excel_file_answer(file, question, mold, vid)
    elif file.pdfinsight:
        assert localstorage.exists(file.pdfinsight_path())
        if vid is None:
            vid = await NewModelVersion.get_enabled_version(mold.id)
        if test_accuracy:
            crude_answer = await pw_db.scalar(
                NewSpecialAnswer.select(NewSpecialAnswer.data)
                .where(
                    NewSpecialAnswer.qid == question.id,
                    NewSpecialAnswer.answer_type == SpecialAnswerType.TEST_ACCURACY_CRUDE.value,
                )
                .order_by(NewSpecialAnswer.id.desc())
            )
            # NOTE: macos中同时使用 peewee_async 和 gino , celery 中会报下面的错误， linux中不会出现
            # objc[46717]: +[NSNumber initialize] may have been in progress in another thread when fork() was called.
            # We cannot safely call it or ignore it in the fork() child process. Crashing instead.
            # Set a breakpoint on objc_initializeAfterForkError to debug.
        else:
            crude_answer = await pw_db.scalar(
                NewQuestion.select(NewQuestion.crude_answer).where(NewQuestion.id == question.id)
            )
        anno_mold = await get_anno_mold(mold)
        anno_crude_answer = None
        if anno_mold:  # 导出schema => 标注schema
            anno_crude_answer = await predict_crude_answer_delegate(file.id, question.id, mold=anno_mold)
        from remarkable.predictor.helpers import create_predictor_prophet

        model_version = await NewModelVersion.find_by_id(vid)
        metadata = await question.fetch_metadata()
        metadata["pdf_path"] = localstorage.mount(file.pdf_path())
        metadata["fid"] = file.id
        if cmf_model := await CmfMoldModelRef.get_enabled_model(mold.id):
            metadata["model_url"] = cmf_model.address
            metadata["model_name"] = cmf_model.name
            metadata["model_id"] = cmf_model.id
            metadata["file_name"] = file.name
        prophet = create_predictor_prophet(
            mold,
            model_version=model_version,
            file=file,
            crude_answer=question.crude_answer,
            metadata=metadata,
            special_rules=special_rules,
        )
        if isinstance(prophet, DefaultProphet) and not vid:
            raise NoEnabledModelError
        await question.update_record(exclusive_status=AIStatus.DOING)
        answer = prophet.run_predict(
            crude_answer=crude_answer,
            pdfinsight_path=file.pdfinsight_path(),
            file=file,
            metadata=metadata,
            anno_mold=anno_mold,
            anno_crude_answer=anno_crude_answer,
            special_rules=special_rules,
        )
        if special_rules:
            from remarkable.service.new_question import replace_answer_item

            origin_preset_answer = question.preset_answer
            if origin_preset_answer:
                answer = replace_answer_item(origin_preset_answer, answer, special_rules)
        answer = prophet.post_process(answer)

        if mold.mold_type == MoldType.HYBRID:
            answers_data = [UserAnswer._make([ADMIN.id, ADMIN.name, answer])]
            if question.llm_status == LLMStatus.FINISH:
                answers_data.append(UserAnswer._make([ADMIN.id, ADMIN.name, question.preset_answer]))
            answer = AnswerUtil.merge_answers(answers_data, schema_data=mold.data)

    return answer, vid


async def _predict_excel_file_answer(file, question, mold=None, vid=None):
    from remarkable.predictor.default_predictor.utils import DefaultProphet
    from remarkable.predictor.helpers import create_predictor_prophet

    if vid is None:
        vid = await NewModelVersion.get_enabled_version(mold.id)
    metadata = await question.fetch_metadata()
    metadata["fid"] = file.id
    if cmf_model := await CmfMoldModelRef.get_enabled_model(mold.id):
        metadata["model_url"] = cmf_model.address
        metadata["model_name"] = cmf_model.name
        metadata["model_id"] = cmf_model.id
        metadata["file_name"] = file.name
        metadata["excel_path"] = file.path()
    model_version = await NewModelVersion.find_by_id(vid)
    prophet = create_predictor_prophet(
        mold,
        model_version=model_version,
        file=file,
        crude_answer=question.crude_answer,
        metadata=metadata,
        special_rules=[],
    )
    if isinstance(prophet, DefaultProphet) and not vid:
        raise NoEnabledModelError
    await question.update_record(exclusive_status=AIStatus.DOING)
    answer = prophet.run_predict(
        crude_answer=None,
        pdfinsight_path=file.pdfinsight_path(),
        file=file,
        metadata=metadata,
        anno_mold=None,
        anno_crude_answer=None,
        special_rules=[],
        predict_excel=True,
    )
    answer = prophet.post_process(answer)

    return answer, vid


async def answer_convert(question: NewQuestion):
    fid = question.data["file_id"]
    _file = await NewFile.find_by_id(fid)
    _mold = await NewMold.find_by_id(question.mold)
    answer_convert_config = config.get_config("web.answer_convert") or {}
    if _mold.name in answer_convert_config.values():
        # 上传文件时指定新scheme 直接返回其答案
        return question.answer
    aim_mold_name = answer_convert_config.get(_mold.name)
    if not aim_mold_name:
        return None
    aim_mold = await NewMold.find_by_name(aim_mold_name)
    if not aim_mold:
        raise Exception(f"can't find convert aim mold: {aim_mold_name}")
    predictor = AnswerPredictorFactory.create(aim_mold, file=_file, anno_answer=question.answer, metadata={})
    return predictor.predict_answer()


def table_element_content_text(ele):
    def cell_ordering(row_and_col):
        row, col = row_and_col.split("_")
        return int(row) * 1000 + int(col)

    return "|".join([v.get("text") for k, v in sorted(ele.get("cells").items(), key=lambda x: cell_ordering(x[0]))])


def split_chars(chars, interval=100):
    lines = []
    for char in chars:
        if lines:
            line_break = char["box"][1] > lines[-1][-1]["box"][3] or char["box"][0] > lines[-1][-1]["box"][2] + interval
            cross_page = char["page"] != lines[-1][-1]["page"]
            if line_break or cross_page:
                lines.append([char])
            else:
                lines[-1].append(char)
        else:
            lines.append([char])
    return lines


def get_tbl_text(tbl, aim_cells=None):
    tbl_txt = []
    cells_by_row, _ = group_cells(tbl["cells"])
    for row in sorted(map(int, cells_by_row.keys())):
        cells = cells_by_row.get(str(row), {})
        tr_txt = []
        for col in sorted(map(int, cells.keys())):
            cell = cells.get(str(col))
            if (not aim_cells) or ("_".join(map(str, [row, col])) in aim_cells):
                if not cell.get("dummy"):
                    tr_txt.append(cell["text"])
        if tr_txt:
            tbl_txt.append("".join(tr_txt))
    return "\n".join(tbl_txt)


def revise_result_node(item):
    if not isinstance(item, ResultOfPredictor):
        return ResultOfPredictor([CharResult([], text=item)])
    return item


class AnswerPredictor:
    keyword_patterns = {}

    def __init__(self, mold, file=None, crude_answer=None, metadata=None, **kwargs):
        self.mold = mold
        self.root_schema_name = mold.data["schemas"][0]["name"]
        self.schema_dict = {schema["name"]: schema for schema in mold.data["schemas"]}
        self.schema_type_dict = {schema_type["label"]: schema_type for schema_type in mold.data["schema_types"]}
        self.checksum = mold.checksum
        self.column_analyzers = {}  # 存放要预测的属性
        self.file = file
        self.crude_answer = crude_answer or {}  # 预测位置元素块
        self.prompter = None
        self.confirmed_answer = (metadata or {}).get("confirmed_answer")
        self.extract_methods = (metadata or {}).get("extract_methods")
        self.options = kwargs
        self.answer_version = str(config.get_config("prompter.answer_version", "2.2"))
        self.load_patterns()
        if self.options.get("hkex_meta"):
            self.hkex_meta = self.options.get("hkex_meta")
        self.reader = None
        if self.file and self.file.pdfinsight_path():
            self.reader = PdfinsightReader(localstorage.mount(self.file.pdfinsight_path()))
        self.schema_obj = Schema(self.mold.data)

    def load_patterns(self):
        for col_name, keyword_pattern in self.keyword_patterns.items():
            patterns = (self.options.get("patterns") or {}).get(col_name)
            if patterns:
                self.column_analyzers.update(
                    {col_name: functools.partial(self.pattern_extract, col_name, patterns, keyword_pattern)}
                )

    def pattern_extract(self, attr, patterns, keyword_pattern, **kwargs):
        from remarkable.plugins.predict.models.partial_text_v2 import match_pattern

        items = []
        limit_of_crude_elts = config.get_config("web.limit_of_crude_elts", 3)  # 读取预测元素块的个数
        elements = self.crude_answer.get(attr, [])[:limit_of_crude_elts]
        for _idx, element in enumerate(elements):
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "PARAGRAPH":
                cleaned_text = clean_txt(element["text"])
                groups = keyword_pattern.finditer(cleaned_text)
                for group in groups:
                    c_start, c_end = group.start(), group.end()
                    prev_text = cut_text(element["text"][:c_start], "left")
                    after_text = cut_text(element["text"][c_end:], "right")
                    for pattern in patterns:
                        if match_pattern(pattern[0], prev_text) and match_pattern(pattern[1], after_text):
                            sp_start, sp_end = index_in_space_string(element["text"], (c_start, c_end))
                            items.append(ParaResult(element["chars"][sp_start:sp_end], element))
                            break
                    if items:
                        break
                if items:
                    break
        return ResultOfPredictor(items, crude_elts=elements)

    def predict_answer(self):
        if self.answer_version < "2.2":
            return self.answer_v_1_0()
        else:
            return self.answer_v_2_2()

    def answer_v_1_0(self):
        user_answer = {}
        answer = {"schema": {}, "userAnswer": user_answer}

        # schema
        answer["schema"].update(
            {
                "schema_types": self.mold.data.get("schema_types", []),
                "schemas": self.mold.data.get("schemas", []),
                "version": self.checksum,
            }
        )

        # userAnswer
        for col in self.analysis():
            user_answer[col["md5"]] = col

        return answer

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
            limit_of_preset_num = config.get_config("web.limit_of_preset_num", 10)  # 限制预测答案的个数
            for res_obj in result[:limit_of_preset_num]:
                func_name = "_".join(["build", res_obj.elt_typ])
                if hasattr(self, func_name):
                    func = getattr(self, func_name)
                    col_data = func(res_obj)
                    if col_data:
                        items.append(col_data)
            return items

        def build_col(schema_info, parent_path, index_l):
            schema = build_schema(schema_info)

            path_l = deepcopy(parent_path)
            path_l.append(schema_info["name"])

            col = {
                "schema": schema,
                "score": -1,
                "data": [],
                "key": json.dumps([":".join([path, idx]) for path, idx in zip(path_l, index_l)]),
            }
            return col

        cols = []

        for col_name in self.schema_dict[self.root_schema_name]["orders"]:
            col_attributes = deepcopy(self.schema_dict[self.root_schema_name]["schema"][col_name])
            col_attributes.update({"name": col_name})
            # print('col_name', col_attributes)
            col = build_col(col_attributes, [self.root_schema_name], index_l=("0", "0"))
            if col_name in self.column_analyzers:
                logging.info("predicting col %s for file %s", col_name, self.file.id)
                result = self.column_analyzers[col_name](col=col, col_type=col_attributes.get("type"))
                if col_attributes["type"] in MoldSchema.basic_types:  # 基本类型
                    if result.data:
                        col["data"] = build_col_data(col_attributes, result.data)
                        col["score"] = result.score
                        cols.append(col)
                elif col_attributes["type"] in self.schema_type_dict:  # 枚举
                    if result and result.data is not None:
                        col["data"] = build_col_data(col_attributes, result.data)
                        col["value"] = result.value
                        col["score"] = result.score
                        cols.append(col)
                elif col_attributes["type"] in self.schema_dict:  # 子类型
                    if result:
                        for idx, each in enumerate(result):
                            for sub_col_name in self.schema_dict[col_attributes["type"]].get("orders", []):
                                sub_col_attributes = deepcopy(
                                    self.schema_dict[col_attributes["type"]]["schema"][sub_col_name]
                                )
                                sub_col_attributes.update({"name": sub_col_name})
                                sub_col = build_col(
                                    sub_col_attributes,
                                    [self.root_schema_name, col_attributes["type"]],
                                    ("0", str(idx), "0"),
                                )
                                if each.get(sub_col_name):
                                    sub_col["data"] = build_col_data(sub_col_attributes, each[sub_col_name].data)
                                    sub_col["score"] = each[sub_col_name].score
                                    if hasattr(each[sub_col_name], "value"):  # 子类型可能是枚举
                                        sub_col["value"] = each[sub_col_name].value
                                    cols.append(sub_col)
        return cols

    def answer_v_2_2(self):
        # schema
        schema = {}
        schema.update(
            {
                "schema_types": self.mold.data.get("schema_types", []),
                "schemas": self.mold.data.get("schemas", []),
                "version": self.checksum,
            }
        )

        # userAnswer
        userAnswer = {"version": "2.2", "items": []}
        for col in self.analysis_v_2_2():
            userAnswer["items"].append(col)

        answer = {"schema": schema, "userAnswer": userAnswer}
        return answer

    @staticmethod
    def build_label(label_res):
        return label_res.items

    @staticmethod
    def build_char(char_res):
        if char_res.chars is None:
            return {}

        page_chars = {}
        for char in char_res.chars:
            page_chars.setdefault(int(char["page"]), []).append(char)
        res = {"boxes": [], "handleType": "wireframe"}

        for page in sorted(page_chars):
            lines = split_chars(page_chars[page])
            for chars in lines:
                line_box = get_bound_box([char["box"] for char in chars])  # (左，上，右，下)
                comp_text = "".join([char["text"] for char in chars])
                res["boxes"].append(
                    {
                        "page": page,
                        "box": outline_to_box(line_box),
                        "text": comp_text,
                    }
                )
        if char_res.text:
            if res["boxes"]:
                res["boxes"][0]["text"] = str(char_res.text)
                for box in res["boxes"][1:]:
                    box["text"] = ""
            else:
                res["boxes"].append(
                    {
                        "page": 0,
                        "box": {"box_top": 0, "box_right": 0, "box_bottom": 0, "box_left": 0},
                        "text": str(char_res.text),
                    }
                )
        if char_res.confirm:
            res["confirm"] = True
        return res

    @staticmethod
    def build_paragraph(para_res):
        res = {"boxes": [], "handleType": "wireframe"}
        lines = split_chars(para_res.chars)
        for chars in lines:
            line_box = get_bound_box([char["box"] for char in chars])  # (左，上，右，下)
            comp_text = "".join([char["text"] for char in chars])
            if comp_text and re.sub(r"\s+", "", comp_text):  # 过滤空行
                res["boxes"].append(
                    {
                        "page": para_res.elt["page"],
                        "box": outline_to_box(line_box),
                        "text": comp_text,
                    }
                )
        if para_res.confirm:
            res["confirm"] = True
        return res

    @staticmethod
    def build_outline(obj):
        res = {"boxes": [], "handleType": "wireframe"}
        res["boxes"].append(
            {
                "page": obj.page,
                "box": outline_to_box(obj.outline),
                "text": obj.text,
            }
        )
        if obj.confirm:
            res["confirm"] = True
        return res

    @staticmethod
    def build_table(tbl_res):
        res = {"boxes": [], "handleType": "wireframe"}

        page = tbl_res.elt["page"]
        if tbl_res.cells:
            chars = []
            for cell in tbl_res.cells:
                chars.extend(tbl_res.elt["cells"].get(cell, {}).get("chars", []))
            if chars:
                page = chars[0]["page"]
            lines = split_chars(chars, interval=1000000)  # 表格内默认画一个框
        else:
            lines = [[{"box": tbl_res.elt.get("outline"), "text": get_tbl_text(tbl_res.elt)}]]

        if not lines:
            return None

        for chars in lines:
            line_box = get_bound_box([char["box"] for char in chars])
            comp_text = "".join([char["text"] for char in chars])
            if comp_text and re.sub(r"\s+", "", comp_text):  # 过滤空行
                res["boxes"].append(
                    {
                        "page": page,
                        "box": outline_to_box(line_box),
                        "text": comp_text,
                    }
                )
        if tbl_res.confirm:
            res["confirm"] = True
        return res

    def join_path(self, parent, name):
        path = deepcopy(parent)
        path.append(name)
        return path

    def path_md5(self, path):
        path_str = "[{}]".format(",".join(['"{}"'.format(p) for p in path]))
        return md5(path_str.encode("utf8"))

    def build_col(self, name, defination, parent_path):
        path = self.join_path(parent_path, name)

        attributes = []
        if defination["type"] in MoldSchema.basic_types:
            _attr = deepcopy(defination)
            _attr["name"] = name
            attributes.append(_attr)
        elif defination["type"] in self.schema_dict:
            sub_schema = self.schema_dict.get(defination["type"])
            for field_name in sub_schema.get("orders", []):
                field_defination = sub_schema["schema"][field_name]
                _attr = deepcopy(field_defination)
                _attr["name"] = field_name
                attributes.append(_attr)
        else:
            # TODO: enum type?
            pass

        col = {"schemaPath": path, "md5": self.path_md5(path), "attributes": attributes, "items": []}
        col.update(defination)
        col["label"] = name

        return col

    def analysis(self):
        cols = []
        path = [self.root_schema_name]
        cols.append(
            {
                "label": self.root_schema_name,
                "type": self.root_schema_name,
                "attributes": [],
                "schemaPath": path,
                "md5": self.path_md5(path),
                "items": [],
            }
        )

        def build_col_items(col_name, col, result):
            items = []
            if col["type"] in MoldSchema.basic_types:  # 基本类型
                for each in result.data:
                    func_name = "_".join(["build", each.elt_typ, "field"])
                    if hasattr(self, func_name):
                        func = getattr(self, func_name)
                        items.append({"fields": [func(col_name, each)]})
            elif col["type"] in self.schema_dict:  # 子类型
                if result:
                    for item in result:
                        tmp = {"fields": []}
                        for sub_col_name in self.schema_dict.get(col["type"]).get("orders", []):
                            fields = item[sub_col_name].data
                            # print('sub_col_name', sub_col_name)
                            if fields:
                                for each in fields:
                                    func_name = "_".join(["build", each.elt_typ, "field"])
                                    if hasattr(self, func_name):
                                        func = getattr(self, func_name)
                                        tmp["fields"].append(func(sub_col_name, each))
                            else:
                                tmp["fields"].append(self.empty_field(sub_col_name))
                        items.append(tmp)
            # todo:枚举
            return items

        for col_name, col_attributes in self.schema_dict[self.root_schema_name]["schema"].items():
            col = self.build_col(col_name, col_attributes, path)
            if col_name in self.column_analyzers:
                # print('col_name', col_name, col_attributes)
                result = self.column_analyzers[col_name](col=col, col_type=col_attributes.get("type"))
                items = build_col_items(col_name, col, result)
                for item in items:
                    item["schemaMD5"] = col["md5"]
                    col["items"].append(item)
            cols.append(col)

        return cols

    def build_paragraph_field(self, typ, para_res):
        field = {"components": [], "label": "".join([char["text"] for char in para_res.chars]), "name": typ}
        lines = split_chars(para_res.chars)
        for chars in lines:
            line_box = get_bound_box([char["box"] for char in chars])
            comp_text = "".join([char["text"] for char in chars])
            if comp_text and re.sub(r"\s+", "", comp_text):  # 过滤空行
                field["components"].append(
                    {
                        "text": comp_text,
                        "frameData": {
                            "id": "page%s:%s" % (int(para_res.elt["page"]) + 1, generate_timestamp()),
                            "height": line_box[3] - line_box[1],
                            "width": line_box[2] - line_box[0],
                            "top": line_box[1],
                            "left": line_box[0],
                            "topleft": [line_box[1], line_box[0]],
                            "page": para_res.elt["page"],
                            "type": typ,
                        },
                    }
                )
        if typ not in self.mold["schemas"][0]["schema"]:
            field["label"] = "|_|_|".join([comp.get("text", "") for comp in field["components"]])
        return field

    def build_table_field(self, typ, tbl_res):
        tbl, cells = tbl_res.elt, tbl_res.cells
        label = get_tbl_text(tbl, cells)
        field = {"components": [], "label": label, "name": typ}

        page = tbl["page"]
        if cells:
            chars = []
            for cell in cells:
                chars.extend(tbl["cells"].get(cell, {}).get("chars", []))
            if chars:
                page = chars[0]["page"]
            lines = split_chars(chars, interval=1000000)  # 表格内默认画一个框
        else:
            lines = [[{"box": tbl.get("outline"), "text": label}]]

        for chars in lines:
            line_box = get_bound_box([char["box"] for char in chars])
            comp_text = "".join([char["text"] for char in chars])
            if comp_text and re.sub(r"\s+", "", comp_text):  # 过滤空行
                field["components"].append(
                    {
                        "text": comp_text,
                        "frameData": {
                            "id": "page%s:%s" % (int(page) + 1, generate_timestamp()),
                            "height": line_box[3] - line_box[1],
                            "width": line_box[2] - line_box[0],
                            "top": line_box[1],
                            "left": line_box[0],
                            "topleft": [line_box[1], line_box[0]],
                            "page": page,
                            "type": typ,
                        },
                    }
                )
        return field

    def empty_field(self, typ):
        return {"components": [], "label": "", "name": typ}

    def b_aim_elt(self, elt, regs, anchor_regs=None, pass_regs=None, near_by=None, **kwargs):
        """
        判断是否为目标元素块
        """
        if not (regs or anchor_regs or pass_regs):
            return True

        # `附近/大纲`必须出现某些关键词
        if anchor_regs:
            if not near_by:
                near_by = {"step": -1, "amount": 5, "include": True}
            prev_elts = self.reader.find_elements_near_by(elt["index"], **near_by)
            flag = False
            for prev_elt in prev_elts:
                text_l = elt_text_list(prev_elt)
                if any(any(reg.search(_t) for _t in text_l) for reg in anchor_regs):
                    flag = True
                    break
            elt_syllabus_id = elt.get("syllabus", None)
            if elt_syllabus_id and not flag:
                syllabus_title = self.reader.syllabus_dict[elt_syllabus_id]["title"]
                if any(reg.search(syllabus_title) for reg in anchor_regs):
                    flag = True
            if not flag:
                return False

        # 元素块本身满足条件
        text_l = elt_text_list(elt)
        if regs and any(any(reg.search(_t) for _t in text_l) for reg in regs):
            return True
        return True

    def get_crude_elements(self, attr, col_type):
        if col_type and col_type not in MoldSchema.basic_types + self.schema_obj.enum_types:
            attr = "-".join([col_type, attr])
        res = self.crude_answer.get(attr, [])
        limit_of_crude_elts = config.get_config("web.limit_of_crude_elts")  # 读取预测元素块的个数
        if limit_of_crude_elts:
            res = res[:limit_of_crude_elts]
        return res

    def cell_ordering(self, tbl):
        def weight(row_and_col):
            row, col = row_and_col.split("_")
            return int(row) * 10000 + int(col)

        cells = OrderedDict()
        for k, v in sorted(tbl.get("cells").items(), key=lambda x: weight(x[0])):
            cells.setdefault(k, v)
        return cells

    def _next_cell(self, cell_idx, tbl):
        row, col = map(int, cell_idx.split("_"))
        return tbl["cells"].get("_".join(map(str, [row, col + 1])))

    def simple_tbl(self, tbl, regs, **kwargs):
        """
        处理关键词同cell或下一个cell为结果的情况
            1. 关键词下一个cell为结果，比如：发行人名称|a公司
            2. 同cell, 比如: "持股数量（万股）"中"持股数量"为关键词, "万股"为期望结果, 正则可写为r'持股数量(.*?股)?'
        """
        items = []
        cells = self.cell_ordering(tbl)
        cell_matched = OrderedDict()
        for cell_idx, cell in cells.items():
            for reg in regs:
                matched = reg.search(clean_txt(cell["text"]))
                if matched:
                    cell_matched.setdefault(cell_idx, matched)
            # 匹配到一次即返回, 不再处理剩余单元格
            if kwargs.get("oneshot") and cell_matched:
                break

        for cell_idx, matched in cell_matched.items():
            tkeys = sorted([tkey for tkey in matched.re.groupindex.keys() if tkey.startswith("dst")])
            if not tkeys:  # 提取下个cell
                next_cell = self._next_cell(cell_idx, tbl)
                if next_cell and not next_cell.get("dummy"):
                    items.append(next_cell["chars"])
            else:  # 锚定词与关键字在同一单元格，分组命名为dst
                cell = cells[cell_idx]
                chars = []
                for key in tkeys:
                    gr_idx = matched.re.groupindex[key]
                    if -1 not in matched.regs[gr_idx]:
                        sp_start, sp_end = index_in_space_string(cell["text"], matched.span(key))
                        chars.extend(cell["chars"][sp_start:sp_end])
                items.append(chars)
        return items

    def simple_para(self, para, regs, **kwargs):
        """
        按句式提取段落的一部分作为结果
        """
        items = []
        para = self.reader.fix_continued_para(para)  # 修复跨页段落
        if not regs and regs is not None:  # 空数组表示提取整个段落
            items.append(para["chars"])
            return items
        for reg in regs:
            matched = reg.search(clean_txt(para["text"]))
            chars = []
            if matched:
                tkeys = sorted([tkey for tkey in matched.re.groupindex.keys() if tkey.startswith("dst")])
                for key in tkeys:
                    gr_idx = matched.re.groupindex[key]
                    if -1 not in matched.regs[gr_idx]:
                        sp_start, sp_end = index_in_space_string(para["text"], matched.span(key))
                        chars.extend(para["chars"][sp_start:sp_end])
            if chars:
                items.append(chars)
                break
        return items

    def col_group_in_tbl(self, tbl, options):
        """
        二级属性
        财务表格中一列数据作为一组答案的情况
        """
        res = []
        for sub_attr in options:
            sub_attr["row"] = None
        _, cells_by_col = group_cells(tbl["cells"])
        for col in sorted(cells_by_col, key=int):  # 从左到右
            group = {}
            cells = cells_by_col.get(str(col))
            for row in sorted(cells, key=int):  # 从上到下
                cell = cells.get(str(row))
                if col == "0":  # 第一列决定子属性出现在哪一行
                    for sub_attr in options:
                        if not sub_attr["row"] and any(reg.search(clean_txt(cell["text"])) for reg in sub_attr["regs"]):
                            # print('****', col, row, sub_attr['name'], clean_txt(cell['text']))
                            sub_attr["row"] = row
                else:  # 标注其余列
                    for sub_attr in options:
                        # print(sub_attr['name'], sub_attr['row'], row == sub_attr['row'])
                        if sub_attr["row"] is not None and row == sub_attr["row"]:
                            # print('****', col, row, sub_attr['name'], clean_txt(cell['text']))
                            res_obj = ResultOfPredictor([CharResult(cell["chars"])])
                            group.setdefault(sub_attr["name"], res_obj)
            if group:
                res.append(group)
        return res

    def iter_rows(self, tbl, options, row_hanlder, pass_regs=None):
        """
        迭代表格每一行，区分表头/mid_row/数据行
        """

        tbl_info = TblInfo(tbl, self.reader)
        res = []

        def b_middle_row(cells, tbl_info):
            chars = []
            cells = [
                cell
                for cell in cells.values()
                if not cell.get("dummy") and clean_txt(cell["text"]) and clean_txt(cell["text"]) != "序号"
            ]
            if len(cells) == 1 and DATE_PATTERN.search(clean_txt(cells[0]["text"])):
                chars = cells[0]["chars"]
            if chars:
                tbl_info.meta["time"] = {"text": "".join([x["text"] for x in chars]), "chars": chars}
                return True

        cells_by_row, cells_by_col = group_cells(tbl["cells"])
        for row in sorted(cells_by_row, key=int):  # 从上到下
            cells = cells_by_row.get(row)
            # mid_row
            if b_middle_row(cells, tbl_info):
                continue
            for cell in cells.values():
                if any(reg.search(clean_txt(cell["text"])) for reg in options[0]["regs"]):
                    tbl_info.header_rows.add(int(row))
            # print(row, tbl_info.header_rows, tbl_info.meta.get('time', {}).get('text'))
            # col_head决定子属性出现在哪一列
            if int(row) in tbl_info.header_rows:
                # print('-----', row, {k: v['text'] for k, v in cells.items()})
                for col, cell in cells.items():
                    for sub_attr in options:
                        if not sub_attr.get("col") and any(
                            reg.search(clean_txt(cell["text"])) for reg in sub_attr["regs"]
                        ):
                            # print('*********', row, col, sub_attr['name'], clean_txt(cell['text']))
                            sub_attr["col"] = col
                continue
            # 需要跳过的行
            if pass_regs:
                if any(any(reg.search(clean_txt(cell["text"])) for reg in pass_regs) for cell in cells.values()):
                    continue
            # 提取数据
            item = row_hanlder(row, cells, options, tbl_info)
            if item:
                res.append(item)
        return res


class ConvertPredictor(AnswerPredictor):
    """
    有答案schema转换方法的预测类
    """

    def __init__(self, *args, **kwargs):
        super(ConvertPredictor, self).__init__(*args, **kwargs)
        self.export_answer = None

    def predict_from_convert_answer(self):
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
                if not res_obj:
                    continue
                func_name = "_".join(["build", res_obj.elt_typ])
                if hasattr(self, func_name):
                    func = getattr(self, func_name)
                    res = func(res_obj)
                    if res_obj.elt_typ == "label":
                        items.extend(res)
                    else:
                        items.append(res)
            return items

        def build_col(schema_info, path):
            schema = build_schema(schema_info)

            col = {
                "schema": schema,
                "score": -1,
                "data": [],
                "key": "[%s]" % ",".join(['"%s:%s"' % (key, idx) for key, idx in path]),
                # 'key': json.dumps(['%s:%s' % (key, idx) for key, idx in path]),
            }
            return col

        def build_result(schema, result, path):
            cols = []
            for col_name in schema["orders"]:
                col_attributes = deepcopy(schema["schema"][col_name])
                col_attributes.update({"name": col_name})
                col_res = result.get(col_name, [])
                if not col_res:
                    continue
                for idx, item in enumerate(col_res if isinstance(col_res, list) else [col_res]):
                    col_path = path + [(col_name, idx)]
                    col = build_col(col_attributes, col_path)
                    if col_attributes["type"] in MoldSchema.basic_types:  # 基本类型
                        item = revise_result_node(item)
                        if item.data:
                            col["data"] = build_col_data(col_attributes, item.data)
                            col["score"] = item.score
                            if len(item.data) == 1 and item.data[0] and item.data[0].text:
                                col["text"] = item.data[0].text
                            cols.append(col)
                    elif col_attributes["type"] in self.schema_type_dict:  # 枚举
                        item = revise_result_node(item)
                        if item and item.data is not None:
                            col["data"] = build_col_data(col_attributes, item.data)
                            col["value"] = item.value
                            col["score"] = item.score
                            if len(item.data) == 1 and item.data[0].text:
                                col["text"] = item.data[0].text
                            cols.append(col)
                    elif col_attributes["type"] in self.schema_dict:  # 子类型
                        sub_schema = self.schema_dict[col_attributes["type"]]
                        cols.extend(build_result(sub_schema, item, col_path))
            return cols

        return build_result(self.schema_dict[self.root_schema_name], self.export_answer, [(self.root_schema_name, 0)])

    def predict_from_crude_answer(self):
        cols = []
        return cols

    def analysis_v_2_2(self):
        func = self.predict_from_convert_answer if self.export_answer else self.predict_from_crude_answer
        res = func()
        return res


class TblInfo:
    def __init__(self, tbl, reader):
        self.tbl = tbl
        self.reader = reader
        self.meta = {}
        self.get_tbl_time()
        self.header_rows = {0}
        self.set_header_row()

    def get_tbl_time(self):
        prev_elts = self.reader.find_elements_near_by(self.tbl["index"], step=-1, amount=3)
        for elt in prev_elts:
            if elt["class"] == "PARAGRAPH":
                matched = DATE_PATTERN.search(clean_txt(elt["text"]))
                if matched:
                    sp_start, sp_end = index_in_space_string(elt["text"], matched.span(0))
                    chars = elt["chars"][sp_start:sp_end]
                    self.meta["time"] = {"text": "".join([x["text"] for x in chars]), "chars": chars}

    def set_header_row(self):
        merged = self.tbl["merged"]
        # print(merged)
        for merged_group in merged:
            if [0, 0] in merged_group:
                pass


class LabelResult:
    __slots__ = ["elt_typ", "items", "text", "confirm", "elt"]

    def __init__(self, items, text=None, confirm=False, elt=None):
        self.elt_typ = "label"
        self.items = items
        self.text = text
        self.confirm = confirm
        self.elt = elt


class OutlineResult:
    __slots__ = ["elt_typ", "page", "outline", "text", "confirm", "elt"]

    def __init__(self, page, outline, text="", confirm=False, elt=None):
        self.elt_typ = "outline"
        self.page = page
        self.outline = outline
        self.text = text or ""
        self.confirm = confirm
        self.elt = elt


class CharResult:
    __slots__ = ["elt_typ", "chars", "text", "confirm", "elt_idx", "elt"]

    def __init__(self, chars, text=None, confirm=False, elt_idx=-1, elt=None):
        self.elt_typ = "char"
        self.chars = chars
        self.text = text
        self.elt = elt
        self.confirm = confirm
        self.elt_idx = elt_idx


class ParaResult:
    __slots__ = ["elt_typ", "chars", "elt", "confirm", "text"]

    def __init__(self, chars, elt, text=None, confirm=False):
        self.elt_typ = "paragraph"
        self.chars = chars
        self.elt = elt
        self.confirm = confirm
        self.text = text


class TblResult:
    __slots__ = ["elt_typ", "cells", "elt", "confirm", "text"]

    def __init__(self, cells, elt, confirm=False, text=None):
        self.elt_typ = "table"
        self.cells = cells
        self.elt = elt
        self.confirm = confirm
        self.text = text


class TblCellsResult(object):
    __slots__ = ["elt_typ", "cells", "elt", "text", "confirm"]

    def __init__(self, cells, elt, confirm=False, text=None):
        self.elt_typ = "table_cells"
        self.cells = cells
        self.elt = elt
        self.confirm = confirm
        self.text = text


def build_element_result(element, ignore_cells=True):
    if element["class"] in ["PARAGRAPH", "PAGE_FOOTER", "PAGE_HEADER", "FOOTNOTE"]:
        return ParaResult(element["chars"], element)
    elif element["class"] == "TABLE":
        cells = None if ignore_cells else element["cells"]
        return TblResult(cells, element)
    else:
        raise RuntimeError(f"Not supported element class: {element['class']}")


class ResultOfPredictor(object):
    __slots__ = ["data", "value", "score", "crude_elts"]

    def __init__(self, data, value=None, crude_elts=None, score=None):
        self.data = data
        # self.score = round(crude_elts[0]['score'], 4) if crude_elts else -1
        self.crude_elts = crude_elts or []
        self.score = self.confidence_score(score)
        self.value = value

    def confidence_score(self, score):
        score = score
        if score is None:
            element_result = next((i for i in self.data), None)
            element = getattr(element_result, "elt", {})
            if element:
                score = element.get("score")
        if score is None:
            crude_elt = next((i for i in self.crude_elts), {})
            score = crude_elt.get("score", -1)
        return "%.2f" % float(score)


class RegroupPredictor(AnswerPredictor):
    def __init__(self, *args, **kwargs):
        super(RegroupPredictor, self).__init__(*args, **kwargs)
        self.column_analyzers.update(
            {
                "证券代码": functools.partial(self._pdf_first_line, "证券代码"),
                "公司名称": functools.partial(self._pdf_first_line, "公司名称"),
                "披露前上市公司最近一年资产总额": self.recent_total_assets,
                "股份对价支付金额": self.price_of_paid_shares,
                "股份对价支付数量": self.amount_of_paid_shares,
                "交易或资产金额占比": self.asset_ratio,
                "交易对方对价情况": self.consideration,
                "收购标的情况": self.get_target_info,
                "方案简介": self.scheme_intro,
                "配套融资金额": functools.partial(self._aim_mixin, "配套融资金额"),  # part
                "股票定价方式": functools.partial(self._aim_para, "股票定价方式"),  # part
                "交易金额": functools.partial(self._aim_table_fix, "交易金额"),
                "现金支付金额": functools.partial(self._aim_mixin, "现金支付金额"),
            }
        )
        self.targets = set()
        self.current_target = None
        self.target_maps = {}  # 标的-属性
        self.ignore_l = ["下属", "上市", "子公司", "参股", "控股"]
        if self.options.get("reader"):
            self.reader = self.options.get("reader")
        # 调试用于测试单个属性及准确率
        if self.options.get("attr"):
            self.column_analyzers = {self.options.get("attr"): self.column_analyzers.get(self.options.get("attr"))}

    def get_crude_elements(self, attr, **kwargs):
        col_type = kwargs.get("col_type", "")
        if col_type not in MoldSchema.basic_types:
            attr = "-".join([col_type, attr])
        limit_of_crude_elts = config.get_config("web.limit_of_crude_elts", 5)  # 读取预测元素块的个数
        return self.crude_answer.get(attr, [])[:limit_of_crude_elts]

    def b_target_illegal(self, target_name):
        clean_pattern = re.compile(
            r"(标的|[置注][出入]|被?评估)|(资产|公司|单位)|([合总]计|合并|备考|简要|实际|模拟|假设|简表)|"
            r"((最近)?.年及?.期)|([(（]?[一二三四五六七八九十\d]+[)）.,:、，：]+)"
            r"|(母公司)|(\s+)|的|报告期内?|交易标|\d+"
        )
        clean_target_name = clean_pattern.sub("", clean_txt(target_name))
        if not clean_target_name:
            return True

    def get_purchase_targets(self, **kwargs):
        """
        收购标的
        句式：向/购买/收购……持有的【交易标的】
        交易标的内容构成（通常情况下，存在例外）：公司简称+百分比+“股权”
        示例：唯一网络100.00%股权
        """
        attr = "收购标的"
        intro_target_pattern = re.compile(
            r"(?:(?:通过|以).*?方式)?"
            r"(?:向.*?(?:非?公开发行股[份权票]))?"
            r"(?:购买|收购|置入|采购|[获取]得|对价受让|标的(?:公司|资产)?[为是]?|[及和与、](?!(?:支付|发行)))的?"
            r"(?:(?:[^。；、]*?)?其?所?(?:合计)?持有?的?)?\s*"
            r"(?:(?:.*?)评估的)?"
            r"(?:(?:标的)?(?:公司|资产)?[为是]?)?"
            r"(([^，。、；]{2,20}?)(?:（.*）)?的?(?:[合总]计)?的?\s*(?:[\d,]+(?:\.\d*)?%?\s*(?:的?\s*(?:股(?:普通股)?)?股[权份])"
            r"|(?:全部)?股[权份]中?的\s*[\d,]+(?:\.\d*)?%))"
        )

        def target_existed(tar):
            """
            判断标的是否已经标记过
            """
            for existed_target in self.targets:
                if (clean_txt(tar) in existed_target) or (existed_target in clean_txt(tar)):
                    return True

        def get_target_from_confirmed_answer(item):
            _res = []
            for data in item["data"]:
                element, chars = None, []
                for box in data["boxes"]:
                    _element, _chars = self.reader.find_chars_by_outline(
                        box["page"],
                        (
                            box["box"]["box_left"],
                            box["box"]["box_top"],
                            box["box"]["box_right"],
                            box["box"]["box_bottom"],
                        ),
                    )
                    element = _element if element is None else element
                    if _element and element["index"] == _element["index"]:
                        chars.extend(_chars)
                if not element:
                    continue
                label = "".join([c["text"] for c in chars])
                target_name = get_target_name_from_text(label)
                if not label:
                    continue
                logging.info("found taget from confirmed answer: %s(%s)", label, target_name)
                _res.append((label, chars, element, target_name, True))
            return _res

        def get_target_name_from_text(text):
            text = re.split(r"[\d\.]+%", text)[0]
            search_simply_name = re.search(r"简称\s?[“\"](.*)[”\"]", text)
            if search_simply_name:
                text = search_simply_name.group(1)
            return clean_txt(text)

        res = []
        if self.confirmed_answer and float(self.answer_version) >= 2.0:
            for item in self.confirmed_answer.get("userAnswer", {}).get("items", []):
                key_path = load_key_path(item["key"])
                if key_path[-1].name == attr and item.get("confirm"):
                    res.extend(get_target_from_confirmed_answer(item))
            if res:
                return res

        elts = self.get_crude_elements(attr, **kwargs)

        # 从方案简介中提取标的
        for _idx, element in enumerate(elts):
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "PARAGRAPH":
                # print('--------', self.file.id, idx, 'para', element['page'], element['text'])
                for item in intro_target_pattern.finditer(element["text"]):
                    label, target_name = item.groups()
                    target_name = clean_txt(target_name)
                    # print('======', label, target_name, reg.search(target_name), self.targets)
                    if not self.b_target_illegal(target_name) and not target_existed(target_name):  # 非法标的
                        self.targets.add(target_name)
                        chars = element["chars"][item.start(1) : item.end(1)]
                        # print('******', label, [x['text'] for x in chars])
                        res.append((label, chars, element, target_name, False))
                if res:
                    break

        # 从"财务会计信息"章节中补充
        def find_fin_syllabus():
            syl_dict = self.reader.syllabus_dict
            syl_1 = []
            pattern = re.compile(r"财务会计信息")
            # print('in find_fin_syllabus')
            # syll1_l = {k: v['title'] for k, v in syl_dict.items() if v['level'] <= 1}
            # print(len(syll1_l), syll1_l)
            for _, syl in sorted(syl_dict.items(), key=lambda x: x[0]):
                if syl["level"] <= 1 and pattern.search(clean_txt(syl["title"])) is not None:
                    # print('syl_1', syl)
                    syl_1.append(syl)
            if syl_1 is None:
                return []

            def match_syl(syl, matched):
                for child in [syl_dict.get(idx) for idx in syl.get("children", [])]:
                    if (
                        not any(x in clean_txt(child["title"]) for x in self.ignore_l) and child["level"] <= 4
                    ):  # 过滤下属企业
                        matched.append(child)
                        match_syl(child, matched)

            matches = []
            for syl in syl_1:
                match_syl(syl, matches)
            return matches

        syll_target_pattern = re.compile(
            r"(?:[(（]?[一二三四五六七八九十\d]+[)）.,:、，：\s]+)?"
            r"(?:本次)?(?:最[终后])?(?:(?:标的|拟?购买)(?:公司|资产))?的?(?:母公司)?"
            r"(?P<target>.*?)的?"
            r"(?:(?:最近).年(?:及一期)?|报告期内?)?的?(?:经审计的?)?(?:资产)?"
            r"(?:财务会计信息|(?:简要)?(?:备考|实际)?(?:模拟)?(?:合并)?(资产负债表|现金流量表|利润表|财务报表))"
        )
        sylls = find_fin_syllabus()
        for syll in sylls:
            if not any(neg in clean_txt(syll["title"]) for neg in self.ignore_l) and syll_target_pattern.search(
                clean_txt(syll["title"])
            ):
                typ, elt = self.reader.find_element_by_index(syll["range"][0])
                if typ == "PARAGRAPH":
                    # print('--------', self.file.id, elt['index'], elt['page'], elt['text'])
                    label = self._simple_label(syll_target_pattern, elt)
                    target_name = clean_txt(label)
                    if label and not self.b_target_illegal(target_name) and not target_existed(target_name):  # 非法标的
                        self.targets.add(target_name)
                        label_start = elt["text"].find(label)
                        chars = elt["chars"][label_start : label_start + len(label)]
                        # print('******', label, [x['text'] for x in chars])
                        res.append((label, chars, elt, target_name, False))
        # print('~~~~~~', self.targets)
        return res

    def get_elt_targets(self, elt, targets):
        """
        从上下文或大纲中找元素块对应的标的
        """
        # 查看上下文
        scope, res = [], {}
        if elt["class"] == "TABLE":  # 表格（本身+上面三个段落）
            scope.append(get_tbl_text(elt))
            for idx in range(elt["index"] - 1, 0, -1):
                ele_typ, ele = self.reader.find_element_by_index(idx)
                if ele_typ == "PARAGRAPH":
                    scope.append(ele["text"])
                if len(scope) >= 4:
                    break
        elif elt["class"] == "PARAGRAPH":  # 段落（本身）
            scope.append(elt["text"])
        if any(any(x in item for x in self.ignore_l) for item in scope):  #
            return {}
        for item in scope:
            for target_name in targets:
                if (target_name in clean_txt(item)) or (len(targets) == 1 and "标的" in clean_txt(item)):
                    res.setdefault(target_name, scope)
        if res:
            return res
        # 查看该元素所在大纲中的标的
        sylls = self.reader.find_syllabuses_by_index(elt["index"])
        if any(any(x in clean_txt(syll["title"]) for x in self.ignore_l) for syll in sylls):
            return {}
        for syll in sylls:
            for target_name in targets:
                if (target_name in clean_txt(syll["title"])) or (
                    len(targets) == 1 and "标的" in clean_txt(syll["title"])
                ):
                    res.setdefault(target_name, []).append(clean_txt(syll["title"]))
        return res

    def fill_target_info_pool(self, attr, target_info_pool, elt, target_maps, **kwargs):
        elt_targets = self.get_elt_targets(elt, target_maps)  # 当前元素块对应的标的
        ele_typ = elt["class"]
        chars, aim_cell_l = kwargs.get("chars", []), kwargs.get("aim_cell", [])
        # print('~~~~~~ elt_targets', attr, elt_targets)

        if elt_targets:
            for target_name in target_maps:
                if target_name in elt_targets:
                    # print('************' * 2, target_name, label, [x['text'] for x in chars], aim_cell_l)
                    if ele_typ == "PARAGRAPH":
                        target_info_pool.setdefault(target_name, []).append((chars, elt))
                    elif ele_typ == "TABLE":
                        flag = False
                        if attr in FinancialAttribute.TARGET_ATTRS:  # 财务属性优先取三大表的数据
                            for text in elt_targets[target_name]:
                                if str.endswith(text, ("资产负债表", "现金流量表", "利润表")) and not any(
                                    neg in text for neg in ("简要", "简表", "模拟", "假设")
                                ):
                                    flag = True
                        if flag:
                            target_info_pool.setdefault(target_name, []).insert(0, (aim_cell_l, elt))
                        else:
                            target_info_pool.setdefault(target_name, []).append((aim_cell_l, elt))
        else:  # 没找到对应标的
            # print('************' * 2, DEFAULT_POOL_KEY, label, [x['text'] for x in chars], aim_cell_l)
            if ele_typ == "PARAGRAPH":
                target_info_pool.setdefault(DEFAULT_POOL_KEY, []).append((chars, elt))
            elif ele_typ == "TABLE":
                target_info_pool.setdefault(DEFAULT_POOL_KEY, []).append((aim_cell_l, elt))

    def target_book_value(self, attr, target_maps, **kwargs):
        """
        账面净资产
        表格中数据
        关键字：净资产、资产净额、资产净值、所有者权益
        时间：三年一期中的最近一期，或者三年中最近的一年
        """
        patterns = [
            re.compile(r"归属于?母公司(所有者|股东)?的?(净资产|资产净[额值]|(所有者|股东)?权益(总额|合计)?)"),
            re.compile(r"净资产|资产净[额值]|(所有者|股东)权益(总额|合计)?"),
        ]
        elts = self.get_crude_elements(attr, **kwargs)
        target_info_pool = {DEFAULT_POOL_KEY: []}  # 存放每个标的对应的该属性
        for _idx, element in enumerate(elts):
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "TABLE":
                cells_by_row, cells_by_col = group_cells(element["cells"])
                aim_cell, anchor_cell_l = None, []
                for pattern in patterns:
                    anchor_cell = self._locate_cell_from_tbl_header(element, pattern)  # 属性所在cell
                    if anchor_cell and anchor_cell not in anchor_cell_l:
                        anchor_cell_l.append(anchor_cell)
                # print('--------', attr, idx, 'tbl', element['page'], element['title'], anchor_cell_l)
                select_cells = []
                for anchor_cell in anchor_cell_l:
                    aim_row, aim_col = anchor_cell.split("_")
                    # print('*******', anchor_cell, self._get_cell_text(element, aim_row, aim_col))
                    if aim_row != "0":  # 属性在第一列， 时间在第一行
                        recent_year, recent_period = self.recent_year_period(cells_by_row.get("0", {}))
                        aim_col = recent_year if recent_period is None else recent_period
                    else:  # 属性在第一行， 时间在第一列
                        recent_year, recent_period = self.recent_year_period(cells_by_col.get("0", {}))
                        aim_row = recent_year if recent_period is None else recent_period
                    if aim_row is not None and aim_col is not None:
                        aim_cell = "_".join(map(str, [aim_row, aim_col]))
                    # print('*******', aim_cell, self._get_cell_text(element, aim_row, aim_col))
                    if aim_cell and element["cells"].get(aim_cell) and (aim_cell not in select_cells):
                        select_cells.append(aim_cell)
                mem_cells = []
                memory_path = os.path.join(memory_dir, "%s.json" % attr)
                if (config.get_config("web.predict_from_memory.switch")) and os.path.exists(memory_path):
                    mem_cells = TableUtil.cell_in_memory(element, json.load(open(memory_path)), existed=select_cells)
                select_cells.extend([_[0] for _ in Counter(mem_cells).most_common()])
                for select_cell in select_cells:
                    self.fill_target_info_pool(attr, target_info_pool, element, target_maps, aim_cell=[select_cell])
        return target_info_pool

    def recent_year_profit(self, attr, target_maps, **kwargs):
        """
        标的公司三大财务报表的最近一年的净利润
        表格中数据
        关键字：归属于母公司净利润 > 净利润
        时间：三年一期中的最近一年，或者三年中最近的一年
        """
        patterns = [re.compile(r"^(归属于?母公司(股东|所有者)?的?)净利润"), re.compile(r"^净利润")]
        elts = self.get_crude_elements(attr, **kwargs)
        target_info_pool = {DEFAULT_POOL_KEY: []}  # 存放每个标的对应的该属性
        for _idx, element in enumerate(elts):
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "TABLE":
                cells_by_row, cells_by_col = group_cells(element["cells"])
                aim_cell, anchor_cell_l = None, []
                for pattern in patterns:
                    anchor_cell = self._locate_cell_from_tbl_header(element, pattern)  # 属性所在cell
                    if anchor_cell and anchor_cell not in anchor_cell_l:
                        anchor_cell_l.append(anchor_cell)
                # print('--------', attr, idx, 'tbl', element['page'], element['title'], anchor_cell_l)
                # print({x: y['text'] for x, y in cells_by_row.get('0', {}).items()})
                select_cells = []
                for anchor_cell in anchor_cell_l:
                    aim_row, aim_col = anchor_cell.split("_")
                    # print('*******', anchor_cell, self._get_cell_text(element, aim_row, aim_col))
                    if aim_row != "0":  # 属性在第一列， 时间在第一行
                        aim_col, _ = self.recent_year_period(cells_by_row.get("0", {}))
                    else:  # 属性在第一行， 时间在第一列
                        aim_row, _ = self.recent_year_period(cells_by_col.get("0", {}))
                    if aim_row is not None and aim_col is not None:
                        aim_cell = "_".join(map(str, [aim_row, aim_col]))
                    # print('*******', aim_cell, self._get_cell_text(element, aim_row, aim_col))
                    if aim_cell and element["cells"].get(aim_cell) and (aim_cell not in select_cells):
                        select_cells.append(aim_cell)
                mem_cells = []
                memory_path = os.path.join(memory_dir, "%s.json" % attr)
                if (config.get_config("web.predict_from_memory.switch")) and os.path.exists(memory_path):
                    mem_cells = TableUtil.cell_in_memory(element, json.load(open(memory_path)), existed=select_cells)
                select_cells.extend([_[0] for _ in Counter(mem_cells).most_common()])
                for select_cell in select_cells:
                    self.fill_target_info_pool(attr, target_info_pool, element, target_maps, aim_cell=[select_cell])
        return target_info_pool

    def target_financial_fields(self, attr, target_maps, fattr, **kwargs):
        """
        财务属性
        """
        elts = self.get_crude_elements(attr, **kwargs)
        target_info_pool = {DEFAULT_POOL_KEY: []}  # 存放每个标的对应的该属性
        # if attr not in ['流动资产合计']:  # 测试单个属性
        #     return target_info_pool
        for _idx, element in enumerate(elts):
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "TABLE":
                # print('--------', attr, '%s/%s' % (idx, len(elts)), 'tbl', element['index'], element['page'],
                #       element['title'])
                cells_by_row, cells_by_col = group_cells(element["cells"])
                table_attrs = fattr.table_attrs(
                    element, overdrive=kwargs.get("overdrive"), cleansum=kwargs.get("cleansum")
                )
                # print('********* rows', table_attrs.get(attr, []), table_attrs)
                for row in table_attrs.get(attr, []):
                    row_cells = []
                    cells = cells_by_row.get(str(row), {})
                    for col in sorted(map(int, cells.keys())):
                        row_cells.append("_".join(map(str, [row, col])))
                    self.fill_target_info_pool(attr, target_info_pool, element, target_maps, aim_cell=row_cells)
        return target_info_pool

    def target_busi(self, attr, target_maps, **kwargs):
        """
        标的行业
        段落数据
        句式：
        大象股份所从事业务属于“租赁和商业服务业（L）”中的“（72）商务服务业”。
        盾安新能源所属行业为“D 电力、热力、燃气及水生产和供应业”之“D44 电力、热力生产和供应业”。
        """
        elts = self.get_crude_elements(attr, **kwargs)
        target_info_pool = {DEFAULT_POOL_KEY: []}  # 存放每个标的对应的该属性
        pattern = re.compile(r"(所(在|属|处|从事)(.*?)?(行业|业务)(为|是|属于)|属[为于])(?P<target>.*?)[，。；]")
        for _idx, element in enumerate(elts):
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "PARAGRAPH":
                # print('--------', attr, '%s/%s' % (idx, len(elts)), 'para', element['page'], element['text'])
                for item in pattern.finditer(element["text"]):
                    label = item.group()
                    chars = element["chars"][item.start() : item.end()]
                    # print('*******', label)
                    self.fill_target_info_pool(attr, target_info_pool, element, target_maps, label=label, chars=chars)
        return target_info_pool

    def target_prof(self, attr, target_maps, **kwargs):
        """
        标的业务
        段落数据
        句式：盾安新能源的主营业务为风力发电、光伏发电的项目投资、建设及运营。
        大象股份作为国内前列的户外广告媒体资源运营公司，专注于公共交通系统广告媒体资源运营
        """
        pattern = re.compile(r"(主营|业务[为是]|专注于?|从事)(?P<target>.*?)[，。；]")
        elts = self.get_crude_elements(attr, **kwargs)
        target_info_pool = {DEFAULT_POOL_KEY: []}  # 存放每个标的对应的该属性值
        for _idx, element in enumerate(elts):
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "PARAGRAPH":
                # print('--------', attr, '%s/%s' % (idx, len(elts)), 'para', element['page'], element['text'])
                label = self._simple_label(pattern, element)
                if label:
                    label_start = element["text"].find(label)
                    chars = element["chars"][label_start : label_start + len(label)]
                    # print(print('********', label, [x['text'] for x in chars]))
                    self.fill_target_info_pool(attr, target_info_pool, element, target_maps, label=label, chars=chars)
        return target_info_pool

    def get_eval_method(self, attr, target_maps, **kwargs):
        """
        评估方法
        """
        pattern = re.compile(r"(资产基础法|收益法)")
        elts = self.get_crude_elements(attr, **kwargs)
        target_info_pool = {DEFAULT_POOL_KEY: []}  # 存放每个标的对应的该属性值
        for _idx, element in enumerate(elts):
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "PARAGRAPH":
                # print('--------', attr, '%s/%s' % (idx, len(elts)), 'para', element['page'], element['text'])
                vals = pattern.findall(element["text"])
                if vals:
                    label = vals[-1]
                    label_start = element["text"].find(label)
                    chars = element["chars"][label_start : label_start + len(label)]
                    # print('********', label, [x['text'] for x in chars])
                    self.fill_target_info_pool(attr, target_info_pool, element, target_maps, label=label, chars=chars)
        return target_info_pool

    def get_asset_valuation(self, attr, target_maps, target_eval_method, **kwargs):
        """
        资产评估值
        key：评估价值、估值、评估值、预估值、评估基准日的价值
        如果同时找到好几个，那么取附近关键字存在相应评估方法的那个值
        句式：盾安新能源股东全部权益价值的评估值为200，000万元。
        规则不完善，可以考虑增加规则：连续的几个自然段，出现3个溢价率时，选取单独在一个自然段那个（确认的语句可能在前面，也可能在后面）
        todo: 根据"评估方法+标的"确定资产评估值
        """
        patterns = [
            re.compile(
                r"(?:[评预]?估(?:基准日)?的?(?:结果|价?值|作价)?(?:（.*）)?"
                r"(?:合计)?约?[为是]?|[和与])(?:人民币|美元)?\s*(\d[\d,，]*(?:\.\d*)?\s*[万亿]?(?:美?元|英镑))"
            ),
            re.compile(
                r"(?:(?:股东|所有者)?(?:全部)?权益|净资产|股权)(?:（.*）)?(?:账面)?(?:结果|价?值|作价)?(?:（.*）)?"
                r"(?:合计)?(?:金额)?约?[为是]?(?:人民币|美元)?\s*(\d[\d,，]*(?:\.\d*)?\s*[万亿]?(?:美?元|英镑))"
            ),
        ]
        elts = self.get_crude_elements(attr, **kwargs)
        target_info_pool = {DEFAULT_POOL_KEY: []}  # 存放每个标的对应的该属性值

        for _idx, element in enumerate(elts):
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "PARAGRAPH":
                # print('--------', attr, '%s/%s' % (idx, len(elts)), 'para', element['page'], element['text'])
                vals = {}
                for pattern in patterns:
                    for val in pattern.finditer(element["text"]):
                        vals.setdefault(val.span(), val)
                for val in vals.values():
                    label = val.group(1)
                    chars = element["chars"][val.start(1) : val.end(1)]
                    # print('********', label, [x['text'] for x in chars])
                    self.fill_target_info_pool(attr, target_info_pool, element, target_maps, label=label, chars=chars)
            elif ele_typ == "TABLE":
                # print('--------', attr, '%s/%s' % (idx, len(elts)), 'tbl', element['page'], element['title'])
                cells_by_row, cells_by_col = group_cells(element["cells"])
                select_cells = []
                for col, cells in cells_by_col.items():
                    flag = False
                    for row in sorted(map(int, cells.keys())):
                        cell_idx = "_".join(map(str, [row, col]))
                        cell = element["cells"][cell_idx]
                        if clean_txt(cell["text"]) and re.search(r"[评预]?估(价?值|结果)", clean_txt(cell["text"])):
                            flag = True
                        if flag and clean_txt(cell["text"]) and TableUtil.is_num(clean_txt(cell["text"])):
                            # print('****', cell_idx, clean_txt(cell['text']))
                            select_cells.append(cell_idx)
                mem_cells = []
                memory_path = os.path.join(memory_dir, "%s.json" % attr)
                if (config.get_config("web.predict_from_memory.switch")) and os.path.exists(memory_path):
                    mem_cells = TableUtil.cell_in_memory(element, json.load(open(memory_path)), existed=select_cells)
                select_cells.extend([_[0] for _ in Counter(mem_cells).most_common()])
                for select_cell in select_cells:
                    self.fill_target_info_pool(attr, target_info_pool, element, target_maps, aim_cell=[select_cell])
        return target_info_pool

    def get_premium_rate(self, attr, target_maps, target_eval_method, **kwargs):
        """
        溢价率
        key：溢价率，增值率
        如果同时找到好几个，那么取附近关键字存在相应评估方法的那个值
        todo: 根据"评估方法+标的"确定资产溢价率
        """
        # print('target_eval_method', target_eval_method)
        elts = self.get_crude_elements(attr, **kwargs)
        target_info_pool = {DEFAULT_POOL_KEY: []}  # 存放每个标的对应的该属性值
        pattern = re.compile(r"(?:增值率|溢价率)约?[为是]?\s*(\d[\d,]*(?:\.\d*)?\s*%)")
        for _idx, element in enumerate(elts):
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "PARAGRAPH":
                # print('--------', attr, '%s/%s' % (idx, len(elts)), 'para', element['page'], element['text'])
                vals = {}
                for val in pattern.finditer(element["text"]):
                    vals.setdefault(val.span(), val)
                for val in vals.values():
                    label = val.group(1)
                    chars = element["chars"][val.start(1) : val.end(1)]
                    # print('********', label, [x['text'] for x in chars])
                    self.fill_target_info_pool(attr, target_info_pool, element, target_maps, label=label, chars=chars)
            elif ele_typ == "TABLE":
                # print('--------', attr, '%s/%s' % (idx, len(elts)), 'tbl', element['page'],
                #       element['title'])
                cells_by_row, cells_by_col = group_cells(element["cells"])
                select_cells = []
                for col, cells in cells_by_col.items():
                    flag = False
                    for row in sorted(map(int, cells.keys())):
                        cell_idx = "_".join(map(str, [row, col]))
                        cell = element["cells"][cell_idx]
                        if clean_txt(cell["text"]) and re.search(r"(增[值减]率|溢价率)", clean_txt(cell["text"])):
                            flag = True
                        if (
                            flag
                            and clean_txt(cell["text"])
                            and TableUtil.is_num(clean_txt(cell["text"]))
                            and cell_idx not in select_cells
                        ):
                            # print('****', cell_idx, clean_txt(cell['text']))
                            select_cells.append(cell_idx)
                mem_cells = []
                memory_path = os.path.join(memory_dir, "%s.json" % attr)
                if (config.get_config("web.predict_from_memory.switch")) and os.path.exists(memory_path):
                    mem_cells = TableUtil.cell_in_memory(element, json.load(open(memory_path)), existed=select_cells)
                select_cells.extend([_[0] for _ in Counter(mem_cells).most_common()])
                for select_cell in select_cells:
                    self.fill_target_info_pool(attr, target_info_pool, element, target_maps, aim_cell=[select_cell])
        return target_info_pool

    def target_base_info(self, attr, target_maps, **kwargs):
        """
        标的情况基本信息
        形式：表格中的数据
        注册地：注册地/注册地址
        经营场所：住所、经营场所、办公地址
        """
        pattern = PATTERNS.get(attr)
        # print('=========', attr)
        elts = self.get_crude_elements(attr, **kwargs)
        target_info_pool = {DEFAULT_POOL_KEY: []}  # 存放每个标的对应的该属性
        for _idx, element in enumerate(elts):
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "TABLE":
                aim_cell, anchor_cell = None, None
                anchor_cell = self._locate_cell_from_tbl_header(element, pattern)  # 属性所在cell
                # print('--------', attr, idx, 'tbl', element['page'], element['title'], anchor_cell)
                if anchor_cell:
                    aim_row, aim_col = anchor_cell.split("_")
                    # print('*******', anchor_cell, self._get_cell_text(element, aim_row, aim_col))
                    if aim_row:  # 属性在第一列
                        aim_col = 1
                    else:  # 属性在第一行
                        aim_row = 1
                    if aim_row is not None and aim_col is not None:
                        aim_cell = "_".join(map(str, [aim_row, aim_col]))
                    # print('*******', aim_cell, self._get_cell_text(element, aim_row, aim_col))
                    if aim_cell and element["cells"].get(aim_cell):
                        self.fill_target_info_pool(attr, target_info_pool, element, target_maps, aim_cell=[aim_cell])
        return target_info_pool

    def build_secondary_attr(self, attr_name, sub_attr_map):
        items = []
        for sub_fields in sub_attr_map.values():
            fields = []
            for sub_name in self.schema_dict.get(attr_name, {}).get("orders", []):
                if sub_name in sub_fields and sub_fields[sub_name]:
                    fields.append(sub_fields[sub_name])
                else:
                    fields.append(self.empty_field(sub_name))
            items.append({"fields": fields})
        return items

    def find_target_syllabus(self):
        syl_dict = self.reader.syllabus_dict
        syl_1 = []
        pattern = re.compile(r"(?:标的|目标|[置注]入)(?:资产|公司|单位)?的?(?:基本)?(?:情况|概况)?$")
        for _, syl in sorted(syl_dict.items(), key=lambda x: x[0]):
            if syl["level"] <= 1 and pattern.search(clean_txt(syl["title"])) is not None:
                # print('syl_1', syl)
                syl_1.append(syl)

        if syl_1 is None:
            return []

        def match_syl(syl, matched):
            for child in [syl_dict.get(idx) for idx in syl.get("children", [])]:
                if not any(x in clean_txt(child["title"]) for x in self.ignore_l):  # 过滤下属企业
                    matched.append(child)
                    match_syl(child, matched)

        matches = []
        for syl in syl_1:
            match_syl(syl, matches)
        return matches

    def get_target_info(self, **kwargs):
        """
        收购标的情况， 二级属性汇总
        """
        res = []
        targets = self.get_purchase_targets(**kwargs)
        if targets:
            for _label, chars, element, target_name, confirmed in targets:
                self.target_maps.setdefault(target_name, {}).setdefault("收购标的", []).append(
                    (chars, element, confirmed)
                )

            # print('before', self.target_maps.keys())
            # 删掉不合条件的标的
            if not confirmed:
                for tar in self.targets:
                    if (len(self.target_maps) > 1) and (
                        not any(tar in clean_txt(syll["title"]) for syll in self.find_target_syllabus())
                    ):
                        self.target_maps.pop(tar)
            # print('after', self.target_maps.keys())

            pools = {}
            # 财务属性
            fattr = FinancialAttribute(self.reader, target_maps=self.target_maps)
            for fin_attr in fattr.TARGET_ATTRS:
                overdrive, cleansum = True, True
                if fin_attr in ["流动资产合计", "非经常性损益", "净资产", "经营活动现金流量净额", "毛利率"]:
                    cleansum = False
                fin_attr_pool = self.target_financial_fields(
                    fin_attr, self.target_maps, fattr, overdrive=overdrive, cleansum=cleansum, **kwargs
                )
                pools.setdefault(fin_attr, fin_attr_pool)

            # 获得每个标的对应的评估方法
            eval_method_pool = self.get_eval_method("评估方法", self.target_maps, **kwargs)
            target_eval_method = {}
            for idx, target_name in enumerate(self.target_maps):
                tmp = None
                if eval_method_pool.get(target_name):
                    tmp = eval_method_pool[target_name][0]
                elif eval_method_pool.get(DEFAULT_POOL_KEY):  # 没有找到标的对应的值，随机选一个
                    choice = idx if len(eval_method_pool[DEFAULT_POOL_KEY]) >= idx + 1 else 0
                    tmp = eval_method_pool[DEFAULT_POOL_KEY][choice]
                if tmp:
                    target_eval_method[target_name] = "".join([char["text"] for char in tmp[0]])

            pools.update(
                {
                    "注册地": self.target_base_info("注册地", self.target_maps, **kwargs),
                    "经营场所": self.target_base_info("经营场所", self.target_maps, **kwargs),
                    "账面净资产": self.target_book_value("账面净资产", self.target_maps, **kwargs),
                    "标的公司三大财务报表的最近一年的净利润": self.recent_year_profit(
                        "标的公司三大财务报表的最近一年的净利润", self.target_maps, **kwargs
                    ),
                    "标的行业": self.target_busi("标的行业", self.target_maps, **kwargs),
                    "标的业务": self.target_prof("标的业务", self.target_maps, **kwargs),
                    "评估方法": eval_method_pool,
                    "资产评估值": self.get_asset_valuation(
                        "资产评估值", self.target_maps, target_eval_method, **kwargs
                    ),
                    "溢价率": self.get_premium_rate("溢价率", self.target_maps, target_eval_method, **kwargs),
                    "交易货币兑人民币汇率": self.sub_para("交易货币兑人民币汇率", self.target_maps, **kwargs),
                    "标的承诺期第一年净利润": self.sub_mixin(
                        "标的承诺期第一年净利润", self.target_maps, include_self=True, **kwargs
                    ),
                    "市盈率（静态）": self.sub_table("市盈率（静态）", self.target_maps, include_self=True, **kwargs),
                    "市盈率（动态）": self.sub_table("市盈率（动态）", self.target_maps, include_self=True, **kwargs),
                    "市净率": self.sub_table("市净率", self.target_maps, include_self=True, **kwargs),
                    "可比公司 静态市盈率 算术平均数": self.sub_table(
                        "可比公司 静态市盈率 算术平均数", self.target_maps, **kwargs
                    ),
                    "可比公司 静态市盈率 中位数": self.sub_table(
                        "可比公司 静态市盈率 中位数", self.target_maps, **kwargs
                    ),
                    "可比公司 动态市盈率 算术平均数": self.sub_table(
                        "可比公司 动态市盈率 算术平均数", self.target_maps, **kwargs
                    ),
                    "可比公司 动态市盈率 中位数": self.sub_table(
                        "可比公司 动态市盈率 中位数", self.target_maps, **kwargs
                    ),
                    "可比公司 市净率 算术平均数": self.sub_table(
                        "可比公司 市净率 算术平均数", self.target_maps, **kwargs
                    ),
                    "可比公司 市净率 中位数": self.sub_table("可比公司 市净率 中位数", self.target_maps, **kwargs),
                }
            )

            # build_field
            for target_name, field_map in self.target_maps.items():
                for sub_attr, pool in pools.items():
                    tmp = pool.get(target_name, []) + pool.get(DEFAULT_POOL_KEY, [])
                    if tmp:
                        field_map.setdefault(sub_attr, []).extend(tmp)

            for target_info in self.target_maps.values():
                target = {}
                for sub_attr in self.schema_dict.get(kwargs.get("col_type"), {}).get("orders", []):
                    items = []
                    field = target_info.get(sub_attr, [])
                    if field:
                        for item in field:
                            confirmed = False
                            if len(item) == 3:
                                confirmed = item[-1]
                                item = item[:2]
                            if item[-1]["class"] == "TABLE":
                                items.append(TblResult(*item, confirm=confirmed))
                            else:
                                items.append(ParaResult(*item, confirm=confirmed))
                    crude_elts = self.get_crude_elements(sub_attr, **kwargs)
                    target.setdefault(sub_attr, ResultOfPredictor(items, crude_elts=crude_elts))
                res.append(target)
        return res

    def sub_mixin(self, attr, target_maps, include_self=False, **kwargs):
        def fn_para(para, para_patts):
            for patt in para_patts:
                label = self._simple_label(patt, para)
                if not label:
                    return
                label_start = para["text"].find(label)
                chars = para["chars"][label_start : label_start + len(label)]
                self.fill_target_info_pool(attr, target_info_pool, para, target_maps, label=label, chars=chars)

        def fn_tbl(tbl, pattern, extra=None):
            tbl_idx, idx, idy, _ = self._get_aim_table([tbl], pattern, extra=extra)
            select_cells = []
            for idx_ in idx:
                label = self._get_cell_text(tbl, idx_, idy)
                aim_cell = "_".join([str(idx_), str(idy)])
                res = pat_cell_filt.search(label)
                if not res and aim_cell in tbl["cells"]:
                    select_cells.append(aim_cell)
            mem_cells = []
            memory_path = os.path.join(memory_dir, "%s.json" % attr)
            if (config.get_config("web.predict_from_memory.switch")) and os.path.exists(memory_path):
                mem_cells = TableUtil.cell_in_memory(tbl, json.load(open(memory_path)), existed=select_cells)
            select_cells.extend([_[0] for _ in Counter(mem_cells).most_common()])
            for select_cell in select_cells:
                self.fill_target_info_pool(attr, target_info_pool, tbl, target_maps, aim_cell=[select_cell])

        pattern = PATTERNS.get(attr, {})
        tbl_patts, para_patts = pattern.get("tbl"), pattern.get("para")
        target_info_pool = {DEFAULT_POOL_KEY: []}

        extra = list(map(self._extract_stock, target_maps.keys())) if include_self else []
        elts = self._find_elements(attr, typ=None, **kwargs)

        # elts = self._sort_elts(tbls, syl_patt) if syl_patt else elts  # for PRO
        if pattern.get("syl"):  # for DEV
            # print('\tORDERS:', [(elt['class'], elt['index']) for elt in elts])
            elts = self._sort_elts(elts, pattern.get("syl"))
            # print('\tORDERS:', [(elt['class'], elt['index']) for elt in elts])

        for _idx, elt in enumerate(elts):
            # print('--------', attr, '%s/%s' % (idx, len(elts)), elt['class'], elt['page'])
            if tbl_patts and elt.get("class", "") == "TABLE":
                fn_tbl(elt, pattern, extra)
            elif para_patts and elt.get("class", "") == "PARAGRAPH":
                fn_para(elt, para_patts)

            # if len(target_info_pool) > len(target_maps):
            #     break

        return target_info_pool

    def _sort_elts(self, elts, syl_patt):
        cur_idx, sylls_ = 0, [""] * len(elts)
        for idx, elt in enumerate(elts):
            sylls = self.reader.find_syllabuses_by_index(elt["index"])
            sylls_[idx] = clean_txt(sylls[-1].get("title", "")) if sylls else ""

        para_text = [self._get_previous_text(elt) for elt in elts]
        sylls_para_zip_text = list(zip(sylls_, para_text))

        for patt in syl_patt:
            base_idx = cur_idx
            for idx, _ in enumerate(elts[base_idx:]):
                (sylls, para) = sylls_para_zip_text[base_idx + idx]
                if patt.search(sylls) or patt.search(para):
                    elts.insert(cur_idx, elts.pop(base_idx + idx))
                    sylls_para_zip_text.insert(cur_idx, sylls_para_zip_text.pop(base_idx + idx))
                    cur_idx += 1

        return elts

    def _extract_stock(self, text):
        pat_search = re.compile(r"\d+(\.\d+)?(%|％)股(份|权)")
        result = pat_search.search(text)
        start = result.span(0)[0] if result else None
        return text[:start] if start is not None else text

    def sub_table(self, attr, target_maps, include_self=False, **kwargs):
        def _fill_info_pool(tbl, aim_tbl_info):
            tbl_idx, idx, idy, _ = aim_tbl_info
            select_cells = []
            for idx_ in idx:
                label = self._get_cell_text(tbl, idx_, idy)
                aim_cell = "_".join([str(idx_), str(idy)])
                res = pat_cell_filt.search(label)
                if not res and aim_cell in tbl["cells"]:
                    select_cells.append(aim_cell)
            mem_cells = []
            memory_path = os.path.join(memory_dir, "%s.json" % attr)
            if (config.get_config("web.predict_from_memory.switch")) and os.path.exists(memory_path):
                mem_cells = TableUtil.cell_in_memory(tbl, json.load(open(memory_path)), existed=select_cells)
            select_cells.extend([_[0] for _ in Counter(mem_cells).most_common()])
            for select_cell in select_cells:
                self.fill_target_info_pool(attr, target_info_pool, tbl, target_maps, aim_cell=[select_cell])

        pattern = PATTERNS.get(attr, {})
        target_info_pool = {DEFAULT_POOL_KEY: []}

        if not pattern.get("tbl"):
            return target_info_pool

        extra = list(map(self._extract_stock, target_maps.keys())) if include_self else []
        tbls = self._find_elements(attr, typ="TABLE", **kwargs)

        if pattern.get("syl"):
            tbls = self._sort_elts(tbls, pattern.get("syl"))

        for _elt_idx, tbl in enumerate(tbls):
            # print('--------', attr, '%s/%s' % (elt_idx, len(tbls)), 'tbl', tbl['page'], tbl['title'])
            aim_tbl_info = self._get_aim_table([tbl], pattern, extra)
            _fill_info_pool(tbl, aim_tbl_info)
        return target_info_pool

    def sub_para(self, attr, target_maps, **kwargs):
        pattern = PATTERNS.get(attr, {}).get("para")
        target_info_pool = {DEFAULT_POOL_KEY: []}  # 存放每个标的对应的该属性
        if not pattern:
            return target_info_pool

        elts = self._find_elements(attr, typ="PARAGRAPH", **kwargs)
        for patt in pattern:
            for _idx, element in enumerate(elts):
                # print('--------', attr, '%s/%s' % (idx, len(elts)), 'para', element['page'], element['text'])
                label = self._simple_label(patt, element)
                if not label:
                    continue

                label_start = element["text"].find(label)
                chars = element["chars"][label_start : label_start + len(label)]
                # print('*******', label)
                self.fill_target_info_pool(attr, target_info_pool, element, target_maps, label=label, chars=chars)
        return target_info_pool

    def recent_year_period(self, cells):
        """
        三年一期中最近一年or一期
        :param cells: 时间所在行/列
        :return: (recent_year, recent_period)
        """
        year_pattern = re.compile(r"(\d{4})年?度?")
        res = []
        for k, v in cells.items():
            if v.get("dummy"):  # 跳过合并单元格
                continue
            v = re.sub(r"\s+", "", v["text"])
            if year_pattern.search(v):
                res.append((k, v))
        if res and len(res) >= 2:
            times = sorted(res, key=lambda i: i[0])  # [(1, '2017年'), (2, '2016年度'), (3, '2015年度')]
            if "12" in times[0][1] or re.search(r"^\d{4}年?度?$", times[0][1]):  # 没有最近一期
                times.insert(0, (None, None))
            # print([re.sub(r'\s+', '', v['text']) for v in cells.values()])
            # print(times)
            return times[1][0], times[0][0]
        return None, None

    def scheme_intro(self, **kwargs):
        """
        方案简介
            标注规则：包含收购方式、交易对方、收购标的、配套融资、收购标的的子公司情况这些信息相连的所有句子。
        常见句式：
            拟通过 发行股份的方式/支付现金的方式/发行股份及收购现金的方式 购买……持有的【收购标的】，向……募集不超过xx元的配套资金（关键字是“配套资金/配套融资”）。
        特殊情况：
            1）收购标的通常是 公司名+百分比+“股权”，特殊情况：收购标的不是公司股权，而是某个项目或者某个资产。
            2）特殊的收购：资产置换，此时我们只关注置入资产，不关注置出资产。
            3）涉及好几项收购，收购方案按以上句式写了好几个，所以需要将这些句子都抽取出来。
        """
        attr = "方案简介"
        pattern = re.compile(r"(购买|[获取][取得]|收购)")
        items = []
        elts = self.get_crude_elements(attr, **kwargs)
        for _idx, element in enumerate(elts):
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "PARAGRAPH":
                # print('--------', attr, idx, 'para', element['page'], element['text'])
                if pattern.search(clean_txt(element["text"])):
                    # print('******', element['texts'])
                    items.append(ParaResult(element["chars"], element))
                    # break
                # if items:
                #     break
        return ResultOfPredictor(items, crude_elts=elts)

    def recent_total_assets(self, **kwargs):
        """
        披露前上市公司最近一年资产总额
        形式：表格中的数据
        字段：资产总额、资产总计、总资产
        时间：三年一期中的最近一年，或者三年中最近的一年
        """
        attr = "披露前上市公司最近一年资产总额"
        pattern = re.compile(r"^(资产[总合][额计]|总资产)")
        items = []
        elts = self.get_crude_elements(attr, **kwargs)
        for idx, element in enumerate(elts):
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "TABLE":
                cells_by_row, cells_by_col = group_cells(element["cells"])
                anchor_cell = self._locate_cell_from_tbl_header(element, pattern)  # 属性所在cell
                aim_cell = None
                # print('--------', attr, idx, 'tbl', element['page'], element['title'], anchor_cell)
                select_cells = []
                if anchor_cell:
                    aim_row, aim_col = anchor_cell.split("_")
                    # print('*******', anchor_cell, self._get_cell_text(element, aim_row, aim_col))
                    if aim_row:  # 属性在第一列， 时间在第一行
                        aim_col, _ = self.recent_year_period(cells_by_row.get("0", {}))
                    else:  # 属性在第一行， 时间在第一列
                        aim_row, _ = self.recent_year_period(cells_by_col.get("0", {}))
                    if aim_row is not None and aim_col is not None:
                        aim_cell = "_".join(map(str, [aim_row, aim_col]))
                    # print('*******', aim_cell, self._get_cell_text(element, aim_row, aim_col))
                    if aim_cell and element["cells"].get(aim_cell) and (aim_cell not in select_cells):
                        select_cells.append(aim_cell)
                mem_cells = []
                memory_path = os.path.join(memory_dir, "%s.json" % attr)
                if (config.get_config("web.predict_from_memory.switch")) and os.path.exists(memory_path):
                    mem_cells = TableUtil.cell_in_memory(element, json.load(open(memory_path)), existed=select_cells)
                select_cells.extend([_[0] for _ in Counter(mem_cells).most_common()])
                items.extend([TblResult([idx], element) for idx in select_cells])
        return ResultOfPredictor(items, crude_elts=elts)

    def amount_of_paid_shares(self, **kwargs):
        """
        股份对价支付数量
        交易对方对价情况”表中，目前是优先标这个表里的；
        如果这个表里没有，那么需要标段落里的：
        1）本次发行股份购买资产的股票发行数量为
        2）本次购买资产发行股份的数量为
        3）本次交易需向交易对方xx发行股份数量为
        """
        attr = "股份对价支付数量"
        tbl_patterns = [
            re.compile("(股[份票权]?|发行)(对价|支付|部分|数量?|[(（][万亿]?股[）)])"),
            re.compile("支付方式"),
            re.compile("(股[份票权]?|发行)?数量?"),
        ]
        para_patterns = [
            re.compile(
                r"("
                r"发行[^，：；。]*?(数量|股数)[^，：；。]*?(分别|不超过)[^，：；。]*?(，)(合计|即)"
                r"|同时拟向.*发行股份数量不超过"
                r"|折合股数"
                r"|发行[^，：；。]*?(股数|股票|数量|股份)"
                r"|向[^，：；。]*?发行"
                r"|(认购|收购)[^，：；。]*?(发行|持有)"
                r"|((共计)?发行|取得|认购|购买)"
                r")[^，：；。]*?(?P<target>\d+(,\d{3})*(\.\d+)?\s*[万亿]?股)"
            )
        ]
        money_pattern = re.compile(r"[-_,，.\s\d万亿元()（）]")
        ignore_pattern = [re.compile(r"占?比[利率]?"), re.compile(r"[(（][万亿]?元[）)]")]
        items = []
        elts = self.get_crude_elements(attr, **kwargs)
        for idx, element in enumerate(elts):
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "TABLE":
                anchor_cells = []
                cells_by_row, cells_by_col = group_cells(element["cells"])
                for pattern in tbl_patterns:
                    for col, cell in cells_by_row.get("0", {}).items():
                        if pattern.search(clean_txt(cell["text"])) and not any(
                            reg.search(clean_txt(cell["text"])) for reg in ignore_pattern
                        ):
                            # print('anchor_cell', col, clean_txt(cell['text']), pattern)
                            anchor_cells.append("_".join(map(str, [0, col])))
                    if anchor_cells:
                        break
                # print('--------', attr, self.file.id, idx, 'tbl', element['index'], element['page'], element['title'],
                #       anchor_cells)
                # d1 = {k: v['text'] for k, v in element['cells'].items() if k.startswith('0_')}
                # print(sorted(d1.items(), key=lambda x: int(x[0].split('_')[1]), reverse=True))
                # d2 = {k: v['text'] for k, v in element['cells'].items() if k.endswith('_0')}
                # print(sorted(d2.items(), key=lambda x: int(x[0].split('_')[0]), reverse=True))
                select_cells = []
                if anchor_cells:
                    second_cells = []
                    if len(anchor_cells) > 1:  # 检查第二行是否为标题
                        for anchor_cell in deepcopy(anchor_cells):
                            sec_cell = anchor_cell.replace("0_", "1_")
                            if money_pattern.sub("", element["cells"].get(sec_cell, {}).get("text", "")):
                                anchor_cells.remove(anchor_cell)
                                second_cells.append(sec_cell)
                    # print('anchor_cells', anchor_cells)
                    # print('second_cells', second_cells)
                    aim_cell = None
                    if len(anchor_cells) == 1:
                        anchor_cell = anchor_cells[0]
                        _, aim_col = anchor_cell.split("_")
                        for row in sorted(map(int, cells_by_col.get("0", {}).keys()), reverse=True):
                            if not money_pattern.sub(
                                "", element["cells"].get("_".join(map(str, [row, aim_col])), {}).get("text", "")
                            ):
                                aim_cell = "_".join(map(str, [row, aim_col]))
                            if aim_cell:
                                break
                    else:
                        aim_col = None
                        for reg in tbl_patterns:
                            for second_cell in second_cells:
                                cell_text = clean_txt(element["cells"].get(second_cell, {}).get("text", ""))
                                if reg.search(cell_text) and not any(
                                    pattern.search(cell_text) for pattern in ignore_pattern
                                ):
                                    # print('second_cell', second_cell, cell_text, reg)
                                    aim_col = second_cell.split("_")[1]
                                if aim_col is not None:
                                    for row in sorted(map(int, cells_by_col.get("0", {}).keys()), reverse=True):
                                        if not money_pattern.sub(
                                            "",
                                            element["cells"]
                                            .get("_".join(map(str, [row, aim_col])), {})
                                            .get("text", ""),
                                        ):
                                            aim_cell = "_".join(map(str, [row, aim_col]))
                                        if aim_cell:
                                            break
                                    break
                    if (
                        aim_cell
                        and element["cells"].get(aim_cell)
                        and money_pattern.search(clean_txt(element["cells"][aim_cell]["text"]))
                    ):
                        # print('*****', aim_cell, element['cells'].get(aim_cell)['text'])
                        # items.append(TblResult([aim_cell, ], element))
                        select_cells.append(aim_cell)
                        # break
                mem_cells = []
                memory_path = os.path.join(memory_dir, "%s.json" % attr)
                if (config.get_config("web.predict_from_memory.switch")) and os.path.exists(memory_path):
                    mem_cells = TableUtil.cell_in_memory(element, json.load(open(memory_path)), existed=select_cells)
                select_cells.extend([_[0] for _ in Counter(mem_cells).most_common()])
                items.extend([TblResult([idx], element) for idx in select_cells])
        if not items:
            for _idx, element in enumerate(elts):
                ele_typ, element = self.reader.find_element_by_index(element["element_index"])
                if ele_typ == "PARAGRAPH":
                    # print('--------', attr, self.file.id, idx, 'para', element['page'], element['text'])
                    for pattern in para_patterns:
                        label = self._simple_label(pattern, element)
                        if label:
                            label_start = element["text"].find(label)
                            chars = element["chars"][label_start : label_start + len(label)]
                            # print('****', label, [x['text'] for x in chars])
                            items.append(ParaResult(chars, element))
                    #         break
                    # if items:
                    #     break
        return ResultOfPredictor(items, crude_elts=elts)

    def price_of_paid_shares(self, **kwargs):
        """
        股份对价支付金额
        `交易对方对价情况`表中，目前是优先标这个表里的；
        如果这个表里没有，那么需要标段落里的：
        1）本次发行股份购买资产的股票发行金额为
        2）本次购买资产发行股份的金额为
        3）本次交易需向交易对方xx发行股份金额为
        """
        attr = "股份对价支付金额"
        tbl_patterns = [
            re.compile("(股[份票权])(对价|支付|部分)"),
            re.compile("支付方式"),
            re.compile("(交易)?(对价|金额|价格)"),
        ]
        para_patterns = [
            re.compile(
                r"(发行股份[^，：。]*?支付"
                r"|(股份对价|股份支付金额|股份转让对价|股权作价|股票对价)"
                r"|发行股份[^，：。]*?购买资产[^，：。]*?交易对价"
                r"|派发股利"
                r"|拟购买[^，：。]*?股权评估值"
                r"|股权收购[^，：。]*?对价)"
                r"[^，：。]*?(?P<target>\d{1,3}(,\d{3})*(\.\d{2})?\s*[万亿]?元)"
            ),
            re.compile(
                r"剩余" r"[^，：。]*?(?P<target>\d{1,3}(,\d{3})*(\.\d{2})?\s*[万亿]?元)" r"以发行股份的?方式支付"
            ),
        ]
        money_pattern = re.compile(r"[-_,，.\s\d万亿元()（）]")
        ignore_pattern = [re.compile(r"占?比[利率]?"), re.compile(r"[(（][万亿]?股[）)]")]

        items = []
        elts = self.get_crude_elements(attr, **kwargs)
        for idx, element in enumerate(elts):
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "TABLE":
                anchor_cells = []
                cells_by_row, cells_by_col = group_cells(element["cells"])
                for pattern in tbl_patterns:
                    for col, cell in cells_by_row.get("0", {}).items():
                        if pattern.search(clean_txt(cell["text"])) and not any(
                            reg.search(clean_txt(cell["text"])) for reg in ignore_pattern
                        ):
                            # print('anchor_cell', col, clean_txt(cell['text']), pattern)
                            anchor_cells.append("_".join(map(str, [0, col])))
                    if anchor_cells:
                        break
                # print('--------', attr, self.file.id, idx, 'tbl', element['index'], element['page'], element['title'],
                #       anchor_cells)
                # d1 = {k: v['text'] for k, v in element['cells'].items() if k.startswith('0_')}
                # print(sorted(d1.items(), key=lambda x: int(x[0].split('_')[1]), reverse=True))
                # d2 = {k: v['text'] for k, v in element['cells'].items() if k.endswith('_0')}
                # print(sorted(d2.items(), key=lambda x: int(x[0].split('_')[0]), reverse=True))
                select_cells = []
                if anchor_cells:
                    second_cells = []
                    if len(anchor_cells) > 1:
                        for anchor_cell in deepcopy(anchor_cells):  # 第二行是否为表头
                            sec_cell = anchor_cell.replace("0_", "1_")
                            if money_pattern.sub("", element["cells"].get(sec_cell, {}).get("text", "")):  # 不是金额
                                anchor_cells.remove(anchor_cell)
                                second_cells.append(sec_cell)
                    aim_cell = None
                    if len(anchor_cells) == 1:
                        anchor_cell = anchor_cells[0]
                        _, aim_col = anchor_cell.split("_")
                        for row in sorted(map(int, cells_by_col.get("0", {}).keys()), reverse=True):
                            if not money_pattern.sub(
                                "", element["cells"].get("_".join(map(str, [row, aim_col])), {}).get("text", "")
                            ):
                                aim_cell = "_".join(map(str, [row, aim_col]))
                            if aim_cell:
                                break
                    else:
                        aim_col = None
                        for reg in tbl_patterns:
                            for second_cell in second_cells:
                                cell_text = clean_txt(element["cells"].get(second_cell, {}).get("text", ""))
                                if reg.search(cell_text) and not any(
                                    pattern.search(cell_text) for pattern in ignore_pattern
                                ):
                                    # print('second_cell', second_cell, cell_text, reg)
                                    aim_col = second_cell.split("_")[1]
                                if aim_col is not None:
                                    for row in sorted(map(int, cells_by_col.get("0", {}).keys()), reverse=True):
                                        if not money_pattern.sub(
                                            "",
                                            element["cells"]
                                            .get("_".join(map(str, [row, aim_col])), {})
                                            .get("text", ""),
                                        ):
                                            aim_cell = "_".join(map(str, [row, aim_col]))
                                        if aim_cell:
                                            break
                                    break
                    if (
                        aim_cell
                        and element["cells"].get(aim_cell)
                        and money_pattern.search(clean_txt(element["cells"][aim_cell]["text"]))
                    ):
                        # print('*****', aim_cell, element['cells'].get(aim_cell)['text'])
                        # items.append(TblResult([aim_cell, ], element))
                        select_cells.append(aim_cell)
                mem_cells = []
                memory_path = os.path.join(memory_dir, "%s.json" % attr)
                if (config.get_config("web.predict_from_memory.switch")) and os.path.exists(memory_path):
                    mem_cells = TableUtil.cell_in_memory(element, json.load(open(memory_path)), existed=select_cells)
                select_cells.extend([_[0] for _ in Counter(mem_cells).most_common()])
                items.extend([TblResult([idx], element) for idx in select_cells])
        if not items:
            for _idx, element in enumerate(elts):
                ele_typ, element = self.reader.find_element_by_index(element["element_index"])
                if ele_typ == "PARAGRAPH":
                    # print('--------', attr, self.file.id, idx, 'para', element['page'], element['text'])
                    for pattern in para_patterns:
                        label = self._simple_label(pattern, element)
                        if label:
                            label_start = element["text"].find(label)
                            chars = element["chars"][label_start : label_start + len(label)]
                            # print('****', label, [x['text'] for x in chars])
                            items.append(ParaResult(chars, element))
        return ResultOfPredictor(items, crude_elts=elts)

    def asset_ratio(self, **kwargs):
        """
        交易或资产金额占比
        形式：表格中的数据
        定位表格后，找"资产总额"那一行/列的百分比，如果是2个百分比，一般标第二个
        如果有2个百分比，排除带“标准/准则”字样的那行/列数据，或者排除“50%”这个数据，如果还剩2个百分比，再执行之前的规则
        """
        attr = "交易或资产金额占比"
        pattern = re.compile(r"^(资产[合总][额计]|总资产)")
        elts = self.get_crude_elements(attr, **kwargs)

        def find_ratio_cell(tbl, row=None, col=None):
            cells_by_row, cells_by_col = group_cells(tbl["cells"])
            if row is not None:
                cells, heads = cells_by_row.get(row, {}), cells_by_row.get("0", {})
            else:
                cells, heads = cells_by_col.get(col, {}), cells_by_col.get("0", {})
            # print(row, col, {k: v['text'] for k, v in cells.items()})

            for idx in sorted(map(int, cells.keys()), reverse=True):  # 倒序查找百分比
                idx = str(idx)
                cell, head = cells.get(idx, {}), heads.get(idx, {})
                if re.search(r"(标准|准则)", clean_txt(head.get("text", ""))):  # 排除"标准/准则"
                    continue
                if (clean_txt(cell.get("text", "")).find("%") != -1) or (
                    re.search(r"比[值率例]|占比", clean_txt(head.get("text", "")))
                ):
                    return idx

        items = []
        for idx, element in enumerate(elts):
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "TABLE":
                anchor_cell = self._locate_cell_from_tbl_header(element, pattern)  # 属性所在cell
                aim_cell = None
                # print('--------', attr, idx, ele_typ, element['page'], element['title'], anchor_cell)
                select_cells = []
                if anchor_cell:
                    aim_row, aim_col = anchor_cell.split("_")
                    # print('*******', anchor_cell, self._get_cell_text(element, aim_row, aim_col))
                    if aim_row != "0":  # 属性在第一列
                        aim_col = find_ratio_cell(element, row=aim_row)
                    else:  # 属性在第一行
                        aim_row = find_ratio_cell(element, col=aim_col)
                    if aim_row is not None and aim_col is not None:
                        aim_cell = "_".join(map(str, [aim_row, aim_col]))
                    # print('*******', aim_cell, self._get_cell_text(element, aim_row, aim_col))
                    if aim_cell and element["cells"].get(aim_cell) and (aim_cell not in select_cells):
                        select_cells.append(aim_cell)
                mem_cells = []
                memory_path = os.path.join(memory_dir, "%s.json" % attr)
                if (config.get_config("web.predict_from_memory.switch")) and os.path.exists(memory_path):
                    mem_cells = TableUtil.cell_in_memory(element, json.load(open(memory_path)), existed=select_cells)
                select_cells.extend([_[0] for _ in Counter(mem_cells).most_common()])
                items.extend([TblResult([idx], element) for idx in select_cells])
        return ResultOfPredictor(items, crude_elts=elts)

    def consideration(self, **kwargs):
        """
        交易对方对价情况，提取整个表格
        绝大部分情况是以表格形式出现， 可能有多个
        表头中的关键字：交易对方、交易对手、对价、作价、交易价格、交易金额、支付
        """
        attr = "交易对方对价情况"
        pattern = re.compile(r"(交易(对方|对手|对象|价格|金额)|对价|作价|支付)")
        items = []
        elts = self.get_crude_elements(attr, **kwargs)
        for _idx, element in enumerate(elts):
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "TABLE":
                # print('--------', '%s/%s' % (idx, len(elts)), 'tbl', element['page'], element['title'])
                anchor_cell = self._locate_cell_from_tbl_header(element, pattern)  # 属性所在cell
                if anchor_cell:
                    # print('*******', anchor_cell, self._get_cell_text(element, *anchor_cell.split('_')))
                    items.append(TblResult([], element))
        return ResultOfPredictor(items, crude_elts=elts)

    def _simple_label(self, pattern, para):
        res = pattern.search(para["text"])
        if res:
            return res.group("target")

    def _pdf_first_line(self, attr, **kwargs):
        """
        从文档的第一个段落中查找
        句式：证券代码:300091 证券简称:金通灵 上市地点:深圳证券交易所
        """
        pattern = PATTERNS.get(attr)
        items, paras = [], []

        # 目标元素块为文档第一段和页眉
        if self.reader.data.get("paragraphs"):
            paras.append(self.reader.data["paragraphs"][0])
        if self.reader.data.get("page_headers"):
            paras.append(self.reader.data["page_headers"][0])

        for para in paras:
            # print('-----', attr, para['class'], para['text'], re.split(r'\s+', para['text']))
            for section in re.split(r"\s+", para["text"]):
                if pattern.match(section) and len(section.split("：")) == 2:
                    _, label = section.split("：")
                    label_start = para["text"].find(section) + len(_) + 1
                    chars = para["chars"][label_start : label_start + len(label)]
                    if label:
                        # print('****', label, [x['text'] for x in chars])
                        items.append(ParaResult(chars, para))
                        break
            if items:
                break
        return ResultOfPredictor(items, crude_elts=self.get_crude_elements(attr, **kwargs))

    def _get_cell_chars(self, tbl, idx, idy):
        key = "_".join(map(str, [idx, idy]))
        if key not in tbl["cells"]:
            return ""
        return tbl["cells"][key]["chars"]

    def _get_cell_text(self, tbl, idx, idy):
        key = "_".join(map(str, [idx, idy]))
        if key not in tbl["cells"]:
            return ""
        return tbl["cells"][key]["text"]

    def _locate_cell_from_tbl_header(self, tbl, pattern):
        """
        从表头中查找关键字，作为锚点
        """
        cells_by_row, cells_by_col = group_cells(tbl["cells"])

        for col, cell in cells_by_row.get("0", {}).items():  # 第一行
            if pattern.search(clean_txt(cell["text"])):
                return "_".join(map(str, [0, col]))
        for row, cell in cells_by_col.get("0", {}).items():  # 第一列
            if pattern.search(clean_txt(cell["text"])):
                return "_".join(map(str, [row, 0]))

    def _find_elements(self, attr, typ=None, **kwargs):  # typ: TABLE PARAGRAPH
        crude_elts = self.get_crude_elements(attr, **kwargs)
        idxs = [elt.get("element_index") for elt in crude_elts]
        elts = [self.reader.find_element_by_index(idx) for idx in idxs]

        if not typ:
            return [elt[1] for elt in elts if all(elt)]
        else:
            return [elt[1] for elt in elts if all(elt) and elt[0] == typ]

    def _aim_para(self, attr, **kwargs):
        pattern = PATTERNS.get(attr, {}).get("para")
        if not pattern:
            return []

        items = []
        paras = self._find_elements(attr, typ="PARAGRAPH", **kwargs)
        for patt in pattern:
            for para in paras:
                # print('--------', attr, 'para', para['page'], para['text'])
                for item in patt.finditer(para["text"]):
                    item.group()
                    chars = para["chars"][item.start() : item.end()]
                    # print('******', label, [x['text'] for x in chars])
                    items.append(ParaResult(chars, para))
        return ResultOfPredictor(items, crude_elts=self.get_crude_elements(attr, **kwargs))

    def _add_info_to_table(self, tbl):
        attr_dict = {"cells_by_row": {}, "cells_by_col": {}, "nrows": 0, "ncols": 0, "ntitles": 0}
        attr_dict["cells_by_row"], attr_dict["cells_by_col"] = group_cells(tbl["cells"])
        attr_dict["nrows"], attr_dict["ncols"] = len(attr_dict["cells_by_row"]), len(attr_dict["cells_by_col"])
        ntitles = 0
        matrix = self._tbl_to_matrix(attr_dict["cells_by_row"], row_limit=3)

        if attr_dict["nrows"] >= 3 and not ntitles:
            ntitles = 3 if any((x[0] == x[1] == x[2] for x in zip(*matrix[:3]))) else 0
        if attr_dict["nrows"] >= 2 and not ntitles:
            ntitles = 2 if any((x[0] == x[1] for x in zip(*matrix[:2]))) else 0
        attr_dict["ntitles"] = 1 if not ntitles else ntitles  # ntitles==1 may also means no headline

        tbl.update(attr_dict)

        return tbl

    def _tbl_to_matrix(self, cells_by_rank, row_limit=3):
        """Sort all cells'text as a matrix(only text).

        :row_limit=None means no limitation
        """
        matrix = [
            [[clean_txt(col.get("text", ""))] for _, col in sorted(row.items(), key=lambda x: int(x[0]))]
            for _, row in sorted(cells_by_rank.items(), key=lambda x: int(x[0]))[:row_limit]
        ]

        return matrix

    def _sort_table_keys(self, tbl, by_row=True, rev_row=False, rev_col=False):
        """Sort all table keys, default row_first."""
        ret = []
        keys = tbl.get("cells", {}).keys()
        key_dic = defaultdict(list)
        for key in keys:
            k, v = key.split("_")
            key_dic[k].append(v)

        if by_row:
            ret = [
                "_".join([row, col])
                for row in sorted(key_dic.keys(), key=int, reverse=rev_row)
                for col in sorted(key_dic[row], key=int, reverse=rev_col)
            ]
        else:
            ret = [
                "_".join([row, col])
                for col in sorted(key_dic.get("0", []), key=int, reverse=rev_col)
                for row in sorted(key_dic.keys(), key=int, reverse=rev_row)
            ]

        return ret

    def _sort_rank_keys(self, cells, reverse=False):
        """Sort keys of cells_by_col/row that returned by group_cells"""
        return sorted(cells.items(), key=lambda x: int(x[0]), reverse=reverse)

    def _get_previous_text(self, elt, typ="PARAGRAPH"):
        try_, typ_, para, text = 3, None, None, ""
        while try_:
            try_ -= 1
            typ_, para = self.reader.find_element_by_index(elt["index"] - 1)
            text = clean_txt(para.get("text", "")) if typ_ == typ and para else ""
            if text and text[-1] in lst_colon:
                return text

        return text

    def _locate_cell_key(self, tbl, pattern, extra=None):
        """Return idx&idy of cell of tbl matchs one of patterns"""

        def _has_extra(text):
            return pat_mean.search(text)

        def _get_idx_normal(tbl, patt, idy, extra=None):  # positioning AIM normally
            idx = []
            idx_mean = _get_mean_start(tbl)
            for key in self._sort_table_keys(tbl, by_row=False, rev_row=True):
                row, col = key.split("_")
                if int(row) < tbl.get("ntitles"):
                    continue
                if int(col) >= int(idy):
                    break

                cell_txt = clean_txt(tbl["cells"][key]["text"])

                cell_txt_ex = self._extract_stock(cell_txt) if extra and int(row) > idx_mean else ""
                if patt[0].search(cell_txt) or cell_txt in extra or cell_txt_ex and cell_txt_ex in extra:
                    idx_, idy_ = key.split("_")
                    if idx_ not in idx:
                        idx.append(idx_)

            return idx

        def _get_mean_start(tbl):
            for idx, row in self._sort_rank_keys(tbl.get("cells_by_row"), reverse=False):
                if int(idx) < tbl.get("ntitles"):
                    continue

                texts = [cell["text"] for cell in row.values()]
                texts = [text for text in texts if not pat_col_title_esc.search(text)]
                if any(map(_has_extra, texts)):
                    return int(idx)

            return float("inf")

        def _get_idx_corpore(tbl, idy, extra=None):  # positioning corpore via '均值|平均|中位|中值'
            idx = ""
            idx_mean = _get_mean_start(tbl)
            for key in self._sort_table_keys(tbl, by_row=False):
                row, col = key.split("_")
                if int(row) < max(tbl.get("ntitles"), idx_mean):
                    continue
                if int(col) >= int(idy):
                    break

                cell_txt = clean_txt(tbl["cells"][key]["text"])
                if pat_col_title_esc.search(cell_txt):
                    continue
                if _has_extra(cell_txt):
                    idx_, idy_ = key.split("_")
                    idx = idx_ if idx and int(idx_) > int(idx) else idx or idx_

            result = str(int(idx) + 1) if idx and int(idx) + 1 < tbl.get("nrows") else ""

            return [result] if result else []

        def _get_idy(tbl, patt, row=0, start=None, end=None):
            idy, start_, end_ = "", 0, 0

            if not patt or not all(patt[: row + 1]):
                return idy, start, end

            col_title = ""
            for col, cell in self._sort_rank_keys(tbl.get("cells_by_row", {}).get(str(row), {}), reverse=False):
                if start and end and (int(col) < start or int(col) > end):
                    continue

                text = clean_txt(cell["text"])
                if pat_col_title_esc.search(text):
                    continue

                if not idy and patt[row + 1].search(text):
                    idy, start_ = col, int(col)
                    col_title = cell["text"]

                if idy and col_title == cell["text"]:
                    end_ = int(col)
                elif idy and col_title != cell["text"]:
                    break

            return idy, start_, end_

        def _conform_to_sylla(tbl, pat_sylla):
            # pat_conform_to_sylla = 可比*
            sylls = self.reader.find_syllabuses_by_index(tbl["index"])
            res_1 = pat_sylla.search(clean_txt(sylls[-1].get("title", ""))) if sylls else None

            para_txt = self._get_previous_text(tbl)
            res_2 = pat_sylla.search(para_txt) and para_txt[-1] in lst_colon

            return True if res_1 or res_2 else False

        def _get_index_default(tbl, patt):
            idx, idy = [], ""

            for idx_, row_cells in self._sort_rank_keys(tbl.get("cells_by_row"), reverse=False):
                cell_text = ""
                if int(idx_) < tbl.get("ntitles"):
                    continue
                for idy_, cell in self._sort_rank_keys(row_cells, reverse=False):
                    cell_text_ = clean_txt(cell["text"])
                    res = patt.search(cell_text_)
                    if res:
                        cell_text = cell_text_
                    elif not res and cell_text:
                        return [idx_], idy_

            return idx, idy

        def func_(pattern, patt):
            # if tbl['index'] == 1722:
            #     from pudb import set_trace; set_trace()
            idx, idy = [], ""
            # 1. check the first row
            idy, start, end = _get_idy(tbl, patt, row=0)

            # 2. check the second row
            if patt[2:] and idy:
                idy, start, end = _get_idy(tbl, patt, row=1, start=start, end=end)

            # 2. maybe the third row
            if patt[3:] and idy:
                idy, *_ = _get_idy(tbl, patt, row=2, start=start, end=end)

            # 3.1 include_self=True, ["市盈率（静态）", "市盈率（动态）", "市净率",]
            if idy:
                idx = _get_idx_normal(tbl, patt, idy, extra=extra)

                if not idx and extra and _conform_to_sylla(tbl, pat_conform_to_sylla):
                    idx = _get_idx_corpore(tbl, idy, extra=extra)
            elif pattern.get("default"):
                idx, idy = _get_index_default(tbl, pattern.get("default"))

            return idx, idy

        tbl = self._add_info_to_table(tbl)
        idx, idy = "", ""
        for patt in pattern.get("tbl", []):
            if len(patt) != tbl.get("ntitles") + 1:
                continue
            idx, idy = func_(pattern, patt)
            if idx and idy:
                return idx, idy

        return idx, idy

    def _get_aim_table(self, tbls, pattern, extra=None):
        extra = [] if extra is None else extra
        for index, tbl in enumerate(tbls):
            idx, idy = self._locate_cell_key(tbl, pattern, extra=extra)
            if idx and idy:
                return index, idx, idy, 0

        return None, [], "", 0

    def _aim_table_fix(self, attr, **kwargs):
        items = []
        pattern = PATTERNS.get(attr, {})
        crude_elts = self.get_crude_elements(attr, **kwargs)
        if not pattern.get("tbl"):
            return ResultOfPredictor(items, crude_elts=crude_elts)

        tbls = self._find_elements(attr, typ="TABLE", **kwargs)
        tbl_index, idx, idy, _ = self._get_aim_table(tbls, pattern)

        if tbl_index is not None:
            tbl = tbls[tbl_index]
            label = self._get_cell_text(tbl, idx[0], idy)
            aim_cell = "_".join([str(idx[0]), str(idy)])
            res = pat_cell_filt.search(label)
            if not res and aim_cell in tbl["cells"]:
                items.append(TblResult([aim_cell], tbl))

        if items:
            return ResultOfPredictor(items, crude_elts=crude_elts)

        return self._aim_para(attr, **kwargs)

    def _aim_mixin(self, attr, **kwargs):
        def _tbl(tbls, pattern):
            aim_tbl = self._get_aim_table(tbls, pattern)
            tbl_idx, idx, idy, _ = aim_tbl
            if tbl_idx is None:
                return None

            tbl = tbls[tbl_idx]
            label = self._get_cell_text(tbl, idx[0], idy)
            aim_cell = "_".join([str(idx[0]), str(idy)])
            res = pat_cell_filt.search(label)

            if not res and aim_cell in tbl["cells"]:
                # return TblResult([aim_cell, ], tbl)
                return aim_cell

        def _para(paras, pattern):
            para = paras[0] if paras else None
            if not para:
                return None

            for patt in pattern:
                label = self._simple_label(patt, para)
                if not label:
                    continue

                label_start = para["text"].find(label)
                chars = para["chars"][label_start : label_start + len(label)]
                return ParaResult(chars, para)

        items = []
        pattern = PATTERNS.get(attr, {})
        tbl_pattern, para_pattern = pattern.get("tbl"), pattern.get("para")

        elts = self._find_elements(attr, typ=None, **kwargs)
        for elt in elts:
            if elt["class"] == "TABLE" and tbl_pattern:
                select_cells = []
                aim_cell = _tbl([elt], pattern)
                if aim_cell:
                    select_cells.append(aim_cell)
                mem_cells = []
                memory_path = os.path.join(memory_dir, "%s.json" % attr)
                if (config.get_config("web.predict_from_memory.switch")) and os.path.exists(memory_path):
                    mem_cells = TableUtil.cell_in_memory(elt, json.load(open(memory_path)), existed=select_cells)
                select_cells.extend([_[0] for _ in Counter(mem_cells).most_common()])
                items.extend([TblResult([idx], elt) for idx in select_cells])
            elif elt["class"] == "PARAGRAPH" and para_pattern:
                item = _para([elt], para_pattern)
                if item:
                    items.append(item)
        return ResultOfPredictor(items, crude_elts=self.get_crude_elements(attr, **kwargs))
