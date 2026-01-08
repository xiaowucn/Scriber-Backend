import logging
from functools import partial

from remarkable.answer.common import dump_key, name_path, parse_path
from remarkable.answer.node import AnswerItem, AnswerNode, simple_json_v2
from remarkable.common.constants import JSONConverterStyle
from remarkable.common.util import box_to_outline

logger = logging.getLogger(__name__)


class AnswerReader:
    def __init__(self, answer):
        self.answer = answer
        self.schema_dict = {s["name"]: s for s in self.answer["schema"]["schemas"]}
        self.enum_dict = {s["label"]: s for s in self.answer["schema"]["schema_types"]}
        # set "is_leaf" to schema column
        for _schema in self.answer["schema"]["schemas"]:
            for col_define in _schema["schema"].values():
                col_define["is_leaf"] = col_define["type"] not in self.schema_dict
        self._tree, self._mapping = self.build_answer_tree()

    @property
    def main_schema(self):
        return self.answer["schema"]["schemas"][0]

    @property
    def mold_name(self):
        return self.main_schema["name"]

    @property
    def items(self):
        return self.answer["userAnswer"]["items"]

    @property
    def custom_field(self):
        return self.answer.get("custom_field", {}).get("items", [])

    @property
    def version(self):
        return self.answer["userAnswer"]["version"]

    def __getitem__(self, key):
        return self.answer.get(key)

    def create_node(self, path, parent=None):
        _col_type = None
        # for the root sentinel node
        _schema = {
            "name": "sentinel",
            "orders": [self.main_schema["name"]],
            "schema": {
                self.main_schema["name"]: {
                    "type": self.main_schema["name"],
                    "multi": True,
                    "required": False,
                    "is_leaf": False,
                }
            },
        }
        for _col, _ in path:
            _col_type = _schema["schema"][_col]["type"]
            _schema = self.schema_dict.get(_col_type)
        return AnswerNode(path, _schema, parent=parent)

    def build_answer_tree(self):
        # _root = self.create_node([], self.main_schema["name"])
        _root = self.create_node([])
        _mapping = {}
        for item in self.items:
            _node = _root
            _key_path = []
            for key in parse_path(item["key"]):
                _key_path.append(key)
                if key not in _node:
                    _node[key] = self.create_node(_key_path, parent=_node)
                _node = _node[key]
                _mapping.setdefault(name_path(_node.path), set()).add(_node)
            _node.data = AnswerItem(**item)
        return _root, _mapping

    def find_nodes(self, path: list[str]) -> set[AnswerNode]:
        """根据 path 获取所有答案节点
        要求 path 从 level1 开始（不包含 schema 名称）
        """
        return self._mapping.get("_".join(path), [])

    def to_tile_dict(self, include_custom=False):
        """输出以key_path为索引的字段"""
        res = {}
        items = self.items
        if include_custom:
            items += self.custom_field
        for item in self.items:
            key_path = dump_key(item["key"])
            res[key_path] = item
        return res

    def to_json(self, style: int = JSONConverterStyle.ORIGIN, item_handler: callable = None):
        from remarkable.converter import SimpleJSONConverter

        if style == JSONConverterStyle.ORIGIN:
            return self.answer

        data = {}
        if style == JSONConverterStyle.PLAIN_TEXT:
            data = SimpleJSONConverter(self.answer).convert(item_handler=item_handler or (lambda x: x.plain_text))
        elif style == JSONConverterStyle.ENUM:
            assert isinstance(self.answer, dict) and "schema" in self.answer, "Invalid answer data"
            enum_types = {s["label"] for s in self.answer["schema"]["schema_types"]}
            data = SimpleJSONConverter(self.answer).convert(item_handler=partial(simple_json_v2, enum_types))
        return data

    def to_csv(self):
        from remarkable.converter import SimpleJSONConverter

        return SimpleJSONConverter(self.answer).to_csv()

    def dump_answer_items(self) -> list[dict]:
        """
        从answer_reader重新生成标注答案里的["userAnswer"]["items"]
        :return:
        """
        return self._tree.to_answer_items()

    @staticmethod
    def add_element_index(answer_data, pdfinsight_reader):
        for item in answer_data.get("userAnswer", {}).get("items", []):
            for label_data in item.get("data", []):
                for box_info in label_data.get("boxes"):
                    page = box_info["page"]
                    box = box_info["box"]
                    outline = box_to_outline(box)
                    elements = pdfinsight_reader.find_elements_by_outline(page, outline)
                    if elements:
                        box_info["element_index"] = [
                            element[1].get("index") for element in elements if element[1].get("index")
                        ]
                    else:
                        logger.error("can't find element by page %s, outline %s", page, outline)
                        box_info["element_index"] = []
        return answer_data


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


class MasterAnswerReader(AnswerReader):
    def build_answer_tree(self):
        # _root = self.create_node([], self.main_schema["name"])
        _root = self.create_node([])
        _mapping = {}
        for item in self.items:
            _node = _root
            _key_path = []
            for key in parse_path(item["master_key"]):
                _key_path.append(key)
                if key not in _node:
                    _node[key] = self.create_node(_key_path, parent=_node)
                _node = _node[key]
                _mapping.setdefault(name_path(_node.path), set()).add(_node)
            _node.data = AnswerItem(**item)
        return _root, _mapping


def load_scriber_answer(answer):
    """BACKWARD COMPATIBLE
    读取标注答案，转换为树形结构
    非叶子节点均为 [{}] 结构，实际的是一个 OrderedDict，并且此方法输出时保证按 key 排序
    叶子节点为 None、Str 或 值类型
    例:
    {
        "科创板招股说明书信息抽取": {
            "扉页-发行概况": {
                0: {
                    "(表格)": None,
                    "发行股票类型": 对应的标注答案 item
                    ...
                },
            }
        }
    }
    """
    reader = AnswerReader(answer)
    root_node, _ = reader.build_answer_tree()
    answer_dict = root_node.to_formatter_dict()
    root_key = list(answer_dict.keys())[0]
    root_items = answer_dict[root_key]
    return {root_key: root_items[0] if root_items else {}}


def dump_scriber_answer(answer_tree):
    """
    load_scriber_answer的逆向操作
    :param answer_tree:
    :return:
    """

    def dump_dict(_dict):
        items = []
        for data in _dict.values():
            if not data:
                continue
            if isinstance(data, AnswerItem):
                items.append(data.to_dict())
            elif isinstance(data, dict):
                items.extend(dump_dict(data))
            else:
                raise Exception("Error in dump_scriber_answer")
        return items

    return dump_dict(answer_tree)
