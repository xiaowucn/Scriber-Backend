from dataclasses import dataclass, field
from pathlib import PurePath

from tornado.httputil import HTTPFile

from remarkable.base_handler import route
from remarkable.common.exceptions import CustomError
from remarkable.common.util import simple_match_ext
from remarkable.config import get_config


class Plugin:
    def __init__(self, name):
        self.name = name
        prefix = "remarkable.plugins."
        if self.name.startswith(prefix):
            self.name = self.name[len(prefix) :]

    def route(self, router_url, prefix="/api/v1", use_common_prefix=False):
        if use_common_prefix:
            return route(router_url, prefix=prefix)
        else:
            return route(router_url, prefix=prefix + "/plugins/" + self.name)


class PostFileValidator:
    valid_suffixes = (".docx", ".doc", ".pdf")
    size_limit = 20  # 20M

    @classmethod
    def check_size(cls, file: HTTPFile):
        size_limit = get_config("client.file_size_limit") or cls.size_limit
        if len(file.body) > size_limit * 1024 * 1024:
            raise CustomError(f"文件超过{size_limit}M", resp_status_code=400)

    @classmethod
    def check_suffix(cls, file: HTTPFile):
        if not simple_match_ext(PurePath(file.filename).suffix, file.body, *cls.valid_suffixes):
            raise CustomError("文件类型不支持", resp_status_code=400)

    @classmethod
    def check(cls, file: HTTPFile):
        cls.check_size(file)
        cls.check_suffix(file)


@dataclass
class HTTPFileValidator:
    valid_suffixes: tuple[str, ...] = (".docx", ".doc", ".pdf")
    size_limit: int = field(default=20)

    def check_size(self, file: HTTPFile):
        if len(file.body) > self.size_limit * 1024 * 1024:
            raise CustomError(f"文件超过{self.size_limit}M", resp_status_code=400)

    def check_suffix(self, file: HTTPFile):
        if not simple_match_ext(PurePath(file.filename).suffix, file.body, *self.valid_suffixes):
            raise CustomError("文件类型不支持", resp_status_code=400)

    def __call__(self, file: HTTPFile):
        self.check_size(file)
        self.check_suffix(file)
