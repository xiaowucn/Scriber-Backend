import contextlib
import functools
import json
import re

import peewee
import peewee_async
import psycopg2
import redis
import redis.asyncio as aredis
from gino.api import Gino
from playhouse.mysql_ext import JSONField as MySQLJSONField  # noqa
from speedy.peewee_plus.engine import PAI_PREFETCH_TYPE, PaiUpdateUtcManager
from sqlalchemy.engine.url import URL

from remarkable import config
from remarkable.common.pattern import PatternCollection
from remarkable.config import get_config

if get_config("worker.task_always_eager"):
    import nest_asyncio

    nest_asyncio.apply()

_rdb_pool = redis.ConnectionPool(
    host=config.get_config("redis.host"),
    port=config.get_config("redis.port"),
    db=config.get_config("redis.db"),
    password=(config.get_config("redis.password") or ""),
    decode_responses=True,
)
_async_rdb_pool = aredis.ConnectionPool(
    host=config.get_config("redis.host"),
    port=config.get_config("redis.port"),
    db=config.get_config("redis.db"),
    password=(config.get_config("redis.password") or ""),
    decode_responses=False,  # 异步缓存存的bytes, 关闭自动解码
)
_key_p = PatternCollection([r"\s+:(?P<key>[\w\-]+)\b", r"\s*?%\((?P<key>[\w\-]+)\)s\b"])
legacy_format_p = re.compile(r"%\((\w+)\)s")

IS_MYSQL = get_config("db.type") == "mysql"
IS_GAUSSDB = get_config("db.type") == "gaussdb"


def get_dsn(driver="asyncpg"):
    db_config = config.get_config("db")
    user = db_config.get("user")
    password = db_config.get("password")
    host = db_config.get("host")
    port = db_config.get("port")
    db_name = db_config.get("dbname")
    return URL(drivername=driver, host=host, port=port, username=user, password=password, database=db_name)


class _EmptyBindContext:
    """Do nothing asynchronous context manager"""

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class GinoDB(Gino):
    """Base class for GINO database."""

    pool_min_size = 1
    pool_max_size = 16
    _dsn = get_dsn("mysql") if IS_MYSQL else get_dsn()

    @property
    def _server_settings(self):
        return {k: v for k, v in (config.get_config("db.server_settings") or {}).items() if not isinstance(v, dict)}

    @property
    def is_gaussdb(self):
        return any("gaussdb" in v.lower() for v in self._server_settings.values() if isinstance(v, str))

    def with_bind(self, echo=False, pool_min_size=None, pool_max_size=None, ssl=None, **kwargs):
        if self.bakery._closed:
            # No need to re-initialize gino engine in nested db transactions
            return _EmptyBindContext()
        if IS_MYSQL:
            extra_kw = {}
        else:
            extra_kw = {
                "min_size": pool_min_size or self.pool_min_size,
                "max_size": pool_max_size or self.pool_max_size,
                "ssl": ssl,
                "server_settings": self._server_settings,
            }
        return super().with_bind(
            self._dsn,
            echo=echo,
            **extra_kw,
            **kwargs,
        )

    async def init_app(self, app, loop=None, echo=False, pool_min_size=None, pool_max_size=None, ssl=None, **kwargs):
        """Initialize GINO database connection for tornado web application"""
        if get_config("db.type") == "gaussdb":  # 高斯db不支持使用gino
            return
        if IS_MYSQL:
            extra_kw = {}
        else:
            extra_kw = {
                "min_size": pool_min_size or self.pool_min_size,
                "max_size": pool_max_size or self.pool_max_size,
                "ssl": ssl,
                "server_settings": self._server_settings,
            }

        await self.set_bind(
            self._dsn,
            echo=echo,
            **extra_kw,
            **kwargs,
        )
        app.db = self

    async def raw_sql(self, sql: str, delegate: str = "all", **kwargs):
        """
        Raw SQL query support
        "all" returns a list of RowProxy
        "first" returns one RowProxy, or None
        "one" returns one RowProxy
        "one_or_none" returns one RowProxy, or None
        "scalar" returns a single value, or None
        @param sql: SQL query sting
        @param delegate: supported delegates: "first/one_or_none/one/scalar/all/status"
        @param kwargs: depends on which delegate you selected
        @return: RowProxy or RowProxy list or str...(depends on which delegate you selected)
        """
        sql = self.change_sql_style(sql)
        # convert the possible digital string to integer
        for key, value in kwargs.items():
            if key.endswith("id") and value is not None and str(value).isdigit():
                kwargs[key] = int(value)
        async with self.with_bind():
            return await getattr(self, delegate, self.all)(self.text(sql), **kwargs)

    @classmethod
    def change_sql_style(cls, sql):
        # change format string style: %(xxx)s -> :xxx
        return legacy_format_p.sub(r":\1", sql)

    @staticmethod
    def get_count_in_status_rsp(status_rsp: tuple[str, list]):
        return int(status_rsp[0].split()[-1])


def init_rdb():
    return redis.Redis(connection_pool=_rdb_pool)


def async_rdb():
    return aredis.Redis(connection_pool=_async_rdb_pool)


if IS_MYSQL:
    import pymysql
    from pymysql.constants import FIELD_TYPE

    conv = pymysql.converters.conversions.copy()
    conv[FIELD_TYPE.JSON] = json.loads  # 将JSON类型字段转换为Python对象
    _pw_db_pool = peewee_async.PooledMySQLDatabase(
        config.get_config("db.dbname"),
        host=config.get_config("db.host"),
        port=config.get_config("db.port"),
        user=config.get_config("db.user"),
        password=config.get_config("db.password"),
        autocommit=False,
        max_connections=config.get_config("db.max_connections") or 100,
        conv=conv,
    )
else:
    _pw_db_pool = peewee_async.PooledPostgresqlDatabase(
        config.get_config("db.dbname"),
        host=config.get_config("db.host"),
        port=config.get_config("db.port"),
        user=config.get_config("db.user"),
        password=config.get_config("db.password"),
        options=config.get_config("db.options") or "-c search_path=public",
        autocommit=False,
        max_connections=config.get_config("db.max_connections") or 100,
    )


def format_sql(sql: str, params: dict) -> tuple[str, list]:
    """Support `%(key)s` or `:key` param style."""
    _params = []
    for match in _key_p.finditer(sql):
        _params.append(params[match.group("key")])
    return _key_p.sub(" %s", sql), _params


class _PeeweeManager(PaiUpdateUtcManager):
    async def first(self, query, *args, **kwargs) -> peewee.Model | None:
        """同get()，只是在查询不到结果的时候返回None"""
        try:
            if isinstance(query, str):
                params = kwargs.pop("params", None)
                default_row_type = kwargs.pop("default_row_type", None)
                data = list(await self.execute(query, params=params, default_row_type=default_row_type))
                if data:
                    data = data[0]
            else:
                data = await self.get(query, *args, **kwargs)
        except peewee.DoesNotExist:
            return
        else:
            return data

    async def prefetch_one(self, query, *subqueries):
        """
        :param query: Query
        :param subqueries: 要prefetch的Query或Model(会被转成Model.select())
        :return: instance or None
        """
        try:
            prefetch_type = PAI_PREFETCH_TYPE.JOIN if IS_MYSQL else PAI_PREFETCH_TYPE.WHERE
            prefetched = await self.prefetch(query.limit(1), *subqueries, prefetch_type=prefetch_type)
            instance = list(prefetched)[0]
        except IndexError:
            return None
        return instance

    @contextlib.contextmanager
    def allow_sync(self):
        """Allow sync queries within context. Close sync
        connection on exit if connected.

        Example::

            with database.allow_sync():
                PageBlock.create_table(True)
        """
        if self.database._allow_sync is True:
            yield
        else:
            with super().allow_sync():
                yield

    @contextlib.contextmanager
    def sync_execute(self, sql: str, params: dict | None = None, default_row_type=None) -> peewee.CursorWrapper:
        """Execute raw query synchronously."""
        query = self.make_query(sql, params, default_row_type)
        with self.allow_sync():
            try:
                cursor_wrapper = query.execute()
                try:
                    for row in cursor_wrapper:
                        cursor_wrapper.row_cache.append(row)
                except psycopg2.ProgrammingError:
                    pass
                cursor_wrapper.fetchone = lambda: cursor_wrapper.row_cache[0] if cursor_wrapper.row_cache else None
                cursor_wrapper.fetchall = lambda: cursor_wrapper.row_cache
                yield cursor_wrapper
            finally:
                pass

    async def execute(self, query, params=None, default_row_type=None):
        if isinstance(query, str):
            query = self.make_query(query, params, default_row_type)
            try:
                return await super().execute(query)
            except psycopg2.ProgrammingError:
                # Some raw queries may have no result which will raise ProgrammingError, so we ignore it.
                return None
        return await super().execute(query)

    async def scalar(self, query, as_tuple=False):
        if isinstance(query, str):
            query = peewee.RawQuery(query, _database=self.database)
            try:
                data = await super().scalar(query, as_tuple=as_tuple)
            finally:
                await self.database.close_async()
            return data

        return await super().scalar(query, as_tuple=as_tuple)

    def make_query(self, sql: str, params: dict | None = None, default_row_type=None):
        query = peewee.RawQuery(*format_sql(sql, params or {}), _database=self.database)
        query.default_row_type = default_row_type or peewee.ROW.NAMED_TUPLE
        return query

    async def get_seq_by_name(self, seq_name: str):
        """
        获取表的自增序列
        """
        if IS_MYSQL:
            await self.execute(f"ANALYZE TABLE {seq_name};")
            query = f"SELECT AUTO_INCREMENT as seq_id FROM information_schema.tables WHERE table_name = '{seq_name}' AND table_schema = DATABASE();"
        else:
            query = f"select last_value as seq_id from {seq_name};"
        return await self.first(query)


db = GinoDB()
pw_db = _PeeweeManager(_pw_db_pool)
# Disable sync mode by default, please DO NOT enable it in production due to the multiprocessing issue.
pw_db.database.allow_sync = False


def peewee_transaction_wrapper(method):
    @functools.wraps(method)
    async def wrapper(*args, **kwargs):
        async with pw_db.atomic():
            return await method(*args, **kwargs)

    return wrapper
