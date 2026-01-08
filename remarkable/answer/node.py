"""定义答案树结构
AnswerNode {
    "path": [("根节点", 0), ("分支节点", 0), ..., ("叶子节点", 0)],
    "data": AnswerItem or None,  # 叶子节点 data 为 AnswerItem
    "_branches": {
        "column1": {
            idx1: AnswerNode,
            ...
        },
        ...
    }
}
"""

import json
import re
from collections import OrderedDict, defaultdict
from copy import deepcopy
from functools import cached_property
from itertools import chain

from remarkable.answer.common import full_path, gen_key_md5, get_first_level_field, name_path, parse_path
from remarkable.common.util import compact_dumps


class AnswerItem(dict):
    _plain_text = None
    _origin_text = None
    __columns__ = [
        "data",
        "value",
        "text",
        "score",
        "key",
        "manual",
        "schema",
        "marker",
        "_migrated",
        "meta",
        "custom",
        "md5",
    ]

    def __init__(
        self,
        data=None,
        value=None,
        text=None,
        score=None,
        key=None,
        manual=None,
        schema=None,
        marker=None,
        _migrated=False,
        meta=None,
        item=None,
        custom=False,
        md5=None,
        **kwargs,
    ):
        if not item:
            item = {
                "data": data,
                "value": value,
                "text": text,
                "score": score,
                "key": key,
                "manual": manual,
                "schema": schema,
                "marker": marker,
                "_migrated": _migrated,
                "meta": meta,
                "custom": custom,
                "md5": md5,
            }
            item["md5"] = gen_key_md5(item) if key else None
            item["kwargs"] = kwargs
        if item.get("data") is None:
            item["data"] = []

        super().__init__(item)

    def __getattr__(self, key):
        if key in self.__columns__:
            return self.get(key)
        raise AttributeError()

    def __setattr__(self, key, value):
        if key in self.__columns__:
            return self.update({key: value})
        return super().__setattr__(key, value)

    def simple_text(self, clear=True, enum=True):
        """默认，直接输出 text"""
        if not (self.data or self.value or self.text):
            return None

        texts = []
        if enum and self.value:
            texts.append(self.value)
        else:
            if hasattr(self, "text") and self.text:
                texts.append(self.text)
            if not texts:
                texts = self.get_data_texts()

        if clear:
            texts = [
                re.sub(r"[\n\r]", "", each) if isinstance(each, str) else [re.sub(r"[\n\r]", "", x) for x in each]
                for each in texts
            ]
        return texts[0] if len(texts) == 1 else texts

    def get_data_texts(self) -> list[str]:
        texts = []
        for data in self.data:
            if isinstance(data, str):
                _text = data
            else:
                _text = data["text"] if data.get("text") else "".join([box["text"] for box in data.get("boxes", [])])
            texts.append(_text)
        return texts

    @property
    def raw_text(self):
        return "".join(self.get_data_texts())

    @property
    def plain_text(self) -> str:
        if self._plain_text is None:
            text = self.simple_text()
            if isinstance(text, list):
                text = "\n".join(text)
            self._plain_text = text or ""
        return self._plain_text

    @plain_text.setter
    def plain_text(self, value):
        self._plain_text = value

    @property
    def origin_text(self) -> str:
        if self._origin_text is None:
            text = self.simple_text(clear=False)
            if isinstance(text, list):
                text = "\n".join(text)
            self._origin_text = text or ""
        return self._origin_text

    @origin_text.setter
    def origin_text(self, value):
        self._origin_text = value

    def __add__(self, other):
        if not isinstance(other, AnswerItem):
            return deepcopy(self)
        new_item = AnswerItem([])
        new_item.data = ([] if not self.data else self.data) + ([] if not other.data else other.data)
        new_item.score = max(
            1.0 if self.score is None else float(self.score), 1.0 if other.score is None else float(other.score)
        )
        new_item.value = ("" if self.value is None else str(self.value)) + (
            "" if self.value is None else str(self.value)
        )
        new_item.plain_text = (f"{self.plain_text}\n" if self.plain_text else "") + other.plain_text
        return new_item

    @property
    def is_empty(self):
        return not (self.data or self.text or self.value or self.plain_text)

    @property
    def key_indices(self):
        key = json.loads(self.key)
        indices = [int(item.split(":")[-1]) for item in key]
        return indices

    @property
    def namepath(self):
        return name_path(parse_path(self.key))

    @property
    def first_level_field(self):
        return get_first_level_field(self.key)

    @cached_property
    def compact_key(self):
        return compact_dumps(json.loads(self.key))

    def to_dict(self):
        return {
            "id": self["kwargs"].get("id"),
            "qid": self["kwargs"].get("qid"),
            "data": self.data,
            "value": self.value,
            "text": self.text,
            "score": self.score,
            "key": self.key,
            "manual": self.manual,
            "schema": self.schema,
            "marker": self.marker,
            "_migrated": self._migrated,
            "meta": self.meta,
            "custom": self.custom,
        }


def simple_json_v2(enum_types: set[str], item: AnswerItem):
    """
    return: {
        "choices": [
            "ch1",
            "ch2",
            ...
        ],
        "text": "text",
    }
    """
    text = item.simple_text(enum=False)
    if text and isinstance(text, list):
        text = "\n".join(text)

    ret = {"text": text or None}
    if item.schema.get("data", {}).get("type") in enum_types:
        ret["choices"] = []

    if not item or not (item.data or item.value or item.text):
        return ret

    if "choices" in ret and item.value:
        if isinstance(item.value, list):
            ret["choices"].extend(item.value)
        elif isinstance(item.value, str):
            ret["choices"].append(item.value)
        else:
            raise TypeError(f"Unexpected type of value: {item.value}")
    return ret


class AnswerNode:
    """答案树节点
    node["子公司基本情况", 1]  # 索引为 (name, idx) 形式，返回下级节点 AnswerNode
    node["子公司基本情况"]  # 索引为 name，返回节点分支 {0: AnswerNode, 1: AnswerNode, ...}
    node.data  # 叶子节点保存答案内容
    """

    def __init__(self, path, schema=None, parent=None):
        self.parent = parent
        self.path = deepcopy(path)
        self._branches = None  # {name: {idx: sub_node}}
        self.data = None
        self.schema = schema
        if schema:
            # 初始化非叶子节点
            self._branches = {name: {} for name in schema["schema"]}
        else:
            # 初始化叶子节点
            self.data = AnswerItem()

    @property
    def name(self):
        if not self.path:
            return None
        return self.path[-1][0]

    @property
    def idx(self):
        if not self.path:
            return None
        return self.path[-1][1]

    @property
    def fullpath(self):
        return full_path(self.path)

    @property
    def namepath(self):
        return name_path(self.path)

    @property
    def relative_element_indexes(self):
        return chain(*[data["elements"] for data in self.data["data"]])

    @staticmethod
    def revise_key(key, allow_none_idx=True):
        """format: (str, int/None)"""
        _name, _idx = None, None
        if isinstance(key, tuple):
            _name, _idx = key
        else:
            _name = key

        if not isinstance(_name, str):
            raise Exception("key name is not string")

        if not isinstance(_idx, int):
            if not (_idx is None and allow_none_idx):
                raise Exception("key index is not int")
        return (_name, _idx)

    def __getitem__(self, key):
        _name, _idx = self.revise_key(key)

        if _name not in self._branches:
            raise Exception("can't find branch: %s" % _name)
        _branch = self._branches.get(_name)

        if _idx is None:
            return _branch

        _node = _branch.get(_idx)
        if _idx not in _branch:
            raise Exception("can't find node: %s:%s" % (_name, _idx))
        return _node

    def __setitem__(self, key, val):
        _name, _idx = self.revise_key(key, allow_none_idx=False)
        _branch = self._branches[_name]
        _branch[_idx] = val

    def __contains__(self, key):
        _name, _idx = self.revise_key(key)
        if _name not in self._branches:
            return False
        if _idx is not None and _idx not in self._branches[_name]:
            return False
        return True

    def __len__(self):
        return len(self._branches)

    def keys(self):
        return self._branches.keys()

    def items(self):
        for name, branch in self.branches():
            for idx, item in branch.items():
                yield (name, idx), item

    def branches(self):
        return self._branches.items()

    def setdefault(self, key, defaultval):
        if key not in self:
            self[key] = defaultval
        return self[key]

    def get(self, key, defaultval):
        if key not in self:
            return defaultval
        return self[key]

    def isleaf(self):
        return not self.schema

    def find_by_path(self, path):
        _node = self
        for key in path:
            _node = _node[key]
        return _node

    def descendants(self, only_leaf=False, filter_empty=True):
        for _, item in self.items():
            if item.isleaf():
                if not filter_empty or item.data:
                    yield item
            else:
                if not only_leaf:
                    if not filter_empty or item.branches():
                        yield item
                yield from item.descendants(only_leaf=only_leaf, filter_empty=filter_empty)

    def to_dict(self, item_handler=None, custom_answer: defaultdict[str, list[AnswerItem]] | None = None):
        """输出字典"""
        res = {}
        if custom_answer is None:
            custom_answer = defaultdict(list)
        for col, items in self.branches():
            col_define = self.schema["schema"][col]
            if not col_define["is_leaf"]:
                res[col] = []
                for _, node in sorted(items.items(), key=lambda i: i[0]):
                    # 填充自定义字段
                    cst_ans = {
                        parse_path(i.key)[-1][0] + "_自定义": item_handler(i) if item_handler else i
                        for i in custom_answer.pop(node.fullpath, [])
                    }
                    res[col].append({**node.to_dict(item_handler=item_handler, custom_answer=custom_answer), **cst_ans})
            else:
                if not items:
                    res[col] = None
                else:
                    # 叶子节点只有一个 item
                    if item_handler:
                        res[col] = item_handler(items[0].data)
                    else:
                        res[col] = items[0].data
        return res

    def to_formatter_dict(self):
        """BACKWARD COMPATIBLE: 输出专为 answer formatter 适配的字典格式"""
        res = {}
        for col, items in self.branches():
            col_define = self.schema["schema"][col]
            if not col_define["is_leaf"]:
                res[col] = OrderedDict()
                for idx, node in items.items():
                    res[col][idx] = node.to_formatter_dict()
            else:
                if not items:
                    # 缺省为一个空 AnswerItem
                    res[col] = AnswerItem(key=compact_dumps([f"{k}:{i}" for k, i in self.path + [(col, 0)]]))
                else:
                    # 叶子节点只有一个 item
                    res[col] = items[0].data
        return res

    def to_answer_items(self) -> list[dict]:
        return [x.data.to_dict() for x in self.descendants(only_leaf=True)]
