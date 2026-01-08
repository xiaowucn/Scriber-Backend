from remarkable.base_handler import PermCheckHandler
from remarkable.common.exceptions import CGSException
from remarkable.plugins import Plugin

plugin = Plugin(__name__)


def init():
    from . import (
        cleanfile_handlers,
        ext_handlers,
        handlers,
    )


class CGSHandler(PermCheckHandler):
    def _handle_request_exception(self, e: BaseException) -> None:
        if isinstance(e, CGSException):
            self.error(message=e.message, errors=e.to_dict())
            self.finish()
            return None
        return super()._handle_request_exception(e)
