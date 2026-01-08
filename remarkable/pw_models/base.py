from __future__ import annotations

import logging
import os
import re
from typing import Type, TypeVar

import peewee
from peewee import ForeignKeyField
from playhouse.shortcuts import model_to_dict
from psycopg2.errors import UniqueViolation  # noqa
from speedy.peewee_plus import orm
from speedy.peewee_plus.base import PaiBase
from speedy.peewee_plus.orm import TRUE, or_
from typing_extensions import Self
from utensils.util import generate_timestamp

from remarkable.common.exceptions import CustomError
from remarkable.common.util import add_time_hierarchy
from remarkable.config import get_config
from remarkable.db import IS_MYSQL, pw_db
from remarkable.pw_orm import func

logger = logging.getLogger(__name__)
M = TypeVar("M", bound="BaseModel")


class ScriberModelSelect(peewee.ModelSelect):
    def join(self, dest, join_type=peewee.JOIN.INNER, on=None, src=None, attr=None, **options) -> Self:
        query = super().join(dest, join_type=join_type, on=on, src=src, attr=attr)

        if (
            not isinstance(dest, (peewee.Select, peewee.CTE))
            and join_type != peewee.JOIN.CROSS
            and issubclass(dest, peewee.Model)
            and not options.get("include_deleted")
        ):
            if hasattr(dest, "deleted_utc") and not options.get("include_deleted"):
                query = query.filter(dest.deleted_utc == 0)
                # join: peewee.Join = query._from_list[-1]  # noqa
                # join._on &= dest.deleted_utc == 0  # noqa
        return query


class ScriberBase(PaiBase):
    @classmethod
    def select(cls, *fields, for_update=False):
        is_default = not fields
        if not fields:
            fields = cls._meta.sorted_fields
        query = ScriberModelSelect(cls, fields, is_default=is_default)
        if for_update:
            query = query.for_update()
        return query


class _Meta(peewee.ModelBase):
    def __getattribute__(cls, item):
        if item.startswith("-"):
            return super().__getattribute__(item[1:]).desc()
        return super().__getattribute__(item)


class ReadOnlyForeignKeyField(ForeignKeyField):
    """指定了backref 但在软删时明确不级联删除"""


class BaseModel(ScriberBase, metaclass=_Meta):
    class Meta:
        database = pw_db.database
        db_manager = pw_db
        legacy_table_names = False

    @classmethod
    def select(cls, *fields, for_update=False, **options):
        exclude_fields = set(options.get("exclude_fields", []))
        if not fields and exclude_fields:
            fields = [item for item in cls._meta.sorted_fields if item not in exclude_fields]
        query = super().select(*fields, for_update=for_update)
        if hasattr(cls, "deleted_utc") and not options.get("include_deleted"):
            query = query.filter(cls.deleted_utc == 0)
        return query

    @classmethod
    async def find_by_id(cls: Type[M], record_id: int | str, prefetch_queries=None, **options) -> M | None:  # noqa: UP006
        return await cls.get_by_id(record_id, prefetch_queries=prefetch_queries, **options)

    async def soft_delete(self):
        """Soft delete object from database which has 'deleted_utc' col."""
        if not hasattr(self, "deleted_utc"):
            raise CustomError(f'{self.table_name()} has no column "deleted_utc"')

        self.deleted_utc = generate_timestamp()
        await pw_db.update(self)

        for backref in self._meta.backrefs.keys():
            if isinstance(backref, ReadOnlyForeignKeyField):
                continue
            if isinstance(backref, ForeignKeyField):
                items = await self.get_related_objects(backref.model, backref)
                for item in items:
                    await item.soft_delete()

    def path(self, col="hash", *, parent="", abs_path=False) -> str | None:
        if not hasattr(self, col):
            logger.warning(f"{self.table_name()} has no column {col}")
            return None
        value = getattr(self, col)
        if value is None or str(value) == "" or str(value) == "null":
            return None
        if get_config("client.add_time_hierarchy", False):
            if not hasattr(self, "created_utc"):
                logger.warning(f"{self.table_name()} has no column created_utc")
                return None
            relative_path = add_time_hierarchy(self.created_utc, value, parent)
        else:
            relative_path = os.path.join(parent, value[:2], value[2:])
        if abs_path:
            from remarkable.common.storage import localstorage

            return localstorage.mount(relative_path)
        return relative_path

    def to_dict(self, **kwargs):
        return model_to_dict(self, **kwargs)

    @classmethod
    async def create(cls, **kwargs):
        return await pw_db.create(cls, **kwargs)

    @classmethod
    async def insert_or_update(cls, *, conflict_target=None, **kwargs) -> "BaseModel":
        if IS_MYSQL:
            if conflict_target is None:
                pk_id = kwargs.get("id")
                if pk_id is None:
                    raise ValueError("please specify unique key 'id' in kwargs")
                cond = [cls.id == kwargs.get("id")]
            else:
                cond = [item == kwargs.get(item.column.name) for item in conflict_target]
            res = await pw_db.first(cls.select().where(*cond))
            if res:
                await res.update_(**kwargs)
                pk_id = res.id
            else:
                pk_id = await pw_db.execute(cls.insert(**kwargs))
        else:
            if conflict_target is None:
                conflict_target = [cls.id]
            pk_id = await pw_db.execute(
                cls.insert(**kwargs).on_conflict(conflict_target=conflict_target, update=kwargs)
            )

        return await cls.get_by_id(pk_id)

    @classmethod
    async def insert_and_returning(cls, insert_values: list[dict], returning) -> list[dict]:
        if IS_MYSQL:
            res = []
            for item in insert_values:
                pk = await pw_db.execute(cls.insert(**item))
                inst = await pw_db.first(cls.select().where(cls.id == pk))
                for i in returning:
                    res.append({i.name: getattr(inst, i.name)})
            return res
        else:
            return list(await pw_db.execute(cls.insert(insert_values).returning(*returning).dicts()))

    # @classmethod
    # def load_from_legacy_model(cls, obj):
    #     warnings.warn(
    #         "The 'load_from_legacy_model' method is deprecated, use New ORM model instead", DeprecationWarning
    #     )
    #     if isinstance(obj, cls.__class__):
    #         return obj
    #     if isinstance(obj, dict):
    #         return cls(**obj)
    #     return cls(**obj.to_dict(show_all=True))

    @classmethod
    async def update_by_pk(cls, pk_id, update_timestamp=True, **kwargs):
        item = await cls.find_by_id(pk_id)
        if not item:
            return
        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)
        await pw_db.update(item, update_timestamp=update_timestamp)
        return item

    @classmethod
    def update(cls, __data=None, update_timestamp=True, **update):
        if update_timestamp:
            for key in ["updated_at", "updated_utc"]:
                if hasattr(cls, key):
                    update.setdefault(key, generate_timestamp())
                    break
        return super().update(__data, **update)

    @classmethod
    async def get_first_one(cls, cond, order_by=None, for_update=False) -> "BaseModel" | None:
        if order_by is None:
            order_by = cls.id.desc()
        query = cls.select().where(cond).order_by(order_by)
        if for_update:
            query = query.for_update()
        return await pw_db.first(query)

    @classmethod
    async def create_or_get(cls: Type["TModel"], defaults, **kwargs) -> ["TModel", bool]:  # noqa: UP006
        defaults = defaults or {}
        defaults.update(kwargs)
        conditions = []
        for key, val in kwargs.items():
            conditions.append(getattr(cls, key) == val)

        query = cls.insert(**defaults).on_conflict(
            action="ignore",
            conflict_target=[getattr(cls, key) for key in kwargs],
            conflict_where=(orm.and_(*conditions)),
        )
        record = await pw_db.execute(query)
        return await pw_db.first(cls.select().where(*conditions)), record is not None

    @classmethod
    async def create_or_update(cls, **kwargs):
        try:
            ret = await cls.create(**kwargs)
        except peewee.IntegrityError as exp:
            if IS_MYSQL:
                ret = await cls.insert_or_update(**kwargs)
                return ret
            # todo: 暂时只给同步脚本用, 后续遇到问题再看怎么处理
            match = re.search(r"\((?P<cols>.*)\)=", str(exp.orig))  # noqa
            if not match:
                raise exp
            cols = [i.strip() for i in match.group("cols").split(",")]
            query_kw = {k: kwargs.pop(k) for k in cols}
            ret = await cls.find_by_kwargs(include_deleted=True, **query_kw)
            if getattr(ret, "deleted_utc", None):
                ret.deleted_utc = 0
                kwargs["deleted_utc"] = 0
            await ret.update_(**kwargs)
        return ret

    @classmethod
    async def all_ids_exists(cls, ids: list[int]):
        count = await pw_db.count(cls.select().where(cls.id.in_(ids)))
        return len(set(ids)) == count

    @classmethod
    async def count(cls, cond):
        return await pw_db.count(cls.select().filter(cond))

    @classmethod
    async def find_by_kwargs(
        cls, delegate: str = "first", desc: bool = True, include_deleted: bool = False, **kwargs
    ) -> Self | list[Self] | None:
        query = cls.select(include_deleted=include_deleted).filter(**kwargs)
        if delegate == "first":
            return await pw_db.first(query)
        if delegate == "all":
            if desc:
                query = query.order_by(cls.id.desc())
            else:
                query = query.order_by(cls.id)
            return list(await pw_db.execute(query))
        raise ValueError(f"Unknown delegate: {delegate}")

    @classmethod
    async def find_by_ids(cls: Type[M], record_ids: list[int]) -> list[M]:  # noqa: UP006
        cond = cls.id.in_(record_ids)
        return list(await pw_db.execute(cls.select().where(cond)))

    async def update_(self, **kwargs):
        await pw_db.update(self, **kwargs)

    def updated_info(self, **kwargs):
        """
        对应kwargs更新实例, 获取有变更的字典, 值为tuple(before, after)
        """
        updated = {}
        for key, val in kwargs.items():
            ins_val = getattr(self, key)
            if ins_val != val:
                updated[key] = (ins_val, val)
        return updated

    @classmethod
    def jsonb_build_object(cls, *fields, **kwargs):
        def _get_param():
            for field in fields:
                yield field
                yield getattr(cls, field)
            for key, val in kwargs.items():
                yield key
                yield val

        return func.JSONB_BUILD_OBJECT(*_get_param())

    @classmethod
    async def bulk_update(cls, update_field, by_field, bulk_map, cond=TRUE, jsonb_path=None, **extra):
        """
        根据map: (filter_by, update_value) 批量更新 update_field 为 map 的 value 当 by_field 的值等于 map 的key时

        Args:
            update_field: 要更新的字段
            by_field: 用于匹配的字段
            bulk_map: 批量更新映射 {filter_value: update_value}
            cond: 额外的查询条件
            jsonb_path: JSONB字段的路径，如果指定则使用jsonb_set更新
            **extra: 额外的更新字段

        Returns:
            int: 受影响的行数
        """
        if not bulk_map:
            return 0

        map_values = peewee.ValuesList(bulk_map.items(), columns=["filter_by", "update_value"], alias="map")

        # 如果指定了jsonb_path，使用jsonb_set更新特定路径
        if jsonb_path:
            if IS_MYSQL:
                # MySQL使用JSON_SET
                update_expr = peewee.fn.JSON_SET(update_field, jsonb_path, map_values.c.update_value)
            else:
                # PostgreSQL使用jsonb_set
                update_expr = peewee.fn.jsonb_set(
                    update_field,
                    peewee.Value(jsonb_path.strip("{}").split(",")),
                    map_values.c.update_value.cast("jsonb"),
                )

            query = (
                cls.update({update_field: update_expr, **extra})
                .from_(map_values)
                .where(cond, by_field == map_values.c.filter_by)
            )
        else:
            # 普通字段更新或JSONB字段全量更新
            # 检查是否为JSONB字段的全量更新
            if hasattr(update_field, "field_type") and "json" in str(update_field.field_type).lower():
                # JSONB字段全量更新
                if IS_MYSQL:
                    # MySQL: 直接赋值JSON字符串
                    update_expr = map_values.c.update_value.cast("json")
                else:
                    # PostgreSQL: 转换为jsonb类型
                    update_expr = map_values.c.update_value.cast("jsonb")

                query = (
                    cls.update({update_field: update_expr, **extra})
                    .from_(map_values)
                    .where(cond, by_field == map_values.c.filter_by)
                )
            else:
                # 普通字段更新
                query = (
                    cls.update({update_field: map_values.c.update_value, **extra})
                    .from_(map_values)
                    .where(cond, by_field == map_values.c.filter_by)
                )

                if update_field != by_field:
                    query = query.where(or_(update_field != map_values.c.update_value, update_field.is_null()))

        return await cls.manager().execute(query)


class BaseUTCModel(BaseModel):
    # 有默认值时 建议null=False, created_utc 默认不用加索引
    created_utc = peewee.IntegerField(constraints=[peewee.SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])
    updated_utc = peewee.IntegerField(constraints=[peewee.SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])
    deleted_utc = peewee.IntegerField(constraints=[peewee.SQL("DEFAULT 0")])

    @property
    def deleted(self) -> bool:
        return bool(self.deleted_utc != 0)


TModel = TypeVar("TModel", bound=BaseModel)


def to_sql(query: peewee.Select):
    cur = pw_db.database.cursor()
    sql = cur.mogrify(*query.sql())
    if isinstance(sql, bytes):
        return sql.decode()
    return sql
