import logging
import re
import typing
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection, Request
from starlette.responses import Response
from tornado.web import RequestHandler, decode_signed_value

from remarkable import db
from remarkable.common.constants import get_perms
from remarkable.common.util import need_secure_cookie
from remarkable.config import get_config
from remarkable.security.package_encrypt import aes_dump, aes_load

logger = logging.getLogger(__name__)


def encode_permission(perms: list[dict[str, str]]):
    """
    权限列表转为十进制数, 缩减redis内存占用
    :param perms: [{'perm': 'browse'}, {'perm': 'manage_prj'}]
    :return: 十进制int, 如14
    """
    # 倒排权限列表, 如有新加权限需要从列表末尾插入
    full_perms = get_perms()[::-1]
    # 将接收权限列表按照系统权限列表顺序排列
    perms = [i for i in full_perms if i in [i["perm"] for i in perms]]
    # 转二进制字串
    perms_str = "".join([i in perms and "1" or "0" for i in full_perms])
    return int(perms_str, 2)


def decode_permission(perm: int) -> list[dict[str, str]]:
    """
    十进制数还原为权限列表
    :param perm: 十进制int, 如14
    :return: list, 如[{'perm': 'browse'}, {'perm': 'manage_prj'}]
    """
    full_perms = get_perms()[::-1]
    bin_str = bin(perm).lstrip("0b")
    return [{"perm": i[1]} for i in zip(bin_str.zfill(len(full_perms)), full_perms) if i[0] == "1"]


class RedisDriver:
    EXPIRE_SECONDS = get_config("app.session_expire", 10 * 60)
    FAIL_COUNTS = get_config("app.max_fail_count", 10)
    _hgetall_script = None
    _hmset_script = None
    _client = None
    _app_id = get_config("app.app_id", "scriber")

    @property
    def hgetall_script(self):
        """session如果存在则返回内容, 并同时刷新过期时间
        如果记录登录失败次数超过5次时, 只返回内容不刷新过期时间, 用来限制多次进行登录尝试
        """
        if self._hgetall_script:
            return self._hgetall_script
        lua = """
            local flat_map = redis.call("hgetall", KEYS[1])
            local _fail_count = redis.call("hget", KEYS[1], "_fail_count")
            if next(flat_map) == nil then
                return {}
            end
            if type(_fail_count) == "string" and tonumber(_fail_count) >= tonumber(ARGV[2]) then
                return flat_map
            end
            redis.call("expire", KEYS[1], ARGV[1])
            return flat_map
        """
        self._hgetall_script = self.client.register_script(lua)
        return self._hgetall_script

    @property
    def client(self):
        if not self._client:
            self._client = db.init_rdb()
        return self._client

    def hmset(self, uid, session_id, cache_value):
        u_key = self.db_key(uid, "uid")
        s_key = self.db_key(session_id)
        pipe = self.client.pipeline()
        pipe.lpush(u_key, session_id)  # 改用list记录用户登录过的session_id
        pipe.hmset(s_key, cache_value)
        pipe.expire(u_key, self.EXPIRE_SECONDS)
        pipe.expire(s_key, self.EXPIRE_SECONDS)
        pipe.execute()

    def hgetall(self, session_id):
        flat_map = self.hgetall_script(keys=[self.db_key(session_id)], args=[self.EXPIRE_SECONDS, self.FAIL_COUNTS])
        session_map = {}
        for i in range(0, len(flat_map), 2):
            session_map[flat_map[i]] = flat_map[i + 1]
        return session_map

    def llen(self, key, key_type="uid"):
        """获取uid key的长度, 同时控制该key的长度在配置限制次数+1"""
        key = self.db_key(key, key_type)
        pipe = self.client.pipeline()
        pipe.llen(key)
        pipe.ltrim(key, 0, self.FAIL_COUNTS)
        return pipe.execute()[0]

    def expire(self, keys):
        pipe = self.client.pipeline()
        for key in keys:
            pipe.expire(key, self.EXPIRE_SECONDS)
        pipe.execute()

    def get_latest_session_id(self, uid):
        return self.client.lindex(self.db_key(uid, "uid"), 0)

    def get_session_ids(self, uid):
        return self.client.lrange(self.db_key(uid, "uid"), 0, -1)

    def delete(self, keys):
        pipe = self.client.pipeline()
        for key in keys:
            pipe.delete(key)
        pipe.execute()

    @classmethod
    def db_key(cls, id_str, id_type="session"):
        prefix = "{}:{}".format(cls._app_id, id_type)
        if id_str.startswith(prefix):
            return id_str
        return "{}:{}".format(prefix, id_str)


class SessionManager:
    APP_NAME = get_config("app.app_id")
    SESSION_ID_NAME = "{}_session_id".format(APP_NAME)
    P_NO_NUMBER = re.compile(r"\D")

    def __init__(
        self,
        request: RequestHandler | Request | Response | None = None,  # fastapi: read request & set response
        connection: HTTPConnection | None = None,
        headers: MutableHeaders | None = None,
    ):
        assert request or connection, "Either request or connection must be provided"
        self.aesgcm = AESGCM(get_config("app.secret_key").zfill(16).encode())
        self.request = request
        self.connection = connection
        self.headers = headers
        self._driver = None
        self._session_id = None
        self._cache_map = {}
        self._session_map = None

    @property
    def driver(self):
        if self._driver is None:
            self._driver = RedisDriver()
        return self._driver

    @property
    def user_id(self) -> str:
        """优先从缓存中取uid, 取不到再从cookie里拿"""
        uid = self._cache_map.get("uid")
        if uid:
            return uid
        uid = self.session_map.get("uid")  # 弃用tornado secure cookie
        if uid:
            return uid
        # 根据session_id生成相对固定的非法uid
        numbers = self.P_NO_NUMBER.sub("", self.get_cookie(self.SESSION_ID_NAME) or "")
        return f"-{numbers[-4:] or 1}"

    @property
    def encrypted_session_id(self) -> str:
        return aes_dump(self.aesgcm, data=self.session_id).decode()

    @property
    def session_id(self) -> str:
        def _set_cookie():
            self.set_cookie("scriber_app_id", self.APP_NAME, httponly=True, secure=need_secure_cookie)
            self.set_cookie(
                self.SESSION_ID_NAME,
                aes_dump(self.aesgcm, data=self._session_id).decode(),
                httponly=True,
                secure=need_secure_cookie,
            )

        # 先从浏览器cookie中取session_id
        session_id = ""
        if data := self.get_cookie(self.SESSION_ID_NAME):
            try:
                session_id = aes_load(self.aesgcm, data=data.encode())
            except Exception as e:
                logger.warning(f"Failed to decode session_id: {e}")

        # 单点登录限制
        if get_config("app.single_sign_limit"):
            # 从当前cookie中取出session id与redis中比较, 相同则返回, 不同则说明发生了新的登录动作, 需要重新生成一个session_id
            if session_id:
                self._session_map = self.driver.hgetall(session_id)
                sid_in_redis = self.driver.get_latest_session_id(self.user_id)
                if session_id == sid_in_redis:
                    return session_id
                if not sid_in_redis:
                    # 有session_id但redis中没有，可能是过期，也可能是新登录。
                    self._session_id = session_id
                    self.driver.hmset(self.user_id, session_id, {"_fail_count": 0})
                    _set_cookie()
        else:
            # 默认不做单点登录限制，只要cookie能拿到session_id就直接返回
            if session_id:
                return session_id

        # 返回缓存的session_id
        if self._session_id:
            return self._session_id

        # 如果从浏览器和缓存都没有拿到session_id，则需要重新生成
        self._session_id = uuid4().hex
        # 确保前端在未登录状态拿到cookie前缀, 即app_id
        _set_cookie()
        return self._session_id

    def set_cookie(
        self,
        name: str,
        value: str | bytes,
        *,
        httponly: bool = False,
        secure: bool = False,
        same_site: typing.Literal["lax", "strict", "none"] = "none",
        **kwargs: typing.Any,
    ) -> None:
        if isinstance(self.request, (RequestHandler, Response)):
            if not secure and same_site == "none":
                same_site = "lax"
            self.request.set_cookie(name, value, httponly=httponly, secure=secure, samesite=same_site, **kwargs)

    def get_cookie(self, name: str, default: str | None = None) -> str | None:
        if isinstance(self.request, RequestHandler):
            return self.request.get_cookie(name, default)
        if isinstance(self.request, Request):
            return self.request.cookies.get(name, default)
        return self.connection.cookies.get(name, default)

    def get_secure_cookie(
        self,
        key,
        value=None,
        max_age_days: float = 31,
        min_version: int | None = None,
    ) -> bytes | None:
        if isinstance(self.request, RequestHandler):
            return self.request.get_secure_cookie(key, value)

        if value is None:
            value = self.connection.cookies.get(key) if self.connection else self.request.cookies.get(key)
        return decode_signed_value(
            get_config("app.cookie_secret"),
            key,
            value,
            max_age_days=max_age_days,
            min_version=min_version,
        )

    @property
    def session_map(self) -> dict[str, typing.Any]:
        if self._session_map is None:
            self._session_map = self.driver.hgetall(self.session_id)
        return self._session_map

    def __setitem__(self, key, value):
        if key == "uid":
            value = str(value)
        self._cache_map[key] = value

    def __getitem__(self, key):
        value = self._cache_map.get(key)
        if not value:
            return self.session_map.get(key)
        return value

    def silence_tries(self) -> int:
        login_count = self.driver.llen(self.user_id)
        if int(self.user_id) >= 0:
            # 正常用户返回用户登录次数
            return login_count
        # 非法用户返回非法用户登录总次数
        invalid_login_count = 0
        for _ in self.driver.client.scan_iter(match=self.driver.db_key("uid:-"), count=self.driver.FAIL_COUNTS):
            invalid_login_count += 1
        return max(invalid_login_count, login_count)

    def refresh(self):
        keys = [
            self.driver.db_key(self.user_id, "uid"),
            self.driver.db_key(self.session_id, "session"),
        ]
        self.driver.expire(keys)

    def clear(self, uid: str, sid: str):
        db_uid = self.driver.db_key(uid, "uid")
        if sid is None:
            keys = [db_uid] + [self.driver.db_key(i, "session") for i in self.driver.get_session_ids(uid)]
        else:
            self.driver.client.lrem(db_uid, 0, sid)  # delete current session id
            keys = [self.driver.db_key(sid, "session")]
        self.driver.delete(keys)

    def update(self, uid, **kwargs):
        if "perm" in kwargs:
            kwargs["perm"] = encode_permission(kwargs["perm"])
        for sid in self.driver.get_session_ids(uid):
            session_map = self.driver.hgetall(sid)
            session_map.update(kwargs)
            self.driver.hmset(uid, sid, session_map)

    def set(self):
        if not self._cache_map:
            return
        self.driver.hmset(self.user_id, self.session_id, self._cache_map)


def create_mixin(handler) -> SessionManager:
    attr = "__session_manager"
    if not hasattr(handler, attr):
        setattr(handler, attr, SessionManager(handler))
    return getattr(handler, attr)


class SessionMixin:
    @property
    def session(self) -> SessionManager:
        return create_mixin(self)

    @property
    def silence_tries(self) -> int:
        """获取同一用户(包括非法用户)登录次数"""
        return self.session.silence_tries()

    def session_update(self, uid, **kwargs):
        self.session.update(str(uid), **kwargs)

    def session_refresh(self):
        self.session.refresh()

    def session_clear(self, uid=None):
        if uid is None:
            # delete current user id and session info
            uid = self.session.user_id
            sid = self.session.session_id
        else:
            # delete selected user id and all related session info
            uid = str(uid)
            sid = None
        self.session.clear(uid, sid)

    def session_sync(self):
        self.session.set()

    def session_map(self) -> dict[str, typing.Any]:
        return self.session.session_map
