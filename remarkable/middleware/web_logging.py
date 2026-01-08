import logging
import time

from fastapi import Request
from traceback_with_variables import LoggerAsFile, printing_exc

from remarkable.common.constants import API_PREFIX_V1
from remarkable.config import get_config

logger = logging.getLogger("router")
log_level = get_config("logging.level", "info")  # only info/debug is allowed
logging.basicConfig(
    level=logging.INFO if log_level.upper() == "INFO" else logging.DEBUG,
    format="%(asctime)s - [%(levelname)s] [%(threadName)s] (%(module)s:%(lineno)d) %(message)s",
)


def get_request_ip(request: Request) -> str:
    return request.headers.get("X-Forwarded-For") or request.headers.get("X-Real-IP") or request.client.host


async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    with printing_exc(file_=LoggerAsFile(logger, separate_lines=True)):
        try:
            response = await call_next(request)
        except tuple(request.app.exception_handlers) as exp:
            logger.exception(exp)
            response = await request.app.exception_handlers[exp.__class__](request, exp)

    if request.url.path.startswith(API_PREFIX_V1):
        return response

    logging_func = logger.info if response.status_code < 400 else logger.error
    if request.url.path.startswith("/static"):
        logging_func = logger.debug
    if "session" in request.scope:
        uid = request.scope["session"].user_id
    else:
        uid = "-1"
    logging_func(
        f"{response.status_code} {request.method} {request.url.path}{('?' + request.url.query) if request.url.query else ''}"
        f" ({get_request_ip(request)}) {round((time.time() - start_time) * 1000, 2)}ms UID:{uid}"
    )
    return response
