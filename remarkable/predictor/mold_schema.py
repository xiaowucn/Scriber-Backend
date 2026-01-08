# -*- coding: utf-8 -*-
import json
import uuid
from typing import Any, Callable

from remarkable.common.constants import SAFE_SEPARATOR
from remarkable.common.util import compact_dumps


class MoldSchema:
    basic_types = ["文本", "数字", "日期"]

    def __init__(self, schema_data):
        self.schema_data = schema_data
        self._schemas = self.schema_data["schemas"]

        self.schemas = {schema["name"]: schema for schema in self._schemas}
        self.schema_types = self.schema_data["schema_types"]

        root_schema_data = self._schemas[0]
        self.root_schema = SchemaItem(root_schema_data, [root_schema_data["name"]], self)

    @property
    def enum_types(self):
        return [s["label"] for s in self.schema_types]

    @classmethod
    def create(cls, schema_data):
        return MoldSchema(schema_data)

    def is_enum(self, schema_type):
        return schema_type in self.enum_types

    def is_leaf(self, schema_type):
        return schema_type in self.basic_types or self.is_enum(schema_type)

    def get_enum_values(self, schema_type):
        enum_type = self.get_enum_type(schema_type)
        if enum_type is None:
            return None
        return [value["name"] for value in enum_type["values"]]

    def find_schema_by_path(self, schema_path: str | list):
        if isinstance(schema_path, str):
            schema_path = [i.split(":")[0] for i in json.loads(schema_path)][1:]

        current_schema = self.root_schema
        index = 0
        while current_schema.children and index < len(schema_path):
            schema_name = schema_path[index]
            schema = next(i for i in current_schema.children if i.name == schema_name)
            current_schema = schema
            index += 1

        return current_schema

    def get_alias_by_name(self, name: str):
        aliases = []
        nodes = self.root_schema.children

        while name:
            current = None
            for node in nodes:
                prefix = node.name
                if len(name) > len(node.name):
                    prefix += "-"

                if not name.startswith(prefix):
                    continue

                current = node
                if prefix.endswith("-"):
                    name = name[len(prefix) :]
                else:
                    name = ""
                break

            if current is None:
                return None
            else:
                nodes = current.children
                aliases.append(current.alias)

        return SAFE_SEPARATOR.join(aliases)

    def for_each(self, func: Callable[[Any], None], parent_node=None):
        if parent_node is None:
            parent_node = self.root_schema

        if parent_node.level > 1:
            func(parent_node)

        for child in parent_node.children:
            self.for_each(func, child)

    def gen_path_name_alias(self) -> dict[str, str]:
        names = {}

        def _inner(node: "SchemaItem"):
            alias = SAFE_SEPARATOR.join(i.alias for i in node.get_nodes_include_in_path() if i.level > 1)
            path_name = "-".join(node.path[1:])
            names[path_name] = alias

        self.for_each(_inner)

        return names

    def is_enum_schema(self, schema):
        enum_schema_labels = [i["label"] for i in self.schema_types]
        return schema.type in enum_schema_labels

    def get_enum_type(self, schema_type):
        schema_types = (i for i in self.schema_types if i["label"] == schema_type)
        return next(schema_types, None)

    @property
    def basic_schema_labels(self) -> set[str]:
        return {
            label
            for schema in self._schemas[:1]
            for label, item in schema["schema"].items()
            if item["type"] in self.basic_types
        }

    def get_path_mapping(self, schema_items=None):
        # 获取所有key_path和uuid_path映射关系
        key_path_mapping_uuid_path = {}
        schema_items = schema_items or self.root_schema.children
        for schema_item in schema_items:
            if schema_item.is_leaf:
                key_path_mapping_uuid_path[compact_dumps(schema_item.path)] = schema_item.uuid_path
            if schema_item.children:
                key_path_mapping_uuid_path.update(self.get_path_mapping(schema_item.children))
        return key_path_mapping_uuid_path

    def get_all_uuid(self, schema_items=None) -> set[str]:
        # 获取所有uuid
        if schema_items is None:
            schema_items = self.root_schema.children
            uuids = {self.root_schema.uuid}
        else:
            uuids = set()
        for schema_item in schema_items:
            uuids.add(schema_item.uuid)
            if schema_item.children:
                uuids.update(self.get_all_uuid(schema_item.children))
        return uuids

    def get_field_items(self, mid, parent_item=None) -> list[dict[str, Any]]:
        # 获取字段项信息
        if parent_item is None:
            parent_item = self.root_schema
            field_items = [parent_item.to_field(mid)]
        else:
            field_items = []
        for schema_item in parent_item.children:
            field_items.append(schema_item.to_field(mid))
            if schema_item.children:
                field_items.extend(self.get_field_items(mid, schema_item))
        return field_items


class SchemaItem:
    def __init__(self, data: dict, path: list[str], mold_schema: MoldSchema = None, parent: "SchemaItem" = None):
        self.data = data
        self.path = path
        self.mold_schema = mold_schema
        self.parent = parent
        self.children = [self.create_child(name) for name in self.orders] if self.orders else []

    @property
    def name(self):
        return self.path[-1]

    @property
    def orders(self):
        return self.data.get("orders", [])

    @property
    def alias(self) -> str:
        if self.parent is not None:
            return self.parent.data["schema"][self.name].get("alias") or ""
        if alias := self.data.get("alias"):
            return alias
        return ""

    @property
    def schema(self):
        return self.data.get("schema", {})

    @property
    def type(self):
        return self.data.get("type")

    @property
    def regex(self):
        return self.data.get("regex")

    @property
    def level(self):
        return len(self.path)

    def get_nodes_include_in_path(self, oldest_come_first: bool = True):
        current = self

        nodes = [current]
        while current.level > 1:
            parent = current.parent
            nodes.append(parent)
            current = parent

        if oldest_come_first:
            nodes.reverse()

        return nodes

    @property
    def is_leaf(self):
        return self.mold_schema.is_leaf(self.type)

    @property
    def is_enum(self):
        return self.mold_schema.is_enum(self.type)

    @property
    def is_amount(self):
        sub_schema = {c.name for c in self.children}
        if "单位" in sub_schema and any(i in sub_schema for i in ["数值", "金额"]):
            return True
        return False

    @property
    def path_key(self):
        return json.dumps(self.path, ensure_ascii=False)

    @property
    def uuid(self):
        if self.parent and not self.is_leaf and self.name in self.parent.schema:
            if not self.parent.schema[self.name].get("uuid"):
                self.parent.schema[self.name]["uuid"] = uuid.uuid4().hex
            return self.parent.schema[self.name]["uuid"]
        if not self.data.get("uuid"):
            self.data["uuid"] = uuid.uuid4().hex
        return self.data.get("uuid")

    @property
    def uuid_path(self):
        parent_path = self.parent.uuid_path if self.parent else []
        return parent_path + [self.uuid]

    def sibling_path(self, column: str) -> list[str]:
        return sibling_path(self.path, column)

    def create_child(self, name):
        child_path = self.path + [name]
        schema_type = self.schema[name]["type"]
        schemas = self.mold_schema.schemas
        if schema_type in schemas:
            return SchemaItem(schemas[schema_type], child_path, self.mold_schema, parent=self)
        return SchemaItem(self.schema[name], child_path, self.mold_schema, parent=self)

    def to_answer_data(self):
        data = self.to_data()
        return {"data": data}

    def to_data(self):
        return {
            "type": self.data.get("type") or self.data.get("name"),
            "label": self.name,
            "words": self.data.get("words", ""),
            "multi": self.data.get("multi"),
            "required": self.data.get("required"),
            "description": self.data.get("description"),
            "extract_type": self.data.get("extract_type"),
        }

    def to_field(self, mid: int):
        return {
            "type": self.data.get("type") or self.data.get("name"),
            "words": self.data.get("words", ""),
            "multi": self.data.get("multi"),
            "required": self.data.get("required"),
            "description": self.data.get("description"),
            "alias": self.alias,
            "parent": self.parent.uuid if self.parent else None,
            "uuid": self.uuid,
            "mid": mid,
            "is_leaf": self.is_leaf,
        }

    def __str__(self):
        return f"SchemaItem<{self.name}>"


def sibling_path(path: list[str], column: str) -> list[str]:
    if not path:
        return [column]
    return path[:-1] + [column]
