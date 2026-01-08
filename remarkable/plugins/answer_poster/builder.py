import re
from collections import OrderedDict
from itertools import chain

from sqlalchemy import Column, ForeignKey, Integer, Table, Text, create_engine
from sqlalchemy.orm import mapper, relationship
from sqlalchemy.schema import Sequence

from remarkable.common.schema import Schema

from .models import metadata

namespaces = {}


class TableBuilder:
    def __init__(self):
        self.metadata = metadata
        self.tables = OrderedDict()  # to keep the order from root to leaf
        self.properties = {}
        self.orm_classes = OrderedDict()  # to keep the order from leaf to root

    @staticmethod
    def clear_text(_str):
        _str = re.sub(r"[\s<>()（）、【】%]", "", _str)
        return _str

    @staticmethod
    def table_name(name, namespace=None):
        # return TableBuilder.clear_text(name)
        return TableBuilder.pinyin_name(name, namespaces.setdefault(namespace or "table", {}))

    @staticmethod
    def column_name(name, namespace=None):
        return TableBuilder.clear_text(name)
        # return TableBuilder.pinyin_name(name, namespaces.setdefault(namespace or "column", {}))

    @staticmethod
    def pinyin_name(name, existed_mapping, suffix=0):
        from pypinyin import Style, pinyin

        py_name = "".join(
            chain(*pinyin("%s%s" % (TableBuilder.clear_text(name), suffix or ""), style=Style.FIRST_LETTER))
        ).upper()
        if py_name in existed_mapping and existed_mapping[py_name] != name:
            return TableBuilder.pinyin_name(name, existed_mapping, suffix=suffix + 1)
        else:
            existed_mapping[py_name] = name
            return py_name

    @staticmethod
    def foreign_key(table, column, relationship_column=False):
        name_array = [column, table]
        if not relationship_column:
            name_array.append("id")
        return "_".join(name_array)

    def build(self, mold_data, dsn_url):
        self.schema = Schema(mold_data)
        self._build_single_table_by_schema(self.schema.schemas[0])
        engine = create_engine(dsn_url, echo=False)
        self.metadata.create_all(engine)
        for _type in self.tables:
            self._build_orm_class(_type)
        return self.orm_classes

    def _build_single_table_by_schema(self, single_schema):
        _type_name = single_schema["name"]
        _table_name = TableBuilder.table_name(_type_name)
        if _table_name in self.metadata.tables:
            return
        _table = Table(
            _table_name,
            self.metadata,
            Column("id", Integer, Sequence(f"{_table_name}_id_seq"), primary_key=True),
            Column("record_id", Integer, ForeignKey("record.id"), nullable=False),
            comment=_type_name,
        )
        for col, defination in single_schema["schema"].items():
            col_name = TableBuilder.column_name(col, namespace=_table_name)
            col_type = defination["type"]
            if col_type in self.schema.schema_dict:
                if col_type not in self.tables:
                    self._build_single_table_by_schema(self.schema.schema_dict[col_type])
                _sub_table = self.tables[col_type]
                _foreign_key_column = Column(
                    TableBuilder.foreign_key(_table_name, col_name),
                    Integer,
                    ForeignKey("%s.id" % _table_name),
                    comment="foreign key for %s" % col_name,
                )
                _sub_table.append_column(_foreign_key_column)
                self.properties.setdefault(col_type, []).append(
                    # 1:n 在 外表 增加 relationship 字段，字段名 是 主表名_字段名
                    (
                        _type_name,
                        TableBuilder.foreign_key(_table_name, col_name, relationship_column=True),
                        _foreign_key_column,
                    )
                )
                continue
            col_type = Text
            _table.append_column(Column(col_name, col_type, comment=col))
        self.tables[_type_name] = _table
        return

    def _build_orm_class(self, name):
        if name not in self.orm_classes:
            _orm_class = type(name, (object,), {})
            _properties = {}
            for _parent_type, _column_name, _foreign_key in self.properties.get(name, []):
                _parent_orm_class = self._build_orm_class(_parent_type)
                _properties[_column_name] = relationship(_parent_orm_class, foreign_keys=_foreign_key)
            mapper(_orm_class, self.tables[name], properties=_properties)
            self.orm_classes[name] = _orm_class
        return self.orm_classes[name]
