from typing import Literal

import redis
from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from remarkable import logger
from remarkable.common.constants import API_PREFIX_V2
from remarkable.common.util import need_secure_cookie
from remarkable.security.package_encrypt import aes_load
from remarkable.session import SessionManager


class SessionMiddleware:
    """传入`session`实例，可读写`cookie`"""

    def __init__(
        self,
        app: ASGIApp,
        session_cookie: str = "scriber_app_id",
        path: str = "/",
        same_site: Literal["lax", "strict", "none"] = "none",
    ) -> None:
        self.app = app
        self.session_cookie = session_cookie
        self.path = path
        self.security_flags = "httponly; "
        if need_secure_cookie:  # Secure flag can be used with HTTPS only
            self.security_flags += f"samesite={same_site}; secure"
        else:
            if same_site == "none":
                same_site = "lax"
            self.security_flags += f"samesite={same_site}"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or not scope.get("path", "").startswith(API_PREFIX_V2)
            or scope.get("skip_set_cookie")
        ):  # pragma: no cover
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                session = SessionManager(connection=HTTPConnection(scope), headers=MutableHeaders(scope=message))
                if self.session_cookie not in session.connection.cookies:
                    # 确保前端在未登录状态拿到`session_id`前缀
                    session.headers.append(
                        "Set-Cookie",
                        f"{self.session_cookie}={session.APP_NAME}; path={self.path}; {self.security_flags}",
                    )
                try:
                    encrypted_data = session.get_cookie(session.SESSION_ID_NAME)
                    if (
                        not encrypted_data
                        or aes_load(session.aesgcm, data=encrypted_data.encode()) != session.session_id
                    ):
                        # 浏览器`session_id`未指定或者与服务端不一致时，更新`session_id`
                        session.headers.append(
                            "Set-Cookie",
                            f"{session.SESSION_ID_NAME}={session.encrypted_session_id}; path={self.path}; {self.security_flags}",
                        )
                    session.refresh()
                except redis.exceptions.ConnectionError as exp:
                    logger.warning(f"Unable to connect to redis: {exp}")
                except Exception as exp:
                    logger.error(f"Error while processing session: {exp}")
                    session.headers.append(
                        "Set-Cookie",
                        f"{self.session_cookie}=; path={self.path}; expires=Thu, 01 Jan 1970 00:00:00 GMT; {self.security_flags}",
                    )
                    session.headers.append(
                        "Set-Cookie",
                        f"{session.SESSION_ID_NAME}=; path={self.path}; expires=Thu, 01 Jan 1970 00:00:00 GMT; {self.security_flags}",
                    )
            await send(message)

        await self.app(scope, receive, send_wrapper)
