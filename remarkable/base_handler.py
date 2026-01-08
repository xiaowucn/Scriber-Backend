import asyncio
import datetime
import email.utils
import functools
import html
import http
import importlib
import json
import logging
import mimetypes
import os
import re
import urllib.parse
import warnings
from concurrent.futures import ThreadPoolExecutor
from itertools import chain
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable, Literal

import jwt
import tornado.web
from tornado import httputil, iostream
from tornado.escape import utf8
from user_agents import parse

from remarkable import config
from remarkable.common.constants import API_PREFIX_V1, TokenStatus
from remarkable.common.exceptions import CustomError
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser, TokenUser
from remarkable.models.query_helper import QueryHelper
from remarkable.pw_models.model import NewFileProject, NewFileTree, NewMold
from remarkable.security import authtoken
from remarkable.security.package_encrypt import HexSm4Encryptor, PackageEncrypt
from remarkable.session import SessionMixin

EXPIRE_PROMPT = "The session has expired, please login again"


class route:
    HANDLERS = {}

    def __init__(self, router_url, prefix=API_PREFIX_V1):
        self.router_url = router_url
        self.prefix = prefix

    def __call__(self, clz):
        url = "{}{}".format(self.prefix, self.router_url)
        if url not in self.HANDLERS:
            self.__class__.HANDLERS[url] = clz
        for m in config.get_config("web.http_secure_map") or {}:
            if not hasattr(clz, m.lower()):
                continue
            new_url = "%s/%s" % (url, m.lower())
            if new_url not in self.HANDLERS:
                self.__class__.HANDLERS[new_url] = type(f"Secure{m.capitalize()}{clz.__name__}", (clz,), {})
        return clz

    @classmethod
    def init_handlers(cls):
        logging.info("loading web handlers")
        base_handlers = ["user", "data", "meta", "label_assistant"]
        for handler in base_handlers:
            importlib.import_module(f"remarkable.{handler}.handlers")

        logging.info("loading plugins")
        for plugin in config.get_config("web.plugins") or []:
            logging.info(f"\t- loading plugin: {plugin}")
            try:
                mod = importlib.import_module(f"remarkable.plugins.{plugin}")
            except ModuleNotFoundError as exp:
                logging.warning(f"{exp}")
            else:
                getattr(mod, "init", lambda: logging.warning('No "init" func found'))()

        logging.info("handler list:")
        for url, clz in cls.HANDLERS.items():
            clz.url = url
            logging.info(url)
        return list(cls.HANDLERS.items())


class BaseHandler(tornado.web.RequestHandler, SessionMixin):
    _executor = ThreadPoolExecutor(max_workers=10)

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.hex_binary_key = config.get_config("web.hex_binary_key")
        if self.hex_binary_key:
            self.package_encrypt = HexSm4Encryptor(self.hex_binary_key)
        else:
            binary_key = config.get_config("web.binary_key") or "key"
            self.package_encrypt = PackageEncrypt(binary_key)

    def get_url(self, front_route=""):
        server_url = self.origin_host
        subpath = config.get_config("web.redirect_subpath")
        if subpath:
            server_url = urllib.parse.urljoin(self.origin_host, subpath)

        return server_url if front_route == "" else urllib.parse.urljoin(server_url, front_route.lstrip("/"))

    def initialize(self):
        """
        Hook for subclass initialization. Called for each request.
        before __init__
        """
        if self.url.endswith("/sse"):
            self.set_header("Content-Type", "text/event-stream")
            self.set_header("Cache-Control", "no-cache")
            self.set_header("Connection", "keep-alive")

        self.http_secure_map = config.get_config("web.http_secure_map") or {}
        if not self.http_secure_map:
            self._on_initialized()
            return
        # 禁用不安全的http方法（put/post）
        if self.request.method in self.http_secure_map:
            raise tornado.web.HTTPError(405)
        if not hasattr(self, "url") or self.url is None:
            logging.warning(f"{self.__class__} has no url attribute, please check your code")
            return
        http_method = self.url.split("/")[-1].upper()
        if http_method in self.http_secure_map:
            self.post = getattr(self, http_method.lower())

        self._on_initialized()

    # only used in unittest
    def _on_initialized(self):
        pass

    async def prepare(self):
        if self.request.method.lower() in ("post", "put"):
            for route_ext in config.get_config("web.encrypted_routes") or []:
                if re.search(rf"^/api/v\d+{route_ext}$", self.request.path):
                    logging.debug(f"Decrypt request body for route: {self.request.path}")
                    try:
                        self.request.body = self.package_encrypt.decrypt(self.request.body)
                        self.request.headers["Content-Length"] = len(self.request.body)
                    except ValueError:
                        self.error(_("Cryptographic handshake failed"))
                        self.finish()
                    break
            # 部分接口前端请求头类型不对, 影响 web_args 功能
            # TODO: 待前端修正完毕以后移除此处逻辑
            content_type = self.request.headers.get("Content-Type", "").split(";")[0].lower()
            if content_type in ("text/html", "text/plain", "application/x-www-form-urlencoded"):
                logging.warning(f'Possible invalid "Content-Type": "{content_type}" detected')
                self.request.headers["Content-Type"] = "application/json"

        if (
            (user_id := self.session.user_id)
            and user_id.isdigit()
            and (user := await NewAdminUser.find_by_id(int(user_id)))
        ):
            self.current_user: NewAdminUser = user

    @classmethod
    def run_in_executor(cls, func: Callable, *args: Any) -> Awaitable:
        """Runs a function in a ``concurrent.futures.Executor``. If
        ``executor`` is ``None``, the IO loop's default executor will be used.

        In general, using ``run_in_executor``
        when *calling* a blocking method is recommended instead of using
        this decorator when *defining* a method.
        """
        return asyncio.get_event_loop().run_in_executor(cls._executor, func, *args)

    def check_xsrf_cookie(self):
        if not self.request.path.startswith("/api/v"):
            return None
        if self.request.method in ("GET", "HEAD", "OPTIONS") or not config.get_config("web.xsrf_cookies"):
            return None
        for route_ext in config.get_config("web.trust_routes") or []:
            if re.search(rf"^/api/v\d+{route_ext}$", self.request.path):
                logging.debug(f"Skip xsrf check: {self.request.path}")
                return None
        url = self.request.full_url()
        query = urllib.parse.urlparse(url).query
        params = urllib.parse.parse_qs(query) if query else {}
        if (
            self.request.headers.get("Authorization")
            or "bearer_token" in params
            or all([v for k, v in params.items() if k in ("_token", "_timestamp")] or [None])
        ):
            logging.debug(f"Skip xsrf check: {self.request.path}")
            return None
        try:
            Auth.referer_check(self)
            super().check_xsrf_cookie()
        except tornado.web.HTTPError as exp:
            return Auth.custom_error(self, exp.status_code, exp.log_message)
        return None

    @property
    def origin_host(self):
        scheme = self.request.headers.get("X-Scheme") or "http"
        origin_host = self.request.headers.get("Host") or self.request.host
        origin_host = scheme + "://" + origin_host
        return origin_host

    @property
    def trigger_source(self):
        return self.request.headers.get("X-Trigger-Source", "")

    @property
    def record_menu(self):
        if self.trigger_source == "task":
            return "识别任务管理"
        return "识别文件管理"

    def redirect(self, url, permanent=False, status=None):
        if self._headers_written:
            raise Exception("Cannot redirect after headers have been written")
        if status is None:
            status = 301 if permanent else 302
        else:
            assert isinstance(status, int) and 300 <= status <= 399
        subpath = config.get_config("web.redirect_subpath")
        if subpath:
            prefix = urllib.parse.urljoin(self.origin_host, subpath.lstrip("/"))
            prefix = prefix.rstrip("/")
            if url.startswith("/"):
                url = prefix + url
            elif url.startswith(("http", "https")):
                pass
            else:
                url = prefix + "/" + url
        self.set_status(status)
        self.set_header("Location", utf8(url))
        self.finish()

    def set_default_headers(self):
        # avoid Clickjacking: https://www.ietf.org/rfc/rfc7034.txt
        default_headers = {
            "X-Frame-Options": "DENY",
            "Server": "*",
        }
        http_headers = config.get_config("web.http_headers") or default_headers
        for key, val in http_headers.items():
            self.set_header(key, val)

    def data_received(self, chunk: bytes) -> Awaitable[None] | None:
        pass

    def write_error(self, status_code, **kwargs):
        ex = kwargs.get("exc_info")[1]
        logging.exception(ex)
        if isinstance(ex, CustomError):
            self.error(ex.msg, status_code=ex.resp_status_code, errors=ex.errors)
        elif status_code == 422 and "exc_info" in kwargs:
            etype, exc, traceback = kwargs["exc_info"]
            if hasattr(exc, "messages"):
                if getattr(exc, "headers", None):
                    for name, val in exc.headers.items():
                        self.set_header(name, val)
                error_msg = "Invalid request payload"
                for error_messages in exc.messages.values():
                    for error_message in error_messages.values():
                        if error_message:
                            error_msg = error_message[0]
                            break
                if isinstance(error_msg, dict):
                    self.error(message=str(error_msg), errors=exc.messages, status_code=status_code)
                else:
                    self.error(message=_(error_msg), errors=exc.messages, status_code=status_code)
        elif isinstance(ex, tornado.web.HTTPError):
            self.error(ex.reason, status_code=ex.status_code)
        else:
            self.error(str(ex), status_code=status_code)
            # super(BaseHandler, self).write_error(status_code, **kwargs)

    def get_json_body(self):
        """Return the body of the request as JSON data.
        建议使用 [webargs](https://webargs.readthedocs.io/en/latest/index.html) 接收&验证请求参数
        """
        warnings.warn(
            "The 'get_json_body' method is deprecated, use 'webargs' instead", DeprecationWarning, stacklevel=2
        )
        if not self.request.body:
            return None
        # Do we need to call body.decode('utf-8') here?
        body = self.request.body.strip().decode("utf-8")
        try:
            model = json.loads(html.escape(body, quote=False))
        except Exception:
            logging.exception("Couldn't parse JSON")
            raise tornado.web.HTTPError(400, "Invalid JSON in body of request") from Exception
        return model

    def send_json(self, data, binary=None):
        if self._finished:
            return
        binary = (config.get_config("feature.binary_json") or False) if binary is None else binary
        if binary:
            message = self.package_encrypt.encrypt_json(data)
            self.set_header("Content-Type", "application/binary-json")
            self.write(message)
        else:
            self.set_header("Content-Type", "application/json")
            self.write(json.dumps(data))

    def data(self, data, binary=None):
        self.send_json({"status": "ok", "data": data}, binary=binary)

    def ext_data(self, msg, data, req_id="", status_code=200, binary=None):
        self.set_status(status_code)
        self.send_json({"statusCode": status_code, "msg": msg, "reqId": req_id, "data": data}, binary=binary)

    def ext_error(self, msg, req_id="", status_code=400, binary=None):
        self.set_status(status_code)
        data = {"statusCode": status_code, "msg": msg}
        if req_id:
            data.update({"reqId": req_id})
        self.send_json(data, binary=binary)

    def error(self, message, status_code=200, errors=None, binary=None):
        self.set_status(status_code)
        self.send_json({"status": "error", "message": message, "errors": errors or {}}, binary=binary)

    def on_finish(self):
        self.session_refresh()

    def is_first_fetch_file(self):
        if range_header := self.request.headers.get("Range"):
            # As per RFC 2616 14.16, if an invalid Range header is specified,
            # the request will be treated as if the header didn't exist.
            if request_range := httputil._parse_request_range(range_header):
                start, *_ = request_range
                return not start
        return True

    async def export(
        self,
        abs_path: str | bytes | Path,
        file_name: str | None = None,
        content_type: str = "application/octet-stream",
    ):
        def set_content_length(this, path, req_range):
            size = os.path.getsize(path)
            if req_range:
                start, end = req_range
                if (start is not None and start >= size) or end == 0:
                    # As per RFC 2616 14.35.1, a range is not satisfiable only: if
                    # the first requested byte is equal to or greater than the
                    # content, or when a suffix with length 0 is specified
                    this.set_status(416)  # Range Not Satisfiable
                    this.set_header("Content-Type", "text/plain")
                    this.set_header("Content-Range", "bytes */%s" % (size,))
                    return start, end
                if start is not None and start < 0:
                    start += size
                if end is not None and end > size:
                    # Clients sometimes blindly use a large range to limit their
                    # download size; cap the endpoint at the actual file size.
                    end = size
                # Note: only return HTTP 206 if less than the entire range has been
                # requested. Not only is this semantically correct, but Chrome
                # refuses to play audio if it gets an HTTP 206 in response to
                # ``Range: bytes=0-``.
                if size != (end or size) - (start or 0):
                    this.set_status(206)  # Partial Content
                    this.set_header("Content-Range", httputil._get_content_range(start, end, size))
            else:
                start = end = None

            if start is not None and end is not None:
                length = end - start
            elif end is not None:
                length = end
            elif start is not None:
                length = size - start
            else:
                length = size
            this.set_header("Content-Length", length)
            return start, end

        def set_etag_header(this, path):
            etag = compute_etag(path, this.modified)
            if etag is not None:
                this.set_header("Etag", etag)

        def get_content_type(path):
            mime_type, encoding = mimetypes.guess_type(path)
            # per RFC 6713, use the appropriate type for a gzip compressed file
            if encoding == "gzip":
                return "application/gzip"
            # As of 2015-07-21 there is no bzip2 encoding defined at
            # http://www.iana.org/assignments/media-types/media-types.xhtml
            # So for that (and any other encoding), use octet-stream.
            if mime_type is not None:
                return mime_type
            # if mime_type not detected, use application/octet-stream
            return "application/octet-stream"

        def should_return_304(this):
            if this.check_etag_header():
                return True

            # Check the If-Modified-Since, and don't send the result if the
            # content has not been modified
            ims_value = this.request.headers.get("If-Modified-Since")
            if ims_value is not None:
                date_tuple = email.utils.parsedate(ims_value)
                if date_tuple is not None:
                    if_since = datetime.datetime(*date_tuple[:6])
                    assert this.modified is not None
                    if if_since >= this.modified:
                        return True

            return False

        if isinstance(abs_path, bytes):
            if not content_type:
                content_type = "application/octet-stream"
            self.set_header("Content-Type", content_type)
            if file_name:
                file_name = urllib.parse.quote(file_name)
                self.set_header("Content-Disposition", f"attachment; filename={file_name}")
            return await self.finish(abs_path)
        if not os.path.exists(abs_path):
            raise CustomError(_("File not found"))
        if not file_name:
            file_name = os.path.basename(abs_path)
        file_name = urllib.parse.quote(file_name)
        self.set_header("Content-Disposition", f"attachment; filename={file_name}")
        if not content_type:
            content_type = get_content_type(abs_path)
        self.set_header("Content-Type", content_type)

        self.modified = datetime.datetime.utcfromtimestamp(os.path.getmtime(abs_path))
        set_etag_header(self, abs_path)
        self.set_header("Last-Modified", self.modified)
        cache_time = tornado.web.StaticFileHandler.CACHE_MAX_AGE if "v" in self.request.arguments else 0
        if cache_time > 0:
            self.set_header(
                "Expires",
                datetime.datetime.utcnow() + datetime.timedelta(seconds=cache_time),
            )
            self.set_header("Cache-Control", "max-age=" + str(cache_time))
        if should_return_304(self):
            self.set_status(304)
            return

        request_range = None
        if config.get_config("web.support_http_partial_content", True):
            self.set_header("Accept-Ranges", "bytes")
            range_header = self.request.headers.get("Range")
            if range_header:
                # As per RFC 2616 14.16, if an invalid Range header is specified,
                # the request will be treated as if the header didn't exist.
                request_range = httputil._parse_request_range(range_header)
        start, end = set_content_length(self, abs_path, request_range)

        if self.request.method == "GET":
            from remarkable.common.storage import (
                LocalStorage,
            )

            async for chunk in LocalStorage.chunk_read(abs_path, start, end):
                try:
                    self.write(chunk)
                except iostream.StreamClosedError:
                    return
        else:
            assert self.request.method == "HEAD"

    def get_nafmii_event(self, **kwargs):
        user_agent = parse(self.request.headers.get("User-Agent", ""))

        remote_ip = self.request.headers.get("X-Real-IP") or self.request.remote_ip
        return {
            "ip": remote_ip,
            "client": f"{user_agent.browser.family} {user_agent.browser.version_string}",
            **kwargs,
        }


class DoNothingHandler(BaseHandler):
    def initialize(self):
        pass

    def prepare(self):
        pass

    def check_xsrf_cookie(self):
        pass

    def on_finish(self):
        pass


class Custom404Handler(DoNothingHandler):
    """自定义错误页面"""

    url = ""

    def prepare(self):
        self.error(_("Undefined routing request"), 404)
        self.finish()


class DbQueryHandler(BaseHandler):
    async def pagedata_from_request(self, request, query, columns, orderby="", params=None):
        warnings.warn(
            "The 'pagedata_from_request' method is deprecated, use ORM style query instead",
            DeprecationWarning,
            stacklevel=2,
        )
        if not params:
            params = {}
        if "uid" not in params:
            params["uid"] = self.current_user.id
        return await QueryHelper.pagedata_from_request(request, query, columns, orderby, params)


class Auth:
    def __init__(self, *permission: str | Iterable[str], strategy: Literal["any", "all"] = "any"):
        self.permissions: set[str] = set(chain.from_iterable((p,) if isinstance(p, str) else p for p in permission))
        self.strategy = strategy

    @classmethod
    def referer_check(cls, this):
        """Referer检查
        - `xsrf_cookies=True`且配置`allowed_origins`时，检查Referer
        - 为方便环境变量注入，`allowed_origins`可以配置多个域名（可以只配`hostname`），用逗号分隔
        """
        allowed_origins = {
            p.hostname or p.path
            for p in (
                urllib.parse.urlparse(s.strip())
                for s in (config.get_config("web.allowed_origins") or "").split(",")
                if s
            )
        }
        if not allowed_origins:
            return
        if (referer := this.request.headers.get("referer")) and urllib.parse.urlparse(
            referer
        ).hostname in allowed_origins:
            return
        logging.error(f"Referer check failed: {this.request.full_url()}")
        raise tornado.web.HTTPError(http.HTTPStatus.FORBIDDEN, "Referer check failed")

    @staticmethod
    def _validate_exp(exp) -> None:
        try:
            exp = int(exp)
        except ValueError:
            raise jwt.DecodeError("Expiration Time claim (exp) must be an integer.") from None

        if exp <= datetime.datetime.now(tz=datetime.timezone.utc).timestamp():
            raise jwt.ExpiredSignatureError("Signature has expired")

    async def _has_permission(self, this: BaseHandler) -> bool:
        return await this.current_user.has_perms(*self.permissions, strategy=self.strategy)

    @staticmethod
    def custom_error(this, status_code, reason):
        this.error(_(reason), status_code=status_code)
        this.finish()
        raise tornado.web.HTTPError(status_code, reason=reason)

    @staticmethod
    def token_check(this):
        url = this.request.full_url()
        if "X-Original-Request-URI" in this.request.headers:
            url = this.request.headers["X-Original-Request-URI"]
        return authtoken.validate_url(url, exclude_domain=True)

    @staticmethod
    def simple_token_check(this):
        passed = False
        if simple_token := config.get_config("app.simple_token"):
            passed = simple_token == this.request.headers.get("access-token")

        return passed, TokenStatus.PASSED.value if passed else TokenStatus.INVALID.value

    def __call__(self, method):
        @functools.wraps(method)
        async def wrapper(this: BaseHandler, *args, **kwargs):
            for route_ext in config.get_config("web.trust_routes") or []:
                if re.search(rf"^/api/v\d+{route_ext}$", this.request.path):
                    logging.debug(f"Skip auth check: {this.request.path}")
                    return await method(this, *args, **kwargs)

            if this.current_user is None:
                if this.get_query_argument("_token", "") and this.get_query_argument("_timestamp", ""):
                    # NOTE: 计划废弃
                    passed, msg = self.token_check(this)
                    if not passed:
                        return self.custom_error(this, http.HTTPStatus.UNAUTHORIZED, msg)
                    this.current_user = TokenUser
                    return await method(this, *args, **kwargs)
                if this.request.headers.get("access-token"):
                    # NOTE: 计划废弃
                    passed, msg = self.simple_token_check(this)
                    if not passed:
                        return self.custom_error(this, http.HTTPStatus.UNAUTHORIZED, msg)
                    this.current_user = TokenUser
                    return await method(this, *args, **kwargs)

                # JWT 可能存在于请求头或者请求参数中
                auth_token = this.request.headers.get("Authorization") or this.get_query_argument("_bearer_token", "")
                if auth_token and (secret_key := config.get_config("app.jwt_secret_key")):
                    if (
                        (parts := auth_token.split()) and len(parts) == 2 and parts[0].lower() == "bearer"
                    ):  # 验证头部信息
                        try:
                            payload = jwt.decode(parts[-1], secret_key, algorithms=["HS256"])  # 解码JWT
                            if exp := payload.get("exp"):
                                self._validate_exp(exp)
                            if (path := payload.get("path")) and path != this.request.path:
                                return self.custom_error(this, http.HTTPStatus.UNAUTHORIZED, "JWT path mismatch")
                        except jwt.DecodeError:
                            return self.custom_error(this, http.HTTPStatus.UNAUTHORIZED, "JWT decode error")
                        except jwt.ExpiredSignatureError as e:
                            return self.custom_error(this, http.HTTPStatus.UNAUTHORIZED, str(e))
                        except ValueError as e:
                            return self.custom_error(this, http.HTTPStatus.BAD_REQUEST, str(e))

                        if sub := payload.get("sub"):
                            this.current_user = await pw_db.first(
                                NewAdminUser.select()
                                .where((NewAdminUser.ext_id == sub) | (NewAdminUser.name == sub))
                                .order_by(NewAdminUser.ext_id.desc())
                            )

            if this.current_user is None:
                return self.custom_error(
                    this, http.HTTPStatus.UNAUTHORIZED, "The session has expired, please login again"
                )

            if this.current_user.is_gf_oa_user and not this.get_cookie("SSO_ATTRIBUTE"):
                this.session_clear()
                return self.custom_error(
                    this, http.HTTPStatus.UNAUTHORIZED, "The session has expired, please login again"
                )

            if await self._has_permission(this):
                return await method(this, *args, **kwargs)
            return self.custom_error(this, http.HTTPStatus.FORBIDDEN, "You have no permission")

        return wrapper


@functools.lru_cache()
def compute_etag(path, version=None):
    version_hash = tornado.web.StaticFileHandler.get_content_version(path)
    return f'"{version_hash}"' if version_hash else None


class PermCheckHandler(DbQueryHandler):
    async def has_perms(self, perms: list[str]):
        if not self.current_user:
            return False
        if self.current_user.is_admin:
            return True
        return await self.current_user.has_perms(*perms)

    @property
    def need_folder_permission(self):
        return config.get_config("web.folder_permission") or False

    @staticmethod
    async def treeid_to_pid(treeid):
        tree = await NewFileTree.find_by_id(treeid)
        if not tree:
            raise tornado.web.HTTPError(403, reason="您没有操作该项目的权限")
        return tree.pid

    @staticmethod
    async def fileid_to_pid(treeid):
        _file = await NewFile.find_by_id(treeid)
        if not _file:
            raise tornado.web.HTTPError(403, reason="您没有操作该项目的权限")
        return _file.pid

    async def check_object_uid(self, object_uid):
        if not self.current_user:
            return False
        if object_uid == self.current_user.id:
            return True

        if await self.current_user.has_perms("manage_prj"):
            return True
        # NOTE：订制需求，其实已经破坏了通用的权限控制逻辑
        # https://gitpd.paodingai.com/cheftin/docs_trident/-/issues/254#note_452710
        # "param_perms": [
        #     "prj",
        #     "prj_detail",
        #     "prj_detail_edit"
        # ]
        if await self.current_user.has_perms("add", "del", "edit"):
            return True
        return False

    async def check_project_permission(self, prj_id, project=None, mode="read"):
        if not project:
            project = await NewFileProject.find_by_id(prj_id)
            if not project:
                raise tornado.web.HTTPError(http.HTTPStatus.NOT_FOUND, reason="找不到操作对象")

        if await self.check_object_uid(project.uid):
            return True

        if project.public and (mode == "read" or await self.has_perms(["manage_prj"])):
            return True

        raise tornado.web.HTTPError(403, reason="您没有操作该项目的权限")

    async def check_tree_permission(self, tree_id, tree=None, project=None, mode="read"):
        if not tree:
            tree = await NewFileTree.find_by_id(tree_id)
            if not tree:
                raise tornado.web.HTTPError(http.HTTPStatus.NOT_FOUND, reason="找不到操作对象")

        if not project:
            project = await NewFileProject.find_by_id(tree.pid)
            if not project:
                raise tornado.web.HTTPError(http.HTTPStatus.NOT_FOUND, reason="找不到操作对象")

        if await self.check_object_uid(tree.uid):
            return True

        if project.public and (mode == "read" or await self.has_perms(["manage_prj"])):
            return True

        raise tornado.web.HTTPError(403, reason="您没有操作该项目的权限")

    async def check_file_permission(self, file_id, file=None, mode="read"):
        if not file:
            file = await NewFile.find_by_id(file_id)
            if not file:
                raise tornado.web.HTTPError(http.HTTPStatus.NOT_FOUND, reason="找不到操作对象")

        if await self.check_object_uid(file.uid):
            return True

        if await self.check_tree_permission(file.tree_id, mode=mode):
            return True

        raise tornado.web.HTTPError(403, reason="您没有操作该项目的权限")

    async def check_mold_permission(self, mold_id):
        mold = await NewMold.find_by_id(mold_id)
        if not mold:
            raise tornado.web.HTTPError(http.HTTPStatus.NOT_FOUND, reason="找不到操作对象")

        if await self.check_object_uid(mold.uid):
            return True

        if mold.public and await self.has_perms(["manage_mold"]):
            return True

        raise tornado.web.HTTPError(403, reason="您没有操作该项目的权限")

    async def new_check_mold_permission(self, mold: NewMold):
        if not mold:
            raise tornado.web.HTTPError(http.HTTPStatus.NOT_FOUND, reason="找不到操作对象")

        if await self.check_object_uid(mold.uid):
            return True

        if mold.public and await self.has_perms(["manage_mold"]):
            return True

        raise tornado.web.HTTPError(403, reason="您没有操作该项目的权限")

    async def check_question_permission(self, qid, mode="read"):
        file = await NewFile.find_by_qid(qid)
        if not file:
            raise tornado.web.HTTPError(http.HTTPStatus.NOT_FOUND, reason="找不到操作对象")
        await self.check_file_permission(file.id, mode=mode)

    async def check_user_permission(self, req_uid):
        if await self.check_object_uid(req_uid):
            return True
        if await self.has_perms(["manage_user"]):
            return True

        raise tornado.web.HTTPError(403, reason="您没有操作该项目的权限")

    async def has_question_permission(self, qid):
        try:
            await self.check_question_permission(qid, mode="write")
        except tornado.web.HTTPError as exp:
            if exp.status_code == 401:
                logging.error("need login")
                return False
            if exp.status_code == 403:
                logging.error("no permission")
                return False
            logging.error("unkown status code")
        return True
