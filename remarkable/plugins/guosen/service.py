import hashlib
import io
import json
import os
import shutil
import tempfile
from typing import Any, Literal
from zipfile import ZipFile

from pdfparser.pdftools.convert_scanned_pdf import ScannedPDFRestore
from pdfparser.pdftools.pdf_doc import PDFDoc
from pdfparser.pdftools.pdf_ocr_page import aio_process_ocr_if_need
from pdfparser.pdftools.pdfium_util import PDFiumUtil
from pydantic import BaseModel, ConfigDict, Field
from tornado.httputil import HTTPFile

from remarkable.common.constants import PDFParseStatus
from remarkable.common.storage import localstorage
from remarkable.common.util import md5sum
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import ADMIN
from remarkable.pw_models.model import NewFileProject, NewMold
from remarkable.service.new_file import NewFileService
from remarkable.worker.tasks import preset_answer_by_fid


class Char(BaseModel):
    box: list[float]
    font_box: list[float]
    text: str
    flag: int = 0
    style: str
    pos: list[dict[Literal["x", "y"], float]]
    page: int = 0


class Para(BaseModel):
    outline: list[float] = Field(alias="box")
    outline_score: float = 0.5
    position: list[int] = Field(default_factory=lambda: [0, 0])
    outline_parsed_by: str = "model"
    index: int
    chars: list[Char]
    text: str
    english_chars: list[int] = Field(default_factory=list)
    chinese_chars: list[int] = Field(default_factory=list)
    other_chars: list[int] = Field(default_factory=list)
    page_idx: int = 0
    page: int = 0
    continued: bool = False
    page_merge_paragraph: None = None
    syllabus: int = -1
    processed: bool = True

    def model_dump(
        self,
        *,
        mode: Literal["json", "python"] | str = "python",
        include: set[str] = None,
        exclude: set[str] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool = True,
    ) -> dict[str, Any]:
        data = super().model_dump(
            mode=mode,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
        )
        data["class"] = data["type"] = "PARAGRAPH"
        return data


class SimpleInterdoc(BaseModel):
    paragraphs: list[Para] = Field(alias="texts")
    tables: list = Field(default_factory=list)
    model_version: dict = Field(default_factory=dict)

    model_config = ConfigDict(protected_namespaces=())


async def parse_img(file: NewFile) -> PDFDoc:
    with tempfile.NamedTemporaryFile() as tmp_file:
        page_info = {"image_path": file.path(abs_path=True)}  # 可以传入scale参数，默认为1，即不缩放
        PDFiumUtil.create_pdf_from_images([page_info], tmp_file.name)
        doc = PDFDoc(tmp_file.name)
        pages = doc.pages
        for index, page in pages.items():
            await aio_process_ocr_if_need(page, index, doc, tmp_file.name, ocr_name="pai", force_ocr=True)

        file.pdf = md5sum(tmp_file.name)
        localstorage.create_dir(os.path.dirname(file.pdf_path(abs_path=True)))
        shutil.copy(tmp_file.name, file.pdf_path(abs_path=True))
        origin_path = file.pdf_path(abs_path=True)

        # include_texts 参数控制是否回填文字信息
        ScannedPDFRestore(tmp_file.name, origin_path, pages, include_texts=False).convert()

        file.pdf = md5sum(origin_path)
        localstorage.create_dir(os.path.dirname(file.pdf_path(abs_path=True)))
        shutil.move(origin_path, file.pdf_path(abs_path=True))
    await pw_db.update(file, only=["pdf"])
    return doc


class GuosenFileService(NewFileService):
    @classmethod
    async def create(cls, file: HTTPFile) -> NewFile:
        molds = await pw_db.scalars(NewMold.select(NewMold.id).where(NewMold.name == "自选股"))
        project = await pw_db.first(
            NewFileProject.select().where(NewFileProject.id == get_config("guosen.optional_stock.default_pid"))
        )

        new_file_hash = hashlib.md5(file.body).hexdigest()

        newfile = await pw_db.create(
            NewFile,
            tree_id=project.rtree_id,
            pid=project.id,
            name=file.filename,
            hash=new_file_hash,
            size=len(file.body),
            page=None,
            molds=[],
            pdf=None,
            docx=None,
            uid=ADMIN.id,
            pdfinsight=None,
            meta_info=None,
        )

        localstorage.write_file(newfile.path(), file.body, encrypt=bool(get_config("app.file_encrypt_key")))
        doc = await parse_img(newfile)
        await cls.process_file(newfile, doc)
        await cls.update_molds(newfile, molds)
        await preset_answer_by_fid(newfile.id)

        return newfile

    @classmethod
    async def process_file(cls, file: NewFile, doc: PDFDoc):
        """转换图片为pdf, 并将ocr结果转为interdoc兼容的格式, 将文本块统一当作段落处理"""
        interdoc = SimpleInterdoc.model_validate(doc.pages[0]).model_dump()
        interdoc["styles"] = doc.style.styles

        res = io.BytesIO()
        with ZipFile(res, "w") as zipped:
            zipped.writestr("origin.json", json.dumps(interdoc).encode("utf-8"))
        content = res.getvalue()
        await file.update_(pdfinsight=hashlib.md5(content).hexdigest(), pdf_parse_status=PDFParseStatus.COMPLETE)
        localstorage.write_file(file.pdfinsight_path(), content)
