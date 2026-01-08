import asyncio
import contextvars
import functools
import gettext
import os
import sys
import urllib.parse as urllib_parse
from typing import Any

from a2wsgi.wsgi import Body, WSGIResponder, unicode_to_wsgi
from a2wsgi.wsgi_typing import Environ, StartResponse
from starlette.types import Receive, Scope, Send
from tornado import httputil
from tornado.concurrent import Future
from tornado.escape import native_str

from remarkable.config import get_config, project_root


# WSGI has no facilities for flow control, so just return an already-done
# Future when the interface requires it.
def _dummy_future():
    f = Future()
    f.set_result(None)
    return f


class _WSGIRequestContext:
    def __init__(self, remote_ip, protocol):
        self.remote_ip = remote_ip
        self.protocol = protocol

    def __str__(self):
        return self.remote_ip


class _WSGIConnection(httputil.HTTPConnection):
    def __init__(self, method, start_response, context):
        self.method = method
        self.start_response = start_response
        self.context = context
        self._write_buffer = []
        self._finished = False
        self._expected_content_remaining = None
        self._error = None

    def set_close_callback(self, callback):
        # WSGI has no facility for detecting a closed connection mid-request,
        # so we can simply ignore the callback.
        pass

    def write_headers(self, start_line, headers, chunk=None, callback=None):
        if self.method == "HEAD":
            self._expected_content_remaining = 0
        elif "Content-Length" in headers:
            self._expected_content_remaining = int(headers["Content-Length"])
        else:
            self._expected_content_remaining = None
        self.start_response(
            "%d %s" % (start_line.code, start_line.reason),
            [(native_str(k), native_str(v)) for (k, v) in headers.get_all()],
        )
        if chunk is not None:
            self.write(chunk, callback)
        elif callback is not None:
            callback()
        return _dummy_future()

    def write(self, chunk, callback=None):
        if self._expected_content_remaining is not None:
            self._expected_content_remaining -= len(chunk)
            if self._expected_content_remaining < 0:
                self._error = httputil.HTTPOutputError("Tried to write more data than Content-Length")
                raise self._error
        self._write_buffer.append(chunk)
        if callback is not None:
            callback()
        return _dummy_future()

    def finish(self):
        if self._expected_content_remaining is not None and self._expected_content_remaining != 0:
            self._error = httputil.HTTPOutputError(
                f"Tried to write {self._expected_content_remaining} bytes less than Content-Length"
            )
            raise self._error
        self._finished = True


class WSGIAdapter:
    def __init__(self, app):
        self.app = app

    async def __call__(self, environ: Environ, start_response: StartResponse) -> list[bytes]:
        method = environ["REQUEST_METHOD"]
        uri = urllib_parse.quote(environ.get("SCRIPT_NAME", ""))
        uri += urllib_parse.quote(environ.get("PATH_INFO", ""))
        if environ.get("QUERY_STRING"):
            uri += "?" + environ["QUERY_STRING"]
        headers = httputil.HTTPHeaders()
        if environ.get("CONTENT_TYPE"):
            headers["Content-Type"] = environ["CONTENT_TYPE"]
        if environ.get("CONTENT_LENGTH"):
            headers["Content-Length"] = environ["CONTENT_LENGTH"]
        for key in environ:
            if key.startswith("HTTP_"):
                headers[key[5:].replace("_", "-")] = environ[key]
        if headers.get("Content-Length"):
            body = await environ["wsgi.input"].aread(int(headers["Content-Length"]))
        else:
            body = b""
        protocol = environ["wsgi.url_scheme"]
        remote_ip = environ.get("REMOTE_ADDR", "")
        if environ.get("HTTP_HOST"):
            host = environ["HTTP_HOST"]
        else:
            host = environ["SERVER_NAME"]
        connection = _WSGIConnection(method, start_response, _WSGIRequestContext(remote_ip, protocol))
        request = httputil.HTTPServerRequest(
            method,
            uri,
            "HTTP/1.1",
            headers=headers,
            body=body,
            host=host,
            connection=connection,
        )
        # 问题根源：Tornado 6.5.0 将 _parse_body() 调用从 HTTPConnection.finish_request()
        # 移动到了 RequestHandler._execute()，导致 WSGIAdapter 的预调用与 RequestHandler
        # 的调用产生重复解析。
        #
        # 解决方案：通过检查实际的解析状态（files/body_arguments）来避免重复解析。

        def is_body_parsed(req):
            """检查请求体是否已经被解析过"""
            # 如果有文件或 body_arguments，说明已经解析过
            return len(req.files) > 0 or len(req.body_arguments) > 0

        # 如果还没有解析过，则进行解析
        if not is_body_parsed(request):
            request._parse_body()

        # 创建智能的 _parse_body 方法，避免重复解析
        original_parse_body = request._parse_body

        def smart_parse_body():
            """智能解析方法：检查实际解析状态，避免重复解析"""
            if is_body_parsed(request):
                # 已经解析过（有文件或参数），直接返回
                return
            # 未解析过，执行原始解析
            original_parse_body()

        # 替换为智能解析方法
        request._parse_body = smart_parse_body

        await self.app(request)
        if connection._error:
            raise connection._error
        if not connection._finished:
            raise Exception("request did not finish synchronously")
        return connection._write_buffer


class TornadoMiddleware:
    __name__ = "TornadoMiddleware"

    def __init__(self, app, send_queue_size: int = 10) -> None:
        self.app = WSGIAdapter(app)
        _locales_dir = os.path.join(project_root, "i18n", "locales")
        _language_type = (get_config("client") or {}).get("language", "en")
        gettext.translation("Scriber-Backend", _locales_dir, languages=[_language_type], fallback=True).install()
        self.executor = None
        self.send_queue_size = send_queue_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            responder = _WSGIResponder(self.app, self.executor, self.send_queue_size)
            return await responder(scope, receive, send)


class _Body(Body):
    async def _areceive_more_data(self) -> bytes:
        if not self._has_more:
            return b""
        message = await self.receive()
        self._has_more = message.get("more_body", False)
        return message.get("body", b"")

    async def aread(self, size: int = -1) -> bytes:
        while size == -1 or size > len(self.buffer):
            self.buffer.extend(await self._areceive_more_data())
            if not self._has_more:
                break
        if size == -1:
            result = bytes(self.buffer)
            self.buffer.clear()
        else:
            result = bytes(self.buffer[:size])
            del self.buffer[:size]
        return result


def _build_environ(scope: Scope, body: _Body) -> Environ:
    """
    Builds a scope and request body into a WSGI environ object.
    """
    script_name = scope.get("root_path", "")
    path_info = scope["path"]
    if path_info.startswith(script_name):
        path_info = path_info[len(script_name) :]

    script_name_environ_var = os.environ.get("SCRIPT_NAME", "")
    if script_name_environ_var:
        script_name = unicode_to_wsgi(script_name_environ_var)

    environ: Environ = {
        "asgi.scope": scope,
        "REQUEST_METHOD": scope["method"],
        "SCRIPT_NAME": script_name,
        "PATH_INFO": path_info,
        "QUERY_STRING": scope["query_string"].decode("ascii"),
        "SERVER_PROTOCOL": f"HTTP/{scope['http_version']}",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": scope.get("scheme", "http"),
        "wsgi.input": body,
        "wsgi.errors": sys.stdout,
        "wsgi.multithread": True,
        "wsgi.multiprocess": True,
        "wsgi.run_once": False,
    }

    # Get server name and port - required in WSGI, not in ASGI
    server_addr, server_port = scope.get("server") or ("localhost", 80)
    environ["SERVER_NAME"] = server_addr
    environ["SERVER_PORT"] = str(server_port or 0)

    # Get client IP address
    client = scope.get("client")
    if client is not None:
        addr, port = client
        environ["REMOTE_ADDR"] = addr
        environ["REMOTE_PORT"] = str(port)

    # Go through headers and make them into environ entries
    for name, value in scope.get("headers", []):
        name = name.decode("latin1")
        if name == "content-length":
            corrected_name = "CONTENT_LENGTH"
        elif name == "content-type":
            corrected_name = "CONTENT_TYPE"
        else:
            corrected_name = f"HTTP_{name}".upper().replace("-", "_")
        # HTTPbis say only ASCII chars are allowed in headers, but we latin1 just in case
        value = value.decode("latin1")
        if corrected_name in environ:
            value = environ[corrected_name] + "," + value
        environ[corrected_name] = value
    return environ


class _WSGIResponder(WSGIResponder):
    def send(self, message: Any) -> None:
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is self.loop:
            # Already on the same loop; avoid run_coroutine_threadsafe deadlock.
            try:
                self.send_queue.put_nowait(message)
            except asyncio.QueueFull:
                # Schedule a background put to avoid blocking the current loop turn.
                self.loop.create_task(self.send_queue.put(message))
        else:
            super().send(message)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        body = _Body(self.loop, receive)
        environ = _build_environ(scope, body)
        sender = None
        try:
            sender = self.loop.create_task(self.sender(send))
            context = contextvars.copy_context()
            func = functools.partial(context.run, self.awsgi)
            await func(environ, self.start_response)
            await self.send_queue.put(None)
            await sender
            if self.exc_info is not None:
                raise self.exc_info[0].with_traceback(self.exc_info[1], self.exc_info[2])
        finally:
            if sender and not sender.done():
                sender.cancel()  # pragma: no cover

    def start_response(
        self,
        status: str,
        response_headers: list[tuple[str, str]],
        exc_info: Any = None,
    ) -> None:
        self.exc_info = exc_info
        if not self.response_started:
            self.response_started = True
            status_code_string, _ = status.split(" ", 1)
            status_code = int(status_code_string)
            headers = [
                (name.strip().encode("latin1").lower(), value.strip().encode("latin1"))
                for name, value in response_headers
            ]
            self.send(
                {
                    "type": "http.response.start",
                    "status": status_code,
                    "headers": headers,
                }
            )

    async def awsgi(self, environ: Environ, start_response: StartResponse) -> None:
        for chunk in await self.app(environ, start_response):
            self.send({"type": "http.response.body", "body": chunk, "more_body": True})

        self.send({"type": "http.response.body", "body": b""})
