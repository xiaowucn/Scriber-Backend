import datetime
import decimal
import logging
from typing import Callable, Sequence

import peewee
import webargs
from marshmallow import Schema
from pyparsing import Forward, Group, Literal, Word, alphas, delimitedList, nums
from six.moves import collections_abc
from speedy.peewee_plus.engine import PAI_PREFETCH_TYPE

from remarkable.common import field_validate
from remarkable.db import IS_MYSQL, db, pw_db

logger = logging.getLogger(__name__)


class QueryHelper:
    MAX_PAGE_SIZE = 1000

    @classmethod
    async def count(cls, query, columns, params=None, group_by=None):
        if not params:
            params = {}
        if group_by:
            query = " ".join([query, group_by])
        _fields = ",".join(columns)
        total = len(await db.raw_sql(query.format(_fields), "all", **params))
        return total

    # @classmethod
    # def filter_perm(cls, query, current_user):
    #     if not re.search(r"(from|join)\s+file", query.lower()):
    #         return query
    #     if current_user and current_user.has_any_perms("manage_prj"):
    #         return query
    #     if re.search(r"order\s+by|limit", query.lower()):
    #         raise CustomError("invalid sql")
    #     # 无特殊权限只返回本id所属文件
    #     return "{} and (file.uid = {} or (select public from file_project where id=file.pid limit 1) = true)".format(
    #         query.rstrip(";"), current_user.id
    #     )

    @classmethod
    async def _querydata(cls, query, columns, params=None, order_by=None, group_by=None, page=None, size=None):
        if not params:
            params = {}
        if group_by:
            query = " ".join([query, group_by])
        if order_by and "order by" not in query:
            query = " ".join([query, order_by])
        if page and size and "offset" not in query:
            query = f"{query} offset {(page - 1) * size} limit {size}"
        data = await db.raw_sql(query.format(",".join(columns)), "all", **params)
        return [dict(row) for row in data]

    @classmethod
    async def pagedata(cls, query, columns, page=1, size=20, params=None, group_by="", order_by=""):
        if not params:
            params = {}
        # current_user = None
        # if params and "uid" in params:
        #     current_user = await NewAdminUser.find_by_id(params["uid"])
        # query = cls.filter_perm(query, current_user)
        total = await cls.count(query, columns, params=params, group_by=group_by)
        items = await cls._querydata(
            query.strip(";"), columns, params=params, order_by=order_by, group_by=group_by, page=page, size=size
        )
        return {"page": page, "size": size, "total": total, "items": items}

    @classmethod
    async def pagedata_from_request(cls, request, query, columns, order_by="", params=None):
        page = int(request.get_argument("page", "1"))
        size = int(request.get_argument("size", "20"))
        if size > cls.MAX_PAGE_SIZE:
            size = cls.MAX_PAGE_SIZE
        return await cls.pagedata(query, columns, page=page, size=size, params=params, order_by=order_by)


class RowPacker:
    def __call__(self, row):
        raise NotImplementedError


class DefaultPacker(RowPacker):
    def __call__(self, row):
        return row.to_dict()


class ArgsPacker(RowPacker):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __call__(self, row):
        return row.to_dict(**self.kwargs)


class FuncPacker(RowPacker):
    def __init__(self, func):
        self.func = func

    def __call__(self, row):
        return self.func(row)


field_name = Word(alphas + nums + "_-")
item = Forward()
item <<= Group((field_name + Literal("(").suppress() + delimitedList(item) + Literal(")").suppress())) | field_name
expr = delimitedList(item)
fields_map = {}


def select_fields(fields):
    if not fields_map.get(fields):
        fields_map[fields] = expr.parseString(fields)
    return fields_map[fields]


def marshal(data, fields=None):
    if isinstance(fields, str) and "," in fields:
        fields = select_fields(fields)
    if isinstance(data, collections_abc.Sequence) and not isinstance(data, str):
        res = []
        for row in data:
            res.append(marshal(row, fields))
    else:
        if isinstance(data, dict):
            return {k: str(v) if isinstance(v, (datetime.date, decimal.Decimal)) else v for k, v in data.items()}
        res = {}
        if not fields:
            if isinstance(data, (str, int, float, bool)):
                return data
            return data.to_dict()
        for field in fields:
            if isinstance(field, str):
                field_data = getattr(data, field)
                if hasattr(data, "handle_{}".format(field)):
                    method_or_attr = getattr(data, "handle_{}".format(field))
                    if callable(method_or_attr):
                        res[field] = method_or_attr()
                    else:
                        res[field] = method_or_attr
                elif isinstance(field_data, (str, int, dict, float, bool)) or field_data is None:
                    res[field] = field_data
                elif isinstance(field_data, collections_abc.Sequence):
                    res[field] = marshal(field_data)
                elif isinstance(field_data, (datetime.date, decimal.Decimal)):
                    res[field] = str(field_data)
                else:
                    res[field] = field_data.to_dict()
            else:
                result = None
                try:
                    result = getattr(data, field[0])
                except:  # noqa
                    res[field[0]] = result
                else:
                    res[field[0]] = marshal(result, field[1:])

    return res


class AsyncPagination:
    MAX_PAGE_SIZE = 500
    web_args = {
        "page": webargs.fields.Int(load_default=1, validate=field_validate.Range(1)),
        "size": webargs.fields.Int(load_default=20),
    }

    def __init__(self, query, page=1, size=20):
        self._query = query
        self._page = page
        self._size = size if size < self.MAX_PAGE_SIZE else self.MAX_PAGE_SIZE

    async def data(
        self,
        *subqueries: peewee.Query,
        fields: Sequence = "",
        dump_func: Callable | None = None,
        no_marshal: bool = False,
    ) -> dict:
        total = await pw_db.count(self._query)
        prefetch_type = PAI_PREFETCH_TYPE.JOIN if IS_MYSQL else PAI_PREFETCH_TYPE.WHERE
        items = await pw_db.prefetch(
            paginate(self._query, self._page, self._size), *subqueries, prefetch_type=prefetch_type
        )
        if no_marshal:
            res = items
        else:
            res = marshal(list(items), fields) if not dump_func else [dump_func(i, fields) for i in items]
        return {"page": self._page, "size": self._size, "total": total, "items": res}


class PaginationSchema(Schema):
    page = webargs.fields.Int(load_default=1, validate=field_validate.Range(1))
    size = webargs.fields.Int(load_default=20)


def paginate(query: peewee.Query, page: int, size: int):
    if page > 0:
        page -= 1

    if (not query._limit) or ((page + 1) * size < query._limit):
        query._limit = size
    else:
        query._limit = max(query._limit - page * size, 0)

    query._offset = page * size
    return query
