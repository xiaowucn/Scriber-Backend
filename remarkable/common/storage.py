import gzip
import hashlib
import logging
import os
import shutil
import string
import time
from pathlib import Path
from typing import AsyncGenerator

from cryptography.fernet import Fernet

from remarkable import config
from remarkable.common.util import custom_async_open, run_singleton_task
from remarkable.config import get_config
from remarkable.db import init_rdb

logger = logging.getLogger(__name__)


class LocalStorage:
    valid_chars = string.ascii_lowercase + string.digits
    cache_root = "pdf_cache"
    label_cache_dir = "label_cache"
    ignored_dirs = [cache_root, label_cache_dir]

    def __init__(self, root):
        self.root = os.path.abspath(root)
        if not os.path.exists(root):
            os.makedirs(root)

    @staticmethod
    def _lock_key(path):
        return f"write_file:{hashlib.md5(path.encode()).hexdigest()}"

    def _acquire_lock(self, path):
        """Note: This file lock will be automatically released after a few minutes(30~60)."""
        return run_singleton_task(lambda: None, lock_key=self._lock_key(path))

    def _release_lock(self, path):
        key = f"lock:{self._lock_key(path)}"
        if init_rdb().exists(key):
            init_rdb().delete(key)

    def mount(self, path):
        if path.startswith("/"):
            return path
        return os.path.join(self.root, path)

    def size(self, path):
        return os.path.getsize(self.mount(path))

    def exists(self, path):
        return os.path.exists(self.mount(path))

    def rename(self, source, target):
        return os.rename(self.mount(source), self.mount(target))

    # 文件
    def write_file(self, path, data, open_pack="open", mode="wb", encrypt=False):
        abs_path = self.mount(path)
        get_lock, lock = self._acquire_lock(abs_path)
        if not get_lock:
            return abs_path

        _open = gzip.open if open_pack == "gzip" else open
        _dir = os.path.dirname(abs_path)
        if not self.exists(_dir):
            self.create_dir(_dir)

        try:
            if encrypt:
                key = config.get_config("app.file_encrypt_key")
                data = Fernet(key).encrypt(data)
            with _open(abs_path, mode) as fp_obj:
                fp_obj.write(data)
        except:
            os.remove(abs_path)
            raise
        finally:
            if lock and lock.locked():
                lock.release()
        return abs_path

    def read_file(self, path, open_pack="open", mode="rb", decrypt=False, auto_detect=False):
        if not path or not os.path.exists(self.mount(path)):
            raise FileNotFoundError
        _open = gzip.open if open_pack == "gzip" else open
        with _open(self.mount(path), mode) as file_obj:
            data = file_obj.read()
        if decrypt or (auto_detect and data[:7] == b"gAAAAAB"):
            key = config.get_config("app.file_encrypt_key")
            data = Fernet(key).decrypt(data)
        return data

    def delete_file(self, path):
        abs_path = self.mount(path)
        if os.path.exists(abs_path):
            self._release_lock(abs_path)
            os.remove(abs_path)

    # 目录
    def create_dir(self, path):
        os.makedirs(self.mount(path), exist_ok=True)

    def list_dir(self, path):
        return os.listdir(self.mount(path))

    def _is_valid(self, name, length=30):
        return len(name) == length and all(i in self.valid_chars for i in name)

    def delete_dir(self, path):
        """Note: May be too slow when deleting a big dir."""
        abs_path = self.mount(path)
        if not os.path.exists(abs_path):
            return None

        for _path in Path(abs_path).rglob("*"):
            if _path.is_file():
                self._release_lock(_path.absolute().as_posix())
        return shutil.rmtree(abs_path)

    def _delete_file_cache(self, file_hash):
        cache_path = self.get_cache_path(file_hash)
        return shutil.rmtree(cache_path, ignore_errors=True)

    def get_path(self, file_hash, parent=""):
        return os.path.join(self.root, parent, file_hash[:2], file_hash[2:])

    def get_cache_path(self, file_hash):
        return os.path.join(self.root, self.cache_root, file_hash[:2], file_hash[2:])

    def clear_orphan_files(self, filenames_used: set, clear_cache=False):
        valid_dirs = [
            i
            for i in os.scandir(self.root)
            if i.is_dir() and i.name not in self.ignored_dirs and self._is_valid(i.name, length=2)
        ]

        for directory in valid_dirs:
            for entry in os.scandir(directory.path):
                valid_file = self._is_valid(entry.name)
                filename = f"{directory.name}{entry.name}"
                if not valid_file or filename in filenames_used:
                    continue

                logger.info(f"delete file: {entry.path}")
                self.delete_file(entry.path)
                if clear_cache:
                    logger.info(f"delete cache directory for file: {filename}")
                    self._delete_file_cache(filename)

            try:
                next(os.scandir(directory.path))
            except StopIteration:
                self.delete_dir(directory.path)

    def is_created_recently(self, file_path: str, hours: int) -> bool:
        abs_path = self.mount(file_path)
        if not os.path.exists(abs_path):
            return False

        time_interval = int(time.time()) - int(os.path.getmtime(abs_path))
        if time_interval <= hours:
            return True

        return False

    @classmethod
    async def chunk_read(
        cls,
        abspath: str | Path,
        start: int | None = None,
        end: int | None = None,
        chunk_size=64 * 1024,
    ) -> AsyncGenerator[bytes, None]:
        async with custom_async_open(abspath, "rb") as file:
            if start is not None:
                file.seek(start)
            if end is not None:
                remaining = end - (start or 0)  # type: Optional[int]
            else:
                remaining = None
            while True:
                if remaining is not None and remaining < chunk_size:
                    chunk_size = remaining
                if chunk := await file.read(chunk_size):
                    if remaining is not None:
                        remaining -= len(chunk)
                    yield chunk
                else:
                    return


localstorage = LocalStorage(get_config("web.data_dir"))
tmp_storage = LocalStorage(get_config("web.tmp_dir"))
