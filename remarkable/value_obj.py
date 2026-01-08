import logging
import os
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

from remarkable.common.storage import localstorage
from remarkable.common.util import md5sum

logger = logging.getLogger(__name__)


@dataclass
class FileMetaInfo:
    as_docx: bool = False
    is_ocr_expired: bool = False
    ocr_expired_msg: str = ""
    ocr_expired_pages: list = field(default_factory=list)


@dataclass
class CGSCleanFile:
    blank_pages: list[int] = field(default_factory=list)
    comment_pages: list[int] = field(default_factory=list)
    revisions: list[str] = field(default_factory=list)
    docx: str = ""
    pdf: str = ""

    @property
    def docx_path(self):
        return self._hash2path(self.docx)

    @property
    def pdf_path(self):
        return self._hash2path(self.pdf)

    @staticmethod
    def _path2hash(path) -> str:
        """
        "clean_path": "/opt/scriber/data/clean_file/629" -> "checksum"
        """
        path = Path(path)
        if path.is_absolute():
            if not path.exists():
                logger.error(f"file not found: {path=}")
                return ""
            checksum = md5sum(path)
            dst = Path(localstorage.mount(os.path.join(checksum[:2], checksum[2:])))
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(path.as_posix(), dst.as_posix())
        else:
            checksum = path.name
        return checksum

    @staticmethod
    def _hash2path(hash_) -> Path:
        if not hash_:
            logger.warning("file hash is empty")
        path = Path(localstorage.mount(os.path.join(hash_[:2], hash_[2:])))
        if not path.exists():
            logger.warning(f"file not found: {path=}")
        return path

    def path2hash(self):
        self.docx = self._path2hash(self.docx)
        self.pdf = self._path2hash(self.pdf)

    def delete(self):
        for path in (self.docx_path, self.pdf_path):
            if path.exists() and path.is_file():
                path.unlink()
                logger.info(f"delete file: {path=}")


@dataclass
class CGSFileMeta(FileMetaInfo):
    clean_file: CGSCleanFile = field(default_factory=CGSCleanFile)
    clean_path: dict[str, str] | None = None

    def __post_init__(self):
        self.as_docx = True
        if isinstance(self.clean_file, dict):
            self.clean_file = CGSCleanFile(**self.clean_file)
        if self.clean_path:
            self.clean_file.docx = self.clean_file.docx or self.clean_path.get("clean_docx_path")
            self.clean_file.pdf = self.clean_file.pdf or self.clean_path.get("clean_pdf_path")
            self.clean_file.path2hash()
        if not self.clean_file.docx:
            logger.warning("clean_file.docx is empty")
        if not self.clean_file.pdf:
            logger.warning("clean_file.pdf is empty")

    def to_dict(self):
        ret = asdict(self)
        ret.pop("clean_path")
        return ret
