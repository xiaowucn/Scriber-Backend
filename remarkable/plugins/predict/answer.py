from collections import defaultdict
from itertools import chain

from remarkable.answer.common import full_path, name_path, parse_path
from remarkable.answer.node import AnswerItem


class AnswerNode:
    """答案树节点
    node["子公司基本情况", 1]  # 索引为 (name, idx) 形式，返回下级节点 AnswerNode
    node["子公司基本情况"]  # 索引为 name，返回节点分支 {0: AnswerNode, 1: AnswerNode, ...}
    node.data  # 叶子节点保存答案内容
    """

    def __init__(self, path, parent=None):
        self.path = path
        self._branches = {}  # {name: {idx: sub_node}}
        self.data = None
        self.parent = parent

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

        _branch = self._branches.get(_name)
        if _name not in self._branches:
            raise Exception("can't find branch: %s" % _name)

        if _idx is None:
            return _branch

        _node = _branch.get(_idx)
        if _idx not in _branch:
            raise Exception("can't find node: %s:%s" % (_name, _idx))
        return _node

    def __setitem__(self, key, val):
        _name, _idx = self.revise_key(key, allow_none_idx=False)
        _branch = self._branches.setdefault(_name, {})
        _node = _branch.setdefault(_idx, AnswerNode(self.path + [key], parent=self))
        _node.data = val

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
        return not self._branches

    def find_by_path(self, path):
        _node = self
        for key in path:
            _node = _node[key]
        return _node

    def descendants(self, only_leaf=False):
        for _, item in self.items():
            if not only_leaf or item.isleaf():
                yield item
            if not item.isleaf():
                yield from item.descendants(only_leaf=only_leaf)


class AnswerReader:
    def __init__(self, answer: dict | None):
        self.answer = answer if isinstance(answer, dict) else {}
        self._tree, self._mapping = self.build_answer_tree()

    @property
    def main_schema(self):
        return self.answer["schema"]["schemas"][0]

    @property
    def items(self):
        return self.answer.get("userAnswer", {}).get("items", [])

    @property
    def is_empty(self):
        return not bool(self.items)

    @property
    def version(self):
        return self.answer["userAnswer"]["version"]

    def __getitem__(self, key):
        return self.answer.get(key)

    def build_answer_tree(self):
        _root = AnswerNode([])
        _mapping = defaultdict(dict)
        for item in self.items:
            _node, _idx = _root, 0
            for _name, _idx in parse_path(item["key"]):
                _node = _node.setdefault((_name, _idx), None)
                _mapping[name_path(_node.path)].update({_node: ""})
            _node.data = AnswerItem(**item)
        for key, value in _mapping.items():
            _mapping[key] = list(value.keys())
        return _root, _mapping

    def find_nodes(self, path: list[str]) -> set[AnswerNode]:
        """根据 path 获取所有答案节点
        要求 path 从 level1 开始（不包含 schema 名称）
        """
        return self._mapping.get("_".join(path), [])


def iterate_answer_items(items, level=3):
    for item in items:
        if level == 1:
            yield item
            continue
        for data in item["data"]:
            if level == 2:
                yield (item, data)
                continue
            for box in data["boxes"]:
                if level == 3:
                    yield (item, data, box)
                    continue
