import base64
import gettext
import logging
import logging.config
import os
import re
from typing import Any

import httpx
import tornado.httpserver
import tornado.options
import tornado.web
from fastapi import HTTPException
from fastapi.openapi.utils import get_openapi
from httpx import HTTPStatusError
from speedy.middleware.encrypt import EncryptMiddleware
from speedy.middleware.i18n import translate
from speedy.web_api import PaoDingAPI
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_404_NOT_FOUND

from remarkable.base_handler import Custom404Handler, route
from remarkable.common.constants import API_PREFIX_V1, API_PREFIX_V2
from remarkable.common.util import compact_dumps
from remarkable.config import get_config
from remarkable.middleware.header import header_middleware
from remarkable.middleware.pai_wsgi import TornadoMiddleware
from remarkable.middleware.session import SessionMiddleware
from remarkable.middleware.web_logging import logging_middleware
from remarkable.routers import DEBUG_WEBIF, debug_route
from remarkable.routers.answer import answer_router
from remarkable.routers.cmfchina import router as cmfchina_router
from remarkable.routers.external import external_router
from remarkable.routers.file import file_router
from remarkable.routers.law import law_router
from remarkable.routers.law_judge import judge_router
from remarkable.routers.mold import mold_router
from remarkable.routers.nafmii import router as nafmii_router
from remarkable.routers.user import user_router
from remarkable.security.package_encrypt import HexSm4Encryptor, PackageEncrypt

logger = logging.getLogger(__name__)


class HandleDelegate(tornado.web._HandlerDelegate):
    def execute(self):
        if not self.application.settings.get("compiled_template_cache", True):
            with tornado.web.RequestHandler._template_loader_lock:
                for loader in tornado.web.RequestHandler._template_loaders.values():
                    loader.reset()
        if not self.application.settings.get("static_hash_cache", True):
            tornado.web.StaticFileHandler.reset()

        self.handler = self.handler_class(self.application, self.request, **self.handler_kwargs)
        transforms = [t(self.request) for t in self.application.transforms]

        return self.handler._execute(transforms, *self.path_args, **self.path_kwargs)


class Application(tornado.web.Application):
    def __init__(self):
        logger.info("starting remarkable")
        handlers = route.init_handlers()
        settings = {
            "autoreload": (get_config("client.autoreload") or False),  # 与gunicorn启动模式冲突，默认不应该启用
            "default_handler_class": Custom404Handler,
            "compiled_template_cache": False,
            "template_path": "templates",
            "serve_traceback": (get_config("debug") or False),
            "xsrf_cookies": (get_config("web.xsrf_cookies") or False),
            "xsrf_cookie_kwargs": {"httponly": True},
            "cookie_secret": "am.i.clear?",
        }
        tornado.web.Application.__init__(self, handlers, debug=(get_config("debug") or False), **settings)

    def log_request(self, handler):
        if handler.request.path.startswith("/static"):
            return
        if not handler.request.path.startswith(API_PREFIX_V1):
            return
        request_time = 1000.0 * handler.request.request_time()
        uid = handler.current_user.id if handler.current_user else ""
        if uid:
            uid = "UID:{} ".format(uid)
        logging.info(
            f"{handler.get_status()} {handler._request_summary()} {request_time:.2f}ms {uid}",
        )


class TornadoApplication(Application):
    def get_handler_delegate(
        self,
        request,
        target_class,
        target_kwargs=None,
        path_args=None,
        path_kwargs=None,
    ):
        return HandleDelegate(self, request, target_class, target_kwargs, path_args, path_kwargs)


def create_app():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _locales_dir = os.path.join(project_root, "i18n", "locales")
    _language_type = (get_config("client") or {}).get("language", "zh_CN")
    gettext.translation("Scriber-Backend", _locales_dir, languages=[_language_type], fallback=True).install()

    app = PaoDingAPI(get_config("speedy"), docs_url=f"{API_PREFIX_V2}/docs")

    def custom_openapi() -> dict[str, Any]:
        """仅包含部分接口的 OpenAPI docs，用于生成外部 API 文档
        1. 开发接口 xxx
        2. 生成 OpenAPI 文档（仅包含xxx接口）
        3. 将`/api/v2/docs/openapi.json`导入 https://editor-next.swagger.io
        4. 生成&校对外部 API 文档
        """
        target_paths = ()
        if not app.openapi_schema:
            app.openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                openapi_version=app.openapi_version,
                summary=app.summary,
                description=app.description,
                terms_of_service=app.terms_of_service,
                contact=app.contact,
                license_info=app.license_info,
                routes=[r for r in app.routes if r.path in target_paths],
                webhooks=app.webhooks.routes,
                tags=app.openapi_tags,
                servers=app.servers,
                separate_input_output_schemas=app.separate_input_output_schemas,
            )
        return app.openapi_schema

    @app.exception_handler(HTTPStatusError)
    async def httpx_status_error_handler(request, exc: HTTPStatusError):
        return JSONResponse(
            status_code=exc.response.status_code,
            content={"error": "Call API Error", "detail": exc.response.text},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        media_type = "application/json"
        content = compact_dumps(
            {"status": "error", "message": translate(exc.detail), "errors": {}},
            allow_nan=False,
        ).encode("utf-8")
        if (ins := request.app.middleware_stack.app) and isinstance(ins, EncryptMiddleware):
            media_type = "application/binary-json"
            content = ins.encryptor.encrypt(content)
        return Response(content, status_code=exc.status_code, media_type=media_type)

    app.middleware("http")(logging_middleware)
    app.middleware("http")(header_middleware)
    app.add_middleware(SessionMiddleware)
    if DEBUG_WEBIF:
        app.replace_url_int_convertor()  # url允许负id, 暂时只在debug时开
        app.include_router(debug_route, prefix=API_PREFIX_V2)
    for router in (
        law_router,
        judge_router,
        file_router,
        user_router,
        nafmii_router,
        cmfchina_router,
        external_router,
        mold_router,
        answer_router,
    ):
        app.include_router(router, prefix=API_PREFIX_V2)
    tornado_ins = TornadoMiddleware(TornadoApplication())
    app.mount(API_PREFIX_V1, tornado_ins)
    app.mount("/external_api", tornado_ins)

    # 保持 tornado 加密逻辑不变, fastapi skip /api/v1
    if binary_key := (get_config("web.hex_binary_key") or get_config("web.binary_key")):
        if get_config("web.hex_binary_key"):
            encryptor = HexSm4Encryptor(binary_key)
            x_binary_algorithm = "HexSm4"
        else:
            encryptor = PackageEncrypt(binary_key)
            x_binary_algorithm = None
        app.enable_last_encrypt_middleware(
            encryptor=encryptor,
            x_binary_key=base64.b64encode(
                PackageEncrypt((get_config("web.share_key") or "hkx85vMOBSM7M7W")).encrypt(binary_key.encode())
            ).decode(),
            encrypt_list=(get_config("web.encrypted_response_routes") or []),
            decrypt_list=(get_config("web.encrypted_request_routes") or []),
            skip_list=[
                re.compile(r"/api/v1/.*"),
                "/external/.*",
                *(get_config("web.encrypted_skip_routes") or []),
                *[re.compile(rf"{i}") for i in (get_config("web.encrypted_skip_routes_patterns") or [])],
            ],
            enc_error_rsp=True,
            x_binary_algorithm=x_binary_algorithm,
        )

    # 静态文件服务（带认证）
    # 注意：使用 catch-all 路由而不是 mount，确保 API 路由优先
    static_dir = get_config("web.static_dir", "/opt/scriber/remarkable/static")
    fonts_dir = get_config("web.fonts_dir", "/opt/fonts")

    if os.path.exists(static_dir):
        from remarkable.static_files import serve_authenticated_static_file

        # 字体文件路由（带认证）
        if os.path.exists(fonts_dir):

            @app.get("/pdfonts/{file_path:path}", include_in_schema=False)
            async def serve_fonts(file_path: str, request: Request):
                return await serve_authenticated_static_file(request, fonts_dir, file_path)

            logger.info(f"Mounted authenticated font files from {fonts_dir}")

        # 主静态文件路由（带认证）
        # 使用 catch-all 路由，确保在所有 API 路由之后
        @app.get("/{file_path:path}", include_in_schema=False)
        async def serve_static(file_path: str, request: Request):
            return await serve_authenticated_static_file(request, static_dir, file_path, html=True)

        logger.info(f"Mounted authenticated static files from {static_dir}")
    else:
        # 本地开发环境：代理到前端服务器
        @app.get("/{path:path}", include_in_schema=False)
        async def front_proxy(path: str, response: Response):
            """
            转发目标服务器前端资源到本地开发环境，方便本地开发调试
            需要确保最后载入本接口
            """
            if path.startswith("api/v"):
                response.status_code = HTTP_404_NOT_FOUND
                return response
            backend = get_config("web.debug_frontend_upstream")
            if not backend:
                backend = f"http://{get_config('web.domain')}"
            backend_url = f"{backend.rstrip('/')}/{path.lstrip('/')}"

            async with httpx.AsyncClient(verify=False) as client:
                proxy = await client.get(backend_url, headers={"User-Agent": "Chrome"})
            response.body = proxy.content
            response.status_code = proxy.status_code
            response.headers["content-type"] = proxy.headers["content-type"]
            if path:
                response.headers["cache-control"] = "max-age=36000"
            return response

        logger.info("Using frontend proxy for local development")

    # 按需放开以生成订制 OpenAPI 文档
    # app.openapi = custom_openapi
    return app
