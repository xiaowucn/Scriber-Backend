import io
import logging
import os
import tempfile
from typing import ByteString

from pdfparser.pdftools.pdf_doc import PDFDoc
from pdfparser.pdftools.pdf_ocr_page import (
    process_ocr_if_need,
)
from PIL import Image, ImageSequence
from tornado.httputil import HTTPFile

from remarkable import config
from remarkable.common.storage import localstorage
from remarkable.db import pw_db
from remarkable.models.gffund import GFFundFaxMapping
from remarkable.plugins.ext_api.common import convert_image_to_pdf
from remarkable.pw_models.model import NewFileProject, NewFileTree, NewMold
from remarkable.service.new_file_project import NewFileProjectService

logger = logging.getLogger(__name__)


class GFFundUploadFile:
    default_business_template = "广发业务申请表模板"
    capture_page_ratio = 1 / 3
    page_index = 0

    def __init__(self, fax_number: str, fax_subject: str, tree_id: int, file_id: str, post_file: HTTPFile):
        self.fax_number = fax_number
        self.fax_subject = fax_subject
        self.tree_id = tree_id
        self.file_id = file_id
        self.post_file = post_file

    @property
    def file_is_image(self):
        return self.file_suffix in (".jpg", ".jpeg", ".png", ".tif")

    @property
    def file_suffix(self):
        return os.path.splitext(self.post_file.filename)[-1].lower()

    async def get_file_project(self, uid):
        file_tree = await NewFileTree.find_by_id(self.tree_id)
        if file_tree:
            return await NewFileProject.find_by_id(file_tree.pid)

        if not (file_project := await NewFileProject.find_by_kwargs(name="default")):
            file_project = await NewFileProjectService.create(
                **{
                    "name": "default",
                    "default_molds": [],
                    "uid": uid,
                },
            )
        return file_project

    async def get_mold_id(self):
        if gffund_fax_mapping := await pw_db.first(
            GFFundFaxMapping.select().where(GFFundFaxMapping.fax == f"{self.fax_number or self.fax_subject}")
        ):
            schema_name = None if len(gffund_fax_mapping.model_name) > 1 else gffund_fax_mapping.model_name[0]
        else:
            logger.info(
                "未找到对应的模型，启用默认模型进行解析，fax_number:%s ,fax_subject:%s",
                self.fax_number,
                self.fax_subject,
            )
            schema_name = self.default_business_template
        if schema_name is None:
            file_raw = self.process_file(pick_file=True)
            schema_name = self._get_schema_name_by_file(file_raw)
        mold_obj = await NewMold.find_by_name(schema_name)
        return mold_obj.id

    def process_file(self, pick_file=False):
        if self.file_is_image:
            files = self._split_image()
        else:
            files = [(self.post_file.filename, self.post_file.body)]
        if pick_file:
            if self.file_is_image:
                return files[0][1]
            raise ValueError("普通文件不能同对应多个模板")
        return files

    def _split_image(self):
        files = []
        for i, image in enumerate(ImageSequence.Iterator(Image.open(io.BytesIO(self.post_file.body))), start=1):
            img_byte = io.BytesIO()
            image.save(img_byte, format="png")
            file_raw = img_byte.getvalue()
            files.append((f"{i}-{self.post_file.filename}", file_raw))
        return files

    def _get_schema_name_by_file(self, body: ByteString):
        text = self._get_image_parts_text(body)
        schema_name = "广发业务申请表其他模板" if "基金其他" in text else self.default_business_template
        return schema_name

    def _get_image_parts_text(self, image: ByteString):
        tmp_dir = config.get_config("web.tmp_dir")
        with tempfile.NamedTemporaryFile(dir=tmp_dir) as image_path:
            localstorage.write_file(image_path.name, image, encrypt=bool(config.get_config("app.file_encrypt_key")))
            text = ""
            with tempfile.NamedTemporaryFile(dir=tmp_dir) as pdf_path:
                if convert_image_to_pdf(image_path.name, pdf_path.name):
                    text = self._get_text_in_box_with_ocr(pdf_path.name)
                else:
                    logger.error("jpg转pdf失败")
            logger.debug("image parts text:%s", text)
        return text

    def _get_text_in_box_with_ocr(self, path):
        doc = PDFDoc(path, page_range=[self.page_index])
        page = doc.pages[self.page_index]
        process_ocr_if_need(
            page,
            self.page_index,
            doc,
            path,
            ocr_name=config.get_config("client.ocr.service", "pai"),
            detect_rotation=True,
            frames=[{"outline": self._calculate_box_size(page["size"])}],
        )
        return "".join(item["text"] for item in page["texts"])

    def _calculate_box_size(self, page_size: tuple) -> list:
        width, height = page_size
        return [0, 0, width, height * self.capture_page_ratio]
