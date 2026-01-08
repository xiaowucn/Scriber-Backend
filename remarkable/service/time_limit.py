import random
import string
from datetime import datetime
from pathlib import Path
from types import FunctionType

import attrs
from filelock import FileLock

from remarkable.config import dump_confusion, get_config, load_confusion


def attr2dict(obj):
    def _filter(key, val):
        if key.name.startswith("_") or key.name.endswith("_func"):
            return False
        if getattr(obj, "RENDER_WHITELIST", None) and key.name in obj.RENDER_WHITELIST:
            return True
        if getattr(obj, "RENDER_BLACKLIST", None) and key.name in obj.RENDER_BLACKLIST:
            return False
        if isinstance(val, (FunctionType, datetime)):
            return False
        return True

    return attrs.asdict(obj, filter=_filter)


def _conv2timestamp(date: str | datetime | int = None) -> int:
    if date is None:
        date = datetime.utcnow()
    if isinstance(date, str):
        return int(datetime.strptime(date, "%Y-%m-%d %H:%M:%S").timestamp())
    return int(date.timestamp()) if isinstance(date, datetime) else date


def _intime2str(date: datetime | None = None) -> str:
    if date is None:
        date = int(datetime.utcnow().timestamp())
    return datetime.fromtimestamp(date).strftime("%Y-%m-%d %H:%M:%S")


def random_str(length: int = 8) -> str:
    return "".join(random.choices(string.printable, k=length))


@attrs.define
class PathInfo:
    RENDER_BLACKLIST = ("locker", "path")
    path: Path = attrs.field(converter=Path)
    now_time: int = attrs.field(default=attrs.Factory(_conv2timestamp), converter=_conv2timestamp, repr=_intime2str)
    _locker: FileLock = attrs.field(init=False)

    def __attrs_post_init__(self):
        self._locker = FileLock(self.path.as_posix() + ".lock")

    def save(self, now_time: datetime = None):
        now_time = _conv2timestamp(now_time)
        if now_time > self.now_time:
            self.now_time = now_time
        real_data = dump_confusion(attr2dict(self))
        offset = random.randint(50, 100)
        header = dump_confusion(f"v1\n{offset}\n{len(real_data) + offset}\n".encode("utf-8"))
        data = (
            header
            + random_str(offset - len(header)).encode("utf-8")
            + real_data
            + random_str(offset**3).encode("utf-8")
        )
        with self._locker:
            self.path.write_bytes(data)

    def read(self):
        if not self.path.exists():
            self.save()
        data = self.path.read_bytes()
        ver, start, end, *_ = load_confusion(data.split(b"\n", 1)[0]).decode("utf-8").split("\n")
        assert ver == "v1", "version error"
        self.now_time = load_confusion(data[int(start) : int(end)])["now_time"]
        return self


@attrs.define
class TimeLimit:
    expire_at: int = attrs.field(default=0, converter=_conv2timestamp, repr=_intime2str)
    path: PathInfo = attrs.field(
        default=Path("/tmp/patch_00"), converter=lambda x: x if isinstance(x, PathInfo) else PathInfo(x)
    )
    enable: bool = attrs.field(default=False)
    offset: int = attrs.field(default=28800)

    def sync_times(self, *times: list[datetime] | None):
        self.path.save(max(times + (datetime.utcnow(),)))

    @property
    def is_expired(self):
        if not self.enable:
            return False
        return self.expire_at < (self.path.read().now_time - self.offset)

    @classmethod
    def check(cls, this=None, config=None):
        instance = cls(**(config or get_config("time_limit") or {}))
        if not instance.enable:
            return False

        times = []
        if this and "X-Date" in this.request.headers:
            # 从前端请求中获取当前最新时间
            date_str = this.request.headers["X-Date"]
            times.append(datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S GMT"))
        instance.sync_times(*times)
        return instance.is_expired
