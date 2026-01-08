import collections
import functools
from typing import Any, Callable
from urllib.parse import urljoin

from requests import Request, Response
from requests.cookies import extract_cookies_to_jar
from requests.utils import get_encoding_from_headers
from tornado.httpclient import HTTPRequest, HTTPResponse, AsyncHTTPClient
from tornado.log import gen_log
from tornado.netutil import Resolver, OverrideResolver
from tornado.simple_httpclient import _HTTPConnection, HTTPTimeoutError
from tornado.tcpclient import TCPClient
from tornado.util import Configurable


def make_response(req: Request, resp: HTTPResponse) -> Response:
    response = Response()
    response.status_code = getattr(resp, "code", None)
    response.headers = dict(resp.headers)
    response.encoding = get_encoding_from_headers(response.headers)
    response.raw = resp
    response.reason = response.raw.reason
    response._content = resp.body

    if isinstance(req.url, bytes):
        response.url = req.url.decode("utf-8")
    else:
        response.url = req.url
    extract_cookies_to_jar(response.cookies, req, resp)
    response.request = req
    return response

class AsyncClient(AsyncHTTPClient):
    @classmethod
    def configurable_base(cls) -> type[Configurable]:
        return AsyncClient

    @classmethod
    def configurable_default(cls) -> type[Configurable]:
        return SimpleAsyncHTTPClient

    def __new__(cls, http_server, force_instance: bool = False, **kwargs: Any) -> "AsyncHTTPClient":
        instance = super().__new__(cls, force_instance, **kwargs)
        instance._http_server = http_server

        return instance

    def fetch(self, request: str | HTTPRequest, raise_error: bool = True,
              **kwargs: Any) -> "Future[HTTPResponse]":

        url = self.get_url(request, kwargs.pop("api_version", ""))
        return super().fetch(url, raise_error, **kwargs)

    async def get(self, url, **kwargs):
        return await self._send(url, method="GET", **kwargs)

    async def post(self, url, files=None, data=None, json_data=None, **kwargs):
        return await self._send(url, method="POST", files=files, data=data, json_data=json_data, **kwargs)

    async def put(self, url, files=None, data=None, json_data=None, **kwargs):
        return await self._send(url, method="PUT", files=files, data=data, json_data=json_data, **kwargs)

    async def delete(self, url, files=None, data=None, json_data=None, **kwargs):
        return await self._send(url, method="DELETE", files=files, data=data, json_data=json_data, **kwargs)

    async def _send(self, url: str, method="GET", data=None, json_data=None, files=None, headers=None, api_version="v1", **kwargs) -> Response:
        if not url.startswith("http"):
            version = kwargs.pop("api_version", None)
            if version is not None:
                api_version = version
            url = self.get_url(url, api_version)
        request = Request(url=url, files=files, data=data, json=json_data)
        request_data = request.prepare()
        if headers is None:
            headers = {}
        headers.update(request_data.headers)

        resp = await super().fetch(
            url, raise_error=False, method=method, headers=headers, body=request_data.body, allow_nonstandard_methods=True, **kwargs
        )
        response = make_response(request, resp)

        return response

    def get_protocol(self):
        return "http"

    def get_http_port(self):
        for sock in self._http_server._sockets.values():
            return sock.getsockname()[1]

    def get_url(self, sub_path: str, api_version: str = ""):
        prefix = ""
        if api_version:
            prefix = f"/api/{api_version}/"
            sub_path = sub_path.lstrip("/")

        path = f"{prefix}{sub_path}"

        base_url = f"{self.get_protocol()}://127.0.0.1:{self.get_http_port()}"
        return urljoin(base_url, path)

    @staticmethod
    def get_data(response, name=None):
        data = response.json()["data"]
        if name:
            return data[name]

        return data

# copy from tornado.simple_httpclient.SimpleAsyncHTTPClient
class SimpleAsyncHTTPClient(AsyncClient):
    def initialize(  # type: ignore
        self,
        max_clients: int = 10,
        hostname_mapping: dict[str, str] | None = None,
        max_buffer_size: int = 104857600,
        resolver: Resolver | None = None,
        defaults: dict[str, Any] | None = None,
        max_header_size: int | None = None,
        max_body_size: int | None = None,
    ) -> None:
        super().initialize(defaults=defaults)
        self.max_clients = max_clients
        self.queue: collections.deque[tuple[object, HTTPRequest, Callable[[HTTPResponse], None]]] = (
            collections.deque()
        )
        self.active: dict[object, tuple[HTTPRequest, Callable[[HTTPResponse], None]]] = {}
        self.waiting: dict[object, tuple[HTTPRequest, Callable[[HTTPResponse], None], object]] = {}
        self.max_buffer_size = max_buffer_size
        self.max_header_size = max_header_size
        self.max_body_size = max_body_size
        # TCPClient could create a Resolver for us, but we have to do it
        # ourselves to support hostname_mapping.
        if resolver:
            self.resolver = resolver
            self.own_resolver = False
        else:
            self.resolver = Resolver()
            self.own_resolver = True
        if hostname_mapping is not None:
            self.resolver = OverrideResolver(
                resolver=self.resolver, mapping=hostname_mapping
            )
        self.tcp_client = TCPClient(resolver=self.resolver)

    def close(self) -> None:
        super().close()
        if self.own_resolver:
            self.resolver.close()
        self.tcp_client.close()

    def fetch_impl(
        self, request: HTTPRequest, callback: Callable[[HTTPResponse], None]
    ) -> None:
        key = object()
        self.queue.append((key, request, callback))
        assert request.connect_timeout is not None
        assert request.request_timeout is not None
        timeout_handle = None
        if len(self.active) >= self.max_clients:
            timeout = (
                min(request.connect_timeout, request.request_timeout)
                or request.connect_timeout
                or request.request_timeout
            )  # min but skip zero
            if timeout:
                timeout_handle = self.io_loop.add_timeout(
                    self.io_loop.time() + timeout,
                    functools.partial(self._on_timeout, key, "in request queue"),
                )
        self.waiting[key] = (request, callback, timeout_handle)
        self._process_queue()
        if self.queue:
            gen_log.debug(
                "max_clients limit reached, request queued. "
                "%d active, %d queued requests." % (len(self.active), len(self.queue))
            )

    def _process_queue(self) -> None:
        while self.queue and len(self.active) < self.max_clients:
            key, request, callback = self.queue.popleft()
            if key not in self.waiting:
                continue
            self._remove_timeout(key)
            self.active[key] = (request, callback)
            release_callback = functools.partial(self._release_fetch, key)
            self._handle_request(request, release_callback, callback)

    def _connection_class(self) -> type:
        return _HTTPConnection

    def _handle_request(
        self,
        request: HTTPRequest,
        release_callback: Callable[[], None],
        final_callback: Callable[[HTTPResponse], None],
    ) -> None:
        self._connection_class()(
            self,
            request,
            release_callback,
            final_callback,
            self.max_buffer_size,
            self.tcp_client,
            self.max_header_size,
            self.max_body_size,
        )

    def _release_fetch(self, key: object) -> None:
        del self.active[key]
        self._process_queue()

    def _remove_timeout(self, key: object) -> None:
        if key in self.waiting:
            request, callback, timeout_handle = self.waiting[key]
            if timeout_handle is not None:
                self.io_loop.remove_timeout(timeout_handle)
            del self.waiting[key]

    def _on_timeout(self, key: object, info: str | None = None) -> None:
        """Timeout callback of request.

        Construct a timeout HTTPResponse when a timeout occurs.

        :arg object key: A simple object to mark the request.
        :info string key: More detailed timeout information.
        """
        request, callback, timeout_handle = self.waiting[key]
        self.queue.remove((key, request, callback))

        error_message = "Timeout {0}".format(info) if info else "Timeout"
        timeout_response = HTTPResponse(
            request,
            599,
            error=HTTPTimeoutError(error_message),
            request_time=self.io_loop.time() - request.start_time,
        )
        self.io_loop.add_callback(callback, timeout_response)
        del self.waiting[key]
