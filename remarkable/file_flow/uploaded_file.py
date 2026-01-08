import hashlib
from dataclasses import dataclass
from functools import cached_property


@dataclass(kw_only=True, frozen=True)
class UploadedFile:
    filename: str
    content: bytes

    @cached_property
    def md5(self) -> str:
        return hashlib.md5(self.content).hexdigest()

    @property
    def is_pdf(self):
        return self.filename.lower().endswith(".pdf")

    @property
    def is_docx(self):
        return self.filename.lower().endswith(".docx")

    @property
    def length(self):
        return len(self.content)
