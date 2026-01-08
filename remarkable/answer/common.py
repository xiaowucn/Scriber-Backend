import json
from collections import OrderedDict
from copy import deepcopy
from hashlib import md5
from itertools import zip_longest
from typing import Literal

import numpy as np
from pdfparser.pdftools.pdf_doc import PDFDoc
from pdfparser.pdftools.pdf_util import PDFUtil

from remarkable.common.schema import Schema
from remarkable.common.util import compact_dumps, md5json
from remarkable.config import get_config
from remarkable.models.new_user import ADMIN
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.predictor.mold_schema import MoldSchema, SchemaItem


def parse_path(key):
    return [(name, int(idxstr)) for name, idxstr in [p.split(":") for p in json.loads(key)]]


def name_path(path):
    return "_".join([k for k, i in path[1:]])


def full_path(path):
    return "_".join(["%s:%s" % (k, i) for k, i in path])


def get_mold_name(answer):
    return answer["schema"]["schemas"][0]["name"]


def fix_answer_outline(pdf_path, answer_dict, remove_manual=False):
    """缩小文字外框"""
    pages = []
    for item in answer_dict["userAnswer"]["items"]:
        for datum in item["data"]:
            for box_info in datum.get("boxes"):
                page = box_info.get("page")
                if page not in pages:
                    pages.append(page)
    doc = PDFDoc(pdf_path, pages)
    for item in answer_dict["userAnswer"]["items"]:
        if remove_manual:
            item.pop("manual", None)
            item.pop("marker", None)
        for datum in item["data"]:
            for box_info in datum.get("boxes"):
                box = box_info.get("box")
                page = box_info.get("page")
                top = float(box.get("box_top"))
                left = float(box.get("box_left"))
                right = float(box.get("box_right"))
                bottom = float(box.get("box_bottom"))
                outline = (left, top, right, bottom)
                chars = PDFUtil.chars_in_box_by_center(doc.pages[page], outline)
                fixed_outline = PDFUtil.get_bound_box([char["box"] for char in chars])
                if fixed_outline:
                    # 默认外框太小, 稍微放缩一哈
                    box["box_top"] = fixed_outline[1] - 2
                    box["box_left"] = fixed_outline[0] - 2
                    box["box_right"] = fixed_outline[2] + 2
                    box["box_bottom"] = fixed_outline[3] + 2
    return answer_dict


def fix_answer_outline_interdoc(pdfinsight_path, answer_dict, remove_manual=False):
    """缩小文字外框"""
    pages = []
    for item in answer_dict["userAnswer"]["items"]:
        for datum in item["data"]:
            for box_info in datum.get("boxes"):
                page = box_info.get("page")
                if page not in pages:
                    pages.append(page)
    interdoc = PdfinsightReader(pdfinsight_path)
    for item in answer_dict["userAnswer"]["items"]:
        if remove_manual:
            item.pop("manual", None)
            item.pop("marker", None)
        for datum in item["data"]:
            for box_info in datum.get("boxes"):
                box = box_info.get("box")
                page = box_info.get("page")
                top = float(box.get("box_top"))
                left = float(box.get("box_left"))
                right = float(box.get("box_right"))
                bottom = float(box.get("box_bottom"))
                outline = (left, top, right, bottom)
                _, chars = interdoc.find_chars_by_outline(page, outline)
                chars_outline = PDFUtil.get_bound_box([char["box"] for char in chars if char["text"] not in ("", " ")])
                if chars_outline:
                    fixed_outline = reivse_outline_v2(outline, chars_outline)
                    box["box_top"] = fixed_outline[1]
                    box["box_left"] = fixed_outline[0]
                    box["box_right"] = fixed_outline[2]
                    box["box_bottom"] = fixed_outline[3]
                    box["adjust_with_anno"] = True
                else:
                    box["adjust_with_anno"] = False
    return answer_dict


def reivse_outline(
    anno_outline: tuple[float, float, float, float], chars_outline: tuple[float, float, float, float]
) -> tuple[float, float, float, float]:
    """字符框 向 标注框 扩展，并保证左右扩展相同长度"""
    if not chars_outline:
        return anno_outline
    w_adjust = min(max(chars_outline[0] - anno_outline[0], 0), max(anno_outline[2] - chars_outline[2], 0))
    h_adjust = min(max(chars_outline[1] - anno_outline[1], 0), max(anno_outline[3] - chars_outline[3], 0))
    return (
        chars_outline[0] - w_adjust,
        chars_outline[1] - h_adjust,
        chars_outline[2] + w_adjust,
        chars_outline[3] + h_adjust,
    )


def reivse_outline_v2(
    anno_outline: tuple[float, float, float, float], chars_outline: tuple[float, float, float, float], outline_enlarge=2
) -> tuple[float, float, float, float]:
    """尽量扩展长度 outline_enlarge，但不要超过标注框"""
    w_adjust = min(
        min(max(chars_outline[0] - anno_outline[0], 0), outline_enlarge),
        min(max(anno_outline[2] - chars_outline[2], 0), outline_enlarge),
    )
    h_adjust = min(
        min(max(chars_outline[1] - anno_outline[1], 0), outline_enlarge),
        min(max(anno_outline[3] - chars_outline[3], 0), outline_enlarge),
    )
    return (
        chars_outline[0] - w_adjust,
        chars_outline[1] - h_adjust,
        chars_outline[2] + w_adjust,
        chars_outline[3] + h_adjust,
    )


def gen_key_md5(item: dict):
    return item["md5"] if item.get("md5") else md5(item["key"].encode()).hexdigest()


def is_empty_answer_item(item: dict):
    return not (item.get("data") or item.get("value"))


def is_empty_answer(answer_data: dict | None, check_key: Literal["userAnswer", "custom_field"] = None) -> bool:
    if not isinstance(answer_data, dict):
        return True

    keys = {"userAnswer", "custom_field"}
    if check_key:
        keys &= {check_key}
    if not keys:
        return True

    if len(keys) > 1:
        items_array = np.array(
            tuple(zip_longest(*(answer_data.get(k, {}).get("items", []) for k in keys), fillvalue={}))
        )
    else:
        items_array = np.array(answer_data.get(check_key, {}).get("items", []))
    if not items_array.size:
        return True
    empty_check = np.vectorize(is_empty_answer_item)(items_array)
    return np.all(empty_check)


def dump_key(key: str) -> str:
    # '["基金合同V1:0","001基金名称:0"]' -> "基金合同V1:0|001基金名称:0"
    return "|".join(json.loads(key))


def get_first_level_field(key: str) -> str:
    key = json.loads(key)
    return key[1].split(":")[0]


def create_empty_answer(schema: SchemaItem, index: int = 0):
    path = [(schema.path[0], 0), (schema.path[1], index), *((path, 0) for path in schema.path[2:])]
    return {
        "_migrated": False,
        "custom": False,
        "data": [],
        "key": compact_dumps([f"{k}:{i}" for k, i in path]),
        "manual": None,
        "marker": {"id": ADMIN.id, "name": ADMIN.name, "others": []},
        "meta": {},
        "schema": {
            "data": {
                "description": None,
                "label": schema.name,
                "words": "",
                **schema.data,
            }
        },
        "score": 0.00,
        "text": None,
        "value": [],
    }


def update_manual_tag(answer: dict) -> dict:
    """更新有效答案条目的manual标记"""
    for item in answer.get("userAnswer", {}).get("items", []):
        if is_empty_answer_item(item):
            # 无效答案, manual置否
            item.update({"manual": False})
        else:
            item.update({"manual": True})
    return answer


class EmptyAnswer:
    ANS_KEYS = ["userAnswer", "rule_result"]
    BAD_TYPES = ("文本Segment Notes-Gain or Loss on Disposal",)

    def __init__(self, mold):
        if isinstance(mold, dict):
            # schema from answer
            self.mold = deepcopy(mold)
            self.checksum = self.mold.get("version")
            if self.checksum:
                self.mold.pop("version")
            else:
                self.checksum = md5json(self.mold)
        else:
            # schema from Mold obj
            self.mold = mold.data
            self.checksum = mold.checksum
        self.schema = Schema(self.mold)
        self.root_schema_name = self.mold["schemas"][0]["name"]
        self.schema_dict = {schema["name"]: schema for schema in self.mold["schemas"]}
        self.schema_type_dict = {schema_type["label"]: schema_type for schema_type in self.mold["schema_types"]}
        self.checksum = getattr(mold, "checksum", None) or md5json(self.mold)
        self.answer_version = str(get_config("prompter.answer_version", "2.2"))
        self.answer = self._generate()

    def _generate(self):
        if self.answer_version == "2.2":
            return self.answer_v_2_2()
        return {}

    @classmethod
    def all_null(cls, other_ans, skip_keys=("rule_result",)):
        if not isinstance(other_ans, dict):
            return True
        for _key in cls.ANS_KEYS:
            if _key in skip_keys:
                continue
            for item in other_ans.get(_key, {}).get("items", []):
                if not is_empty_answer_item(item):
                    return False
        return True

    @classmethod
    def update_manual_tag(cls, answer: dict) -> dict:
        """更新有效答案条目的manual标记"""
        answer = deepcopy(answer)
        for key, value in answer.items():
            if key not in cls.ANS_KEYS:
                continue
            for item in value.get("items", []):
                if is_empty_answer_item(item):
                    # 无效答案, manual置否
                    item.update({"manual": False})
                else:
                    item.update({"manual": True})
        return answer

    @staticmethod
    def _plain_path(key: str) -> str:
        """
        :param key: '["LRs:0","A1:0"]'
        :return: 'LRs-0_A1-0'
        """
        return "_".join([i.replace(":", "-") for i in json.loads(key)])

    def merge(self, other_ans: dict, manual_only: bool = False) -> dict:
        if not other_ans:
            return self.answer
        ret_ans = deepcopy(self.answer)
        for key in self.ANS_KEYS:
            groups = OrderedDict()
            base_items = self.answer[key]["items"]
            other_items = other_ans.get(key, {}).get("items", [])
            for item in base_items:
                groups[self._plain_path(item["key"])] = item
            for item in other_items:
                if manual_only and not item.get("manual"):
                    # 跳过非manual标记的内容
                    continue
                # NOTE: not a necessary check
                # if self.schema.contains_path(item['key']):
                groups[self._plain_path(item["key"])] = item
            ret_ans[key]["items"] = list(groups.values())
        return ret_ans

    def answer_v_2_2(self):
        answer = {}
        # schema
        schema = {
            "schema_types": self.mold.get("schema_types", []),
            "schemas": self.mold.get("schemas", []),
            "version": self.checksum,
        }
        answer.update({"schema": schema})

        # userAnswer & rule_result
        for key in self.ANS_KEYS:
            answer[key] = {"version": "2.2", "items": []}
            for col in self.build_v_2_2(key):
                answer[key]["items"].append(col)
        return answer

    def build_v_2_2(self, key="user_answer"):
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

        def build_col(schema_info, parent_path, index_l):
            schema = build_schema(schema_info)

            path_l = deepcopy(parent_path)
            path_l.append(schema_info["name"])

            return {
                "schema": schema,
                "score": -1,
                "data": [],
                "value": "",
                "key": compact_dumps([":".join([path, idx]) for path, idx in zip(path_l, index_l)]),
            }

        cols = []

        for col_name in self.schema_dict[self.root_schema_name]["orders"]:
            col_attributes = deepcopy(self.schema_dict[self.root_schema_name]["schema"][col_name])
            if col_attributes.get("type") in self.BAD_TYPES:
                continue

            col_attributes.update({"name": col_name})
            col = build_col(col_attributes, [self.root_schema_name], index_l=("0", "0"))
            if key == "rule_result":
                if "(" not in col_name:
                    # 兼容LRs, 去掉带括号的rules
                    col["misc"] = {}
                    cols.append(col)
            elif col_attributes["type"] in MoldSchema.basic_types + list(self.schema_type_dict):  # 基本类型
                cols.append(col)
            elif col_attributes["type"] in self.schema_dict:  # 子类型
                for sub_col_name in self.schema_dict[col_attributes["type"]].get("orders", []):
                    sub_col_attributes = deepcopy(self.schema_dict[col_attributes["type"]]["schema"][sub_col_name])
                    sub_col_attributes.update({"name": sub_col_name})
                    sub_col = build_col(
                        sub_col_attributes, [self.root_schema_name, col_attributes["type"]], ("0", "0", "0")
                    )
                    cols.append(sub_col)
        return cols
