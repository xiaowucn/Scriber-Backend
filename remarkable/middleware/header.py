from starlette.requests import Request

from remarkable.common.constants import API_PREFIX_V2


async def header_middleware(request: Request, call_next):
    response = await call_next(request)
    if not request.url.path.startswith(API_PREFIX_V2):
        return response

    if request.url.path.startswith("/api/v"):
        response.headers["Cache-Control"] = "no-cache"
    # avoid Clickjacking: https://www.ietf.org/rfc/rfc7034.txt
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Server"] = "*"
    return response
