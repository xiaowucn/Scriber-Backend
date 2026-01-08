import csv
import io
import logging
import re
from collections import defaultdict
from copy import deepcopy
from difflib import SequenceMatcher
from functools import reduce
from pathlib import Path
from typing import Callable, DefaultDict

from remarkable.answer.common import full_path, get_mold_name, parse_path
from remarkable.answer.node import AnswerNode
from remarkable.answer.reader import AnswerReader
from remarkable.common.util import clean_txt, import_class_by_path
from remarkable.converter.utils import DataPack, flatten_dict
from remarkable.plugins.sse.sse_answer_formatter import AnswerItem
from remarkable.plugins.zjh.util import transfer_unit

p_unit_dimension = re.compile(r"((?<=\d)[倍次人件]|次/年)$")
p_amount = re.compile(r"\d+\s*[万千亿]?美?[元股]$")
p_amount_field = re.compile(r"[元股]）?$|股份$")


class AnswerWorkShop:
    def __init__(self, metadata: DataPack, debug=False):
        self.file = metadata.file
        self.question = metadata.question
        self.project = metadata.project
        self.answer = metadata.answer
        self._debug = debug

    async def work(self):
        raise NotImplementedError


def make_answer_node(answer: dict) -> AnswerNode | None:
    if not answer["userAnswer"]["items"]:
        return None
    root_node, _ = AnswerReader(answer).build_answer_tree()
    mold_name = get_mold_name(answer)
    return root_node[(mold_name, 0)]


class BaseConverter:
    def __init__(self, answer):
        self._raw_answer = deepcopy(answer)
        self.answer_node: AnswerNode = make_answer_node(answer)
        self.mold_name = get_mold_name(answer)

    def convert(self, *args, **kwargs):
        answer = {}
        logging.info(f'No need to convert this: "{self.mold_name}", use origin answer structure')
        if self.answer_node:
            answer = self.answer_node.to_dict(item_handler=lambda n: n.plain_text)
        return answer

    @staticmethod
    def convert_enum_value(text: str, convert_map=None) -> str:
        if convert_map is None:
            convert_map = {"是": "1", "否": "0"}
        return convert_map.get(text, text)

    @staticmethod
    def update_text_in_answer(answer_item, func, **kwargs):
        if not isinstance(answer_item, AnswerItem) or not answer_item.plain_text:
            return AnswerItem([])
        new_item = deepcopy(answer_item)
        text = new_item.plain_text
        new_item.plain_text = func(text, **kwargs)
        return new_item

    @staticmethod
    def get_most_likely_key(key, ref_keys):
        return sorted(ref_keys, key=lambda x: SequenceMatcher(None, key, x).ratio())[-1]

    @staticmethod
    def combine_sub_items(answer: dict[int, dict[str, AnswerItem]], kv_fmt=True, paths: list[str] = None) -> AnswerItem:
        """拼接下级答案到上级"""
        if isinstance(answer, AnswerItem):
            logging.warning("Unexpected type detected, please check your answer")
            return answer
        res = AnswerItem([])
        for item in deepcopy(answer).values():
            for key in item:
                if item[key].is_empty:
                    continue
                if kv_fmt:
                    item[key].plain_text = f"{key}: {item[key].plain_text}"
            res = res + reduce(
                lambda x, y: x + y, [item[k] for k in item.keys() if not item[k].is_empty and (not paths or k in paths)]
            )
        res.plain_text = res.plain_text.strip()
        return res

    @staticmethod
    def fake_sub_items(answer, paths):
        res = {0: {}}
        for path in paths:
            res[0].setdefault(path, answer[path])
        return res


class NullConverter(BaseConverter):
    """暂未实现的转换类可以继承本类"""

    def convert(self, *args, **kwargs):
        logging.warning(f'No converter for schema: "{self.mold_name}" yet, will return None.')


class ConverterMaker:
    @classmethod
    def get_dir_packages(cls, dir_path: Path) -> list[str]:
        packages = set()
        for path in dir_path.glob("*_conv.*"):
            if path.is_file() and path.suffix.lower() in (".py", ".pyc", ".so"):
                packages.add(path.name.rstrip(path.suffix))
        return list(packages)

    @classmethod
    def load_converter(cls, module_path: str, dir_path: Path, cls_name: str) -> type:
        for package in cls.get_dir_packages(dir_path):
            clazz = import_class_by_path(f"{module_path}.{package}.{cls_name}")
            if clazz:
                return clazz
        logging.warning(f'Converter: "{cls_name}" not found in current module path: "{module_path}"')
        return NullConverter


class SSEBaseConverter(BaseConverter):
    def __init__(self, answer):
        super().__init__(answer)
        self.answer_in = self.fill_with_ans_item(self.answer_node)

    @classmethod
    def fill_with_ans_item(cls, answer):
        if isinstance(answer, AnswerNode):
            answer = answer.to_formatter_dict()
        for key, value in answer.items():
            if not isinstance(value, AnswerItem) and isinstance(value, dict):
                # NOTE: 三级"金额"&"单位"合并, 拉到二级
                if len(value) == 1 and 0 in value and "金额" in value[0] and "单位" in value[0]:
                    answer[key] = value[0]["金额"] + value[0]["单位"]
                    answer[key].plain_text = clean_txt(answer[key].plain_text)
                else:
                    cls.fill_with_ans_item(value)
        return answer


class SZSEBaseConverter(BaseConverter):
    @staticmethod
    def is_amount_node(node):
        if not isinstance(node, dict):
            return False

        node_keys = set(node.keys())
        for item in ({"金额", "单位"}, {"数值", "单位", "币种"}):
            if len(node_keys.intersection(item)) > 1:
                return True
        return False

    @staticmethod
    def get_to_unit(field):
        if not field:
            return ""
        if any(x in field for x in ["应收账款周转率（次）", "存货周转率（次）"]):
            return ""
        if any(
            x in field for x in ["每股净资产", "每股经营活动现金流量", "每股净现金流量", "基本每股收益", "稀释每股收益"]
        ):
            return "元"
        if any(
            x in field
            for x in [
                "持股数量",
                "国有股东持有股份",
                "境内民营机构或自然人持有股份",
                "境外股东持有股份",
                "其他股份",
                "合计股份",
            ]
        ):
            return "万股"
        return "万元"

    def convert_currency_unit(self, field, data):
        if not data:
            return data
        if "text" not in data:
            if isinstance(data, dict):
                for key, val in data.items():
                    self.convert_currency_unit(key, val)
            else:  # data is instance of list
                for index, val in enumerate(data):
                    self.convert_currency_unit(index, val)
        else:
            text = data["text"]
            if not text:
                return data
            if p_unit_dimension.search(text):
                text = p_unit_dimension.sub("", text)
                data["text"] = text
            elif p_amount.search(text) or p_amount_field.search(field):
                to_unit = self.get_to_unit(field)
                success, val = transfer_unit(text, to_unit=to_unit)
                if success:
                    data["text"] = val
                else:
                    data["text"] = ""

        return data


class SimpleJSONConverter(BaseConverter):
    def __init__(self, answer):
        super().__init__(answer)
        self._custom_answer = defaultdict(list)

    @property
    def custom_answer(self) -> defaultdict[str, list[AnswerItem]]:
        if not self._custom_answer:
            for item in self._raw_answer.get("custom_field", {}).get("items", []):
                self._custom_answer[self.get_parent_path(item["key"])].append(AnswerItem(**item))
        return self._custom_answer

    def convert(self, *args, **kwargs):
        item_handler = kwargs.pop("item_handler", lambda x: x.plain_text)
        answer = {}
        if self.answer_node:
            answer = self.answer_node.to_dict(item_handler=item_handler, custom_answer=self.custom_answer)
        return self.fill_the_rest_answer(answer, item_handler=item_handler)

    def to_csv(self, sep="-", format_func=None, keep_index=False):
        if not format_func:
            format_func = self.csv_plain_text
        with io.StringIO() as csv_f:
            writer = csv.writer(csv_f)
            for key, value in flatten_dict(self.convert(item_handler=format_func), sep=sep, keep_index=keep_index):
                writer.writerow([key, value])
            return csv_f.getvalue().encode("utf-8-sig")

    @staticmethod
    def csv_plain_text(answer):
        text = answer.simple_text(clear=False)
        if isinstance(text, list):
            text = "\n".join(text)
        text = text.replace("\r", "\n") if text else ""
        return text

    @staticmethod
    def cgs_csv_text(enum_types, answer):
        text = answer.simple_text(clear=False, enum=False)
        if isinstance(text, list):
            text = "\n".join(text)
        text = text.replace("\r", "\n") if text else ""

        if answer["schema"]["data"]["type"] in enum_types:
            return "&&".join(answer.value) + "|" + text

        return text

    @staticmethod
    def get_parent_path(key):
        # '["资产管理合同:0","集合计划的募集:0","测试字段2:0"]' -> '资产管理合同:0_集合计划的募集:0'
        return full_path(parse_path(key)[:-1])

    def fill_the_rest_answer(self, answer, item_handler: Callable):
        def _insert(ans, item, keys=None):
            # 尝试按schema非叶子节点答案顺序填充自定义字段, 成功返回真, 失败返回假
            # 同级schema字段排在先, 自定义字段排在后
            key, *others = keys if keys else [p[0] for p in parse_path(item.key)[1:]]
            if isinstance(ans, list):
                for _ans in ans:
                    if _insert(_ans, item, others):
                        return True
                return False
            if key not in ans:
                ans["_".join((others or [key]) + ["自定义"])] = item_handler(item)
                return True
            if not others:
                ans[key].append({f"{key}_自定义": item_handler(item)})
                return True
            if len(others) == 1:
                ans[key].append({f"{others[0]}_自定义": item_handler(item)})
                return True
            return _insert(ans[key], item, others)

        # 填充剩余的自定义字段
        for item in [i for items in self.custom_answer.values() for i in items]:
            _insert(answer, item)
        # 清空自定义答案缓存
        self._custom_answer = defaultdict(list)
        return answer
