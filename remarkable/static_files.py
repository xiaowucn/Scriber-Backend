"""
静态文件服务函数，支持基于 session 的认证和预压缩文件
"""

import logging
import mimetypes
from pathlib import Path

from starlette.requests import Request
from starlette.responses import FileResponse, RedirectResponse, Response
from starlette.status import HTTP_404_NOT_FOUND

from remarkable import config
from remarkable.dependencies import get_current_user

logger = logging.getLogger(__name__)


# 公开路径列表（无需认证）
PUBLIC_PATHS = {"/", "/index.html", "/index.htm"}


def _get_login_redirect_url() -> str:
    """
    获取登录重定向 URL

    如果配置了 Trident，重定向到 Trident 首页
    否则重定向到本地登录页
    """
    # 检查是否配置了 Trident
    user_system_provider = config.get_config("web.user_system_provider", "self")

    if user_system_provider == "trident":
        # 使用 Trident 用户系统
        trident_url = config.get_config("app.auth.trident.url")
        if trident_url:
            return trident_url

    # 默认重定向到本地登录页
    return "/"


def _is_public_path(path: str) -> bool:
    """
    检查路径是否是公开路径

    规则：
    - 如果使用 Trident 用户系统，所有路径都不公开（包括空路径、登录页）
    - 如果使用本地用户系统，登录页公开
    """
    # 检查是否使用 Trident 用户系统
    user_system_provider = config.get_config("web.user_system_provider", "self")

    if user_system_provider == "trident":
        # Trident 模式：所有路径都需要认证（无例外）
        return False

    # 本地用户系统：登录页公开
    return path in PUBLIC_PATHS


async def _is_authenticated(request: Request) -> bool:
    """
    检查用户是否已认证

    复用 get_current_user 的认证逻辑，支持：
    - Session（cookie）
    - JWT（Bearer token）
    - Simple token（access-token header）
    """
    try:
        # 使用 get_current_user 检查认证
        # 如果认证失败，会抛出 HTTPException
        user = await get_current_user(request, None)
        return user is not None

    except Exception as e:
        # 认证失败（包括 HTTPException）
        logger.debug(f"Authentication failed: {e}")
        return False


async def _try_precompressed(request: Request, directory: Path, file_path: str) -> FileResponse | None:
    """
    尝试返回预压缩文件

    优先级：zstd > gzip

    Returns:
        FileResponse: 成功找到预压缩文件
        None: 没有找到预压缩文件或客户端不支持
    """
    # 检查客户端支持的编码
    accept_encoding = request.headers.get("accept-encoding", "").lower()

    # 构建完整文件路径
    full_path = directory / file_path.lstrip("/")

    # 按优先级尝试预压缩文件
    encodings = []
    if "zstd" in accept_encoding:
        encodings.append(("zstd", ".zst"))
    if "gzip" in accept_encoding:
        encodings.append(("gzip", ".gz"))

    for encoding, suffix in encodings:
        precompressed_path = Path(str(full_path) + suffix)

        if precompressed_path.exists() and precompressed_path.is_file():
            logger.debug(f"Serving precompressed file: {precompressed_path}")

            # 根据原始文件路径（不含压缩后缀）推断正确的 media_type
            # 例如：index.html.gz -> 根据 index.html 推断为 text/html
            # 而不是根据 .gz 推断为 application/gzip
            media_type, _ = mimetypes.guess_type(str(full_path))

            return FileResponse(
                path=precompressed_path,
                media_type=media_type,
                headers={
                    "Content-Encoding": encoding,
                    "Vary": "Accept-Encoding",
                },
            )

    return None


async def serve_authenticated_static_file(
    request: Request,
    directory: str | Path,
    file_path: str,
    html: bool = False,
) -> Response:
    """
    服务静态文件，支持认证和预压缩

    规则：
    1. 本地用户系统：登录页（/ 或 /index.html）无需认证，其他资源需要认证
    2. Trident 用户系统：所有资源都需要认证（包括登录页）
    3. 未认证用户重定向到登录页（本地）或 Trident 首页
    4. 支持预压缩文件：优先返回 .gz 或 .zst 文件（如果存在且客户端支持）

    Args:
        request: Starlette Request 对象
        directory: 静态文件目录
        file_path: 请求的文件路径
        html: 是否支持 HTML 模式（空路径返回 index.html）

    Returns:
        Response: 文件响应或重定向响应
    """
    directory = Path(directory)

    # 处理空路径（根路径）
    if not file_path or file_path == "/":
        file_path = "index.html" if html else ""

    # 检查是否是公开路径（登录页）
    # 注意：空路径会被规范化为 "/"
    if not file_path or file_path == "/":
        request_path = "/"
    elif file_path.startswith("/"):
        request_path = file_path
    else:
        request_path = f"/{file_path}"

    # 检查认证
    if config.get_config("web.user_system_provider", "self") != "self":
        is_public = _is_public_path(request_path)
        if not is_public and not await _is_authenticated(request):
            # 未认证，重定向到登录页（或 Trident 首页）
            redirect_url = _get_login_redirect_url()
            return RedirectResponse(url=redirect_url, status_code=302)

    # 尝试返回预压缩文件
    precompressed_response = await _try_precompressed(request, directory, file_path)
    if precompressed_response:
        return precompressed_response

    # 返回原始文件
    full_path = directory / file_path.lstrip("/")

    if not full_path.exists():
        # 文件不存在
        if html and file_path != "index.html":
            # HTML 模式：尝试返回 index.html（SPA 路由）
            index_path = directory / "index.html"
            if index_path.exists():
                return FileResponse(path=index_path)

        return Response(content="Not Found", status_code=HTTP_404_NOT_FOUND)

    if not full_path.is_file():
        return Response(content="Not Found", status_code=HTTP_404_NOT_FOUND)

    return FileResponse(path=full_path)
