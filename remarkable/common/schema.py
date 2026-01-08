import json
import logging
import re
from collections import defaultdict
from copy import deepcopy
from hashlib import md5

from remarkable.common.exceptions import InvalidMoldError
from remarkable.config import get_config
from remarkable.predictor.mold_schema import MoldSchema


class Schema:
    invalid_field_name_patterns = {
        "字段首尾不允许有空格": re.compile(r"^\s+|\s+$"),
        "字段不允许包含/|.&": re.compile(r"[/|.&]"),
    }

    def __init__(self, mold):
        self.mold = mold
        self.md5_mapping = None
        self.path_set = None
        self.schemas = self.mold["schemas"]
        self.schema_dict = {schema["name"]: schema for schema in self.schemas}
        self.enum_dict = {s["label"]: s for s in self.mold.get("schema_types")}
        self.enum_types = list(self.enum_dict.keys())

    @classmethod
    def validate(cls, new_mold, old_mold=None):
        # TODO: 白名单&枚举类型字段校验
        old_one = cls(old_mold) if old_mold else None
        new_mold = cls(new_mold)
        new_mold.iter_hierarchy_check()

        for path in new_mold.iter_schema_attr():
            if old_one and old_one.contains_path(path)[0]:
                # 旧字段不做校验
                continue
            path_len = len(path)
            if path_len > 4:
                raise InvalidMoldError(f"字段层级超限, 请检查: {path}")
            if len(set(path)) != path_len:
                raise InvalidMoldError(f"发现重复字段, 请检查: {path}")
            for item in path:
                cls.is_valid_filed_name(item)
        for name in (s["name"] for s in new_mold.schemas):
            cls.is_valid_filed_name(name)

    @classmethod
    def is_valid_filed_name(cls, name):
        for reason, pattern in cls.invalid_field_name_patterns.items():
            if pattern.search(name):
                raise InvalidMoldError(f"{reason}, 请检查: {name}")

    @classmethod
    def join_path(cls, parent, name):
        path = deepcopy(parent)
        path.append(name)
        return path

    @classmethod
    def path_md5(cls, path):
        path_str = "[{}]".format(",".join(['"{}"'.format(p) for p in path]))
        return md5(path_str.encode("utf8"))

    def find_attr_type(self, path):
        def _iter(schema, path):
            _name = path.pop(0)
            _definition = schema["schema"].get(_name)
            if not _definition:
                raise Exception("can't find definition of %s", _name)
            _type = _definition["type"]
            if _type in MoldSchema.basic_types:
                if path:
                    raise Exception("col %s is simple type", _name)
                return _type
            if _type in self.enum_dict:
                if path:
                    raise Exception("col %s is enum type", _name)
                return self.enum_dict[_type]
            if _type in self.schema_dict:
                sub_schema = self.schema_dict[_type]
                return _iter(sub_schema, path) if path else sub_schema
            raise Exception("can't find type definition of %s", _type)

        return _iter(self.schemas[0], deepcopy(path))

    def iter_schema_attr(self, need_detail=False):
        def iter_schema(path, schema, field_name):
            path = Schema.join_path(path, field_name)
            if not schema["schema"]:
                if need_detail:
                    yield path, {}
                else:
                    yield path
            simple_types = MoldSchema.basic_types + list(self.enum_dict.keys())
            for name, item in sorted(
                schema["schema"].items(),
                key=lambda x: schema["orders"].index(x[0]),
            ):
                if item["type"] in simple_types:
                    if not need_detail:
                        yield Schema.join_path(path, name)
                    else:
                        yield Schema.join_path(path, name), item
                elif item["type"] in self.schema_dict:
                    yield from iter_schema(path, self.schema_dict[item["type"]], name)
                else:
                    logging.error("unknown type %s", item["type"])

        yield from iter_schema([], self.schemas[0], self.schemas[0]["name"])

    def iter_hierarchy(self):
        """按层级遍历 schema
        for attr in this_iter:
            return attr_path, sub_iter
        """

        def _iter(path, schema, field_name):
            path = Schema.join_path(path, field_name)
            simple_types = MoldSchema.basic_types + list(self.enum_dict.keys())
            for name in schema.get("orders", []):
                # 按顺序取schema
                item = schema["schema"][name]
                attr_path = Schema.join_path(path, name)
                if item["type"] in simple_types:
                    sub_iter = None
                elif item["type"] in self.schema_dict:
                    sub_iter = _iter(path, self.schema_dict[item["type"]], name)
                else:
                    sub_iter = None
                    logging.error("unknown type %s", item["type"])
                yield attr_path, sub_iter

        yield from _iter([], self.schemas[0], self.schemas[0]["name"])

    def iter_hierarchy_check(self):
        """按层级遍历 schema 做检查
        for attr in this_iter:
            return attr_path, sub_iter
        """

        def _iter(path, schema, field_name):
            path = Schema.join_path(path, field_name)
            for name in schema.get("orders", []):
                # 按顺序取schema
                item = schema["schema"][name]
                if item["type"] in MoldSchema.basic_types:
                    if item["multi"] and not get_config("feature.basic_field_multi"):
                        raise InvalidMoldError(f"{name}为{item['type']}字段, 不支持标注多项")

                elif item["type"] in self.schema_dict:
                    _iter(path, self.schema_dict[item["type"]], name)

                if item.get("regex"):
                    try:
                        re.compile(item["regex"])
                    except (TypeError, re.error) as e:
                        raise InvalidMoldError(f"{name}字段的正则表达式存在语法错误") from e

        _iter([], self.schemas[0], self.schemas[0]["name"])

    # NOTE: return the path without field name
    def find_path_by_md5(self, _md5):
        if self.md5_mapping is None:
            self.md5_mapping = {}
            for key_path in self.iter_schema_attr():
                if len(key_path) <= 2:
                    key_path_md5 = Schema.path_md5(key_path)
                else:
                    key_path_md5 = Schema.path_md5(key_path[:-1])
                if key_path_md5 not in self.md5_mapping:
                    self.md5_mapping[key_path_md5] = key_path[:-1]

        return self.md5_mapping.get(_md5)

    def contains_path(self, path, skip_root=False):
        start = 1 if skip_root else 0
        if self.path_set is None:
            self.path_set = {"_".join(key_path[start:]) for key_path in self.iter_schema_attr()}

        if isinstance(path, str):
            if '"' in path:
                path = json.loads(path)
            else:
                path_str = path
        key = path
        if isinstance(path, list):
            if skip_root:
                # 仅仅是改schema名字的情况，尽可能保留标注答案
                key = json.dumps([f"{self.schemas[0]['name']}:0"] + path[1:], ensure_ascii=False)
            path_str = "_".join([x[0] for x in [p.split(":") for p in path[start:]]])
        return path_str in self.path_set, key

    def validate_meta(self, meta):
        all_validate_keys = set()
        all_validate_keys.add(self.mold["schemas"][0]["name"])

        def stat_validate_keys(sub_schema_iter):
            for col_path, sub_iter in sub_schema_iter:
                all_validate_keys.add("|".join(col_path))
                if sub_iter:
                    stat_validate_keys(sub_iter)

        stat_validate_keys(self.iter_hierarchy())
        if not all_validate_keys == set(meta.keys()):
            raise InvalidMoldError("mold.meta数据有误, 请检查")

        field_children_alias = defaultdict(list)
        for key, value in meta.items():
            path_list = key.split("|")
            parent_path = "|".join(path_list[:-1])
            alias = value["alias"]
            self.is_valid_filed_name(alias)
            if alias in field_children_alias[parent_path]:
                raise InvalidMoldError(f"发现重复字段, 请检查: {self.gat_alias_path(meta, parent_path)}")
            for idx in range(1, len(path_list)):
                ancestor_path = "|".join(path_list[:idx])
                ancestor_alias = meta[ancestor_path]["alias"]
                if alias == ancestor_alias:
                    raise InvalidMoldError(f"父子字段重复, 请检查: {self.gat_alias_path(meta, key)}")
            field_children_alias[parent_path].append(alias)

    @staticmethod
    def gat_alias_path(meta, alias):
        alias_path = []
        alias_list = alias.split("|")
        for idx in range(1, len(alias_list) + 1):
            alias_path.append(meta["|".join(alias_list[:idx])]["alias"])

        return "|".join(alias_path)


def attribute_id(key_path):
    name_path = [p.split(":")[0] for p in key_path]
    return "-".join(name_path[1:])
