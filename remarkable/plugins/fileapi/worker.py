import json
import logging
import os
import re
import shutil
import tempfile
from collections import defaultdict
from copy import deepcopy

import pandas as pd
from aipod.rpc import decode_data, encode_data
from msgspec import Struct
from numpy import average
from pdfparser.pdftools.pdf_doc import PDFDoc
from pdfparser.pdftools.pdf_element import extract_interdoc_images_data
from pdfparser.pdftools.pdf_util import PDFUtil
from pdfparser.pdftools.pdfium_util import PDFiumUtil

from remarkable import config
from remarkable.common.constants import PDFParseStatus
from remarkable.common.exceptions import CustomError
from remarkable.common.storage import localstorage
from remarkable.common.util import (
    chars_in_box_by_center,
    match_ext,
    md5sum,
    ready_for_annotate_notify,
    run_singleton_task,
)
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.reader import PdfinsightReader, read_zip_first_file
from remarkable.service.new_file import html2pdf
from remarkable.service.pdf2docx import pdf2docx
from remarkable.service.word import ppt2pdf, text2pdf, word2pdf

logger = logging.getLogger(__name__)


class _Doc(Struct):
    paragraphs: list[dict] = []
    tables: list[dict] = []
    page_headers: list[dict] = []
    page_footers: list[dict] = []
    pages: dict[str, dict] = {}
    syllabuses: list[dict] = []
    shapes: list[dict] = []


class ChapterNode:
    def __init__(self, index=-1, **kwargs):
        self.index = index
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.children = []

    def to_dict(self):
        ret = {}
        for key, value in self.__dict__.items():
            ret[key] = value if key != "children" else [node.to_dict() for node in value]
        return ret


async def create_pdf_cache(file, force=False, by_pdfinsight=None):
    await file.update_(pdf_parse_status=PDFParseStatus.CACHING)
    try:
        pdf_cache = PDFCache(file, by_pdfinsight)
        pdf_cache.build(force)
    except Exception as e:
        logger.exception(f"{file.id} create cache error {e}")
        await file.update_(pdf_parse_status=PDFParseStatus.FAIL)
        raise
    else:
        await file.update_(pdf_parse_status=pdf_cache.get_pdf_parse_status())
        if (
            config.get_config("notification.ready_for_annotate_notify")
        ) and file.pdf_parse_status == PDFParseStatus.COMPLETE:
            await ready_for_annotate_notify(file.id, file.name)
    finally:
        # 更新所有相同文档PDF解析状态
        await pw_db.execute(NewFile.update(pdf_parse_status=file.pdf_parse_status).where(NewFile.hash == file.hash))


def create_docx(file):
    with tempfile.TemporaryDirectory(dir=get_config("web.tmp_dir")) as tmp_dir:
        out_path = os.path.join(tmp_dir, "output.docx")
        interdoc = json.loads(read_zip_first_file(localstorage.mount(file.pdfinsight_path())))
        extract_interdoc_images_data(localstorage.mount(file.pdf_path()), interdoc, scale=2)
        data = pdf2docx(interdoc)
        localstorage.write_file(out_path, data)

        file.docx = md5sum(out_path)
        localstorage.create_dir(os.path.dirname(file.docx_path()))
        shutil.move(out_path, localstorage.mount(file.docx_path()))
        return file.docx


class ConvertPDFError(BaseException):
    pass


class Image2PDFError(ConvertPDFError):
    pass


class Excel2PDFError(ConvertPDFError):
    pass


async def create_pdf(file):
    with tempfile.TemporaryDirectory() as tmp_dir:
        origin_path = localstorage.mount(file.path())
        tmp_path = os.path.join(tmp_dir, "tmp.pdf")

        if file.is_image:
            page_info = {"image_path": origin_path}  # 可以传入scale参数，默认为1，即不缩放
            try:
                PDFiumUtil.create_pdf_from_images([page_info], tmp_path)
            except Exception as exp:
                raise Image2PDFError(f"image to pdf failed: {file.id=}, error: {exp}") from exp
        elif file.is_excel:
            logger.info(f"convert excel to pdf: {file.id=}")
            try:
                engine = "openpyxl" if match_ext(file.path(abs_path=True), ".xlsx") else "xlrd"
                data_frame = pd.read_excel(origin_path, engine=engine)
                html_string = f"""
<html>
<head>
<meta http-equiv="Content-Type" content="text/html;charset=UTF-8"/>
<style>
table, th, td {{font-size:10pt; border:1px solid black; border-collapse:collapse; text-align:center;}}
th, td {{padding: 5px;}}
tr:nth-child(even) {{background: #E0E0E0;}}
</style>
</head>
<body>
{data_frame.to_html(index=False, na_rep="")}
</body>
</html>
                """
                content = await html2pdf(html_string)
                with open(tmp_path, "wb") as f:
                    f.write(content)
            except Exception as exp:
                logging.exception(exp)
                raise Excel2PDFError(f"excel to pdf failed: {file.id=}, error: {exp}") from exp
        elif file.is_word:
            # 仅csc客户会保留本地处理word流程，其余情况，word文档会走pdfinsight转码服务处理
            word2pdf(origin_path, tmp_path)
        elif file.is_txt:
            await text2pdf(origin_path, tmp_path)
        elif file.is_ppt:
            logger.info(f"start convert ppt to pdf: {file.id=}, {file.name=}")
            ppt2pdf(origin_path, tmp_path)
        else:
            shutil.copy2(origin_path, tmp_path)

        if not os.path.exists(tmp_path):
            raise ConvertPDFError(f"convert file failed: {file.id=}")

        file.pdf = md5sum(tmp_path)
        localstorage.create_dir(os.path.dirname(file.pdf_path()))
        shutil.move(tmp_path, localstorage.mount(file.pdf_path()))
        if file.meta_info:
            file.meta_info.update({"raw_pdf": file.pdf})
        else:
            file.meta_info = {"raw_pdf": file.pdf}


class PDFCache:
    SEARCH_MAP_SIZE_PER_FILE = 1000

    def __init__(self, file: NewFile, by_pdfinsight: bool = None):
        self.file = file
        self.by_pdfinsight = get_config("web.parse_pdf", True) if by_pdfinsight is None else by_pdfinsight

    def _cached_file_path(self, filename, absolute=True):
        path = os.path.join(self.file.pdf_cache_path(), filename)
        if absolute:
            return localstorage.mount(path)
        return path

    def _doc_page_cache_path(self, filename):
        return self._cached_file_path(filename)

    @property
    def search_string_path(self):
        return self._doc_page_cache_path("search_string")

    def search_map_path(self, key):
        return self._doc_page_cache_path("search_map_{}".format(key))

    @property
    def page_info_path(self):
        return self._doc_page_cache_path("page_info.json.zst")

    @property
    def chapter_info_path(self):
        return self._doc_page_cache_path("chapter_info.json.zst")

    @property
    def char_idx_range_path(self):
        return self._doc_page_cache_path("char_idx_range_on_page")

    def _save_search_string(self, search_string):
        path = self.search_string_path
        if localstorage.exists(path):
            os.remove(path)

        with open(path, mode="wb") as file_obj:
            file_obj.write(encode_data(search_string))

    def _save_search_map(self, search_map):
        split_map = defaultdict(dict)
        for key, value in search_map.items():
            split_map[key // self.SEARCH_MAP_SIZE_PER_FILE][key] = value
        for key, value in split_map.items():
            path = self.search_map_path(key)
            if localstorage.exists(path):
                os.remove(path)

            with open(path, "wb") as file_obj:
                file_obj.write(encode_data(value))

    def _save_char_idx_range(self, char_idx_range_on_page):
        path = self.char_idx_range_path
        if localstorage.exists(path):
            os.remove(path)
        with open(path, "wb") as file_obj:
            file_obj.write(encode_data(char_idx_range_on_page))

    def get_search_string(self):
        path = self.search_string_path
        if not localstorage.exists(path):
            return None
        with open(path, mode="rb") as file_obj:
            search_string = decode_data(file_obj.read())
        return search_string

    def get_char_in_search_map(self, idx, cache_map):
        cache_key = idx // self.SEARCH_MAP_SIZE_PER_FILE
        if cache_key in cache_map:
            cache_data = cache_map[cache_key]
        else:
            cache_data = self.get_search_map(cache_key, cache_map)
        return cache_data.get(str(idx))

    def get_search_map(self, cache_key, cache_map=None):
        path = self.search_map_path(cache_key)
        if not localstorage.exists(path):
            logging.exception(f"No search map cache found for fid: {self.file.id}")
            return {}
        with open(path, mode="rb") as file_obj:
            cache_data = decode_data(file_obj.read())

        if isinstance(cache_map, dict):
            cache_map[cache_key] = cache_data
        return cache_data

    def get_char_idx_range(self, page):
        """
        给定page所包含的char在全文档chars中的index range
        range左闭右开
        :param page:
        :return:
        """
        path = self.char_idx_range_path
        if not localstorage.exists(path):
            return None

        with open(path, mode="rb") as file_obj:
            data = decode_data(file_obj.read())

        idx_range = data.get(page, [])
        return idx_range

    def get_page_info(self):
        path = self.page_info_path
        if not localstorage.exists(path):
            return None
        with open(path, mode="rb") as file_obj:
            cache_data = decode_data(file_obj.read())
        return cache_data

    def get_chapter_info(self) -> tuple[dict[int, ChapterNode], ChapterNode]:
        path = self.chapter_info_path
        if not localstorage.exists(path):
            raise CustomError(_("The document is being parsed and catalog is not ready."))
        with open(path, mode="rb") as file_obj:
            cache_data = decode_data(file_obj.read())

        chapter_dict = {c["index"]: ChapterNode(**c) for c in cache_data}
        root = ChapterNode()
        for chapter in chapter_dict.values():
            parent = chapter_dict.get(chapter.parent, root)
            parent.children.append(chapter)
        return chapter_dict, root

    def find_closest_chapter(self, page: int, y1: float) -> ChapterNode:
        chapter_dict, root = self.get_chapter_info()
        pages = defaultdict(list)
        for chapter in chapter_dict.values():
            pages[chapter.page].append(chapter)
        if page not in pages:
            while page not in pages:
                page -= 1
                if page < 0:
                    return root
            return pages[page][-1]
        if chapters := [c for c in pages[page] if c.box[1] <= y1]:
            return chapters[-1]
        return pages[page - 1][-1]

    def _get_elements(self, pdfinsight, pdf_doc):
        if self.by_pdfinsight:
            elements = sorted(
                pdfinsight.tables
                + pdfinsight.paragraphs
                + pdfinsight.page_headers
                + pdfinsight.page_footers
                + pdfinsight.shapes,
                key=lambda x: x["index"],
            )
        else:
            elements = []
            index = 0
            for idx, page in pdf_doc.pages.items():
                for element in page["texts"]:
                    element["index"] = index
                    element["page"] = idx
                    index += 1
                    for char in element["chars"]:
                        char["page"] = idx
                    elements.append(element)
        return elements

    def _gen_search_string(self, pdfinsight: _Doc, pdf_doc: PDFDoc, separate="#_#"):
        separate_len = len(separate)
        para_separate = "\n"
        para_separate_len = len(para_separate)

        elements = self._get_elements(pdfinsight, pdf_doc)
        search_string = ""
        search_map = {}
        char_idx_range_on_page = defaultdict(list)
        index = 0
        for element in elements:
            element_page = element["page"]
            char_idx_range_on_page[element_page].append(index)
            if "cells" in element:
                for cell in sorted(element["cells"].keys(), key=lambda x: [int(i) for i in x.split("_")]):
                    for _char in element["cells"][cell]["chars"]:
                        text = _char["text"]
                        if not text:
                            continue
                        search_string += text
                        search_map[index] = {
                            "page": _char["page"],
                            "text": text,
                            "box": _char["box"],
                            "index": element["index"],
                            "index_type": "TABLE",
                        }
                        index += 1
                    search_string += separate
                    index += separate_len
            else:
                last_char = None
                for _char in element["chars"]:
                    text = _char["text"]
                    if not text:
                        continue
                    search_string += text
                    search_map[index] = {
                        "page": _char["page"],
                        "text": text,
                        "box": _char["box"],
                        "index": element["index"],
                        "index_type": "PARAGRAPH",
                    }
                    last_char = search_map[index]
                    index += 1
                if last_char:
                    search_string += para_separate
                    search_map[index] = deepcopy(last_char)
                    search_map[index]["text"] = para_separate
                    index += para_separate_len
            char_idx_range_on_page[element_page].append(index)
        char_idx_range_on_page = {k: [min(v), max(v)] for k, v in char_idx_range_on_page.items()}
        return search_string, search_map, char_idx_range_on_page

    def search(self, keyword):
        find_res = []
        search_string = self.get_search_string()
        if search_string is None:
            return find_res

        search_map_data = {}

        for item in re.finditer(re.escape("".join(keyword.split())), search_string):
            start = item.start()
            end = item.end()
            item_chars = []
            for idx in range(start, end):
                _char = self.get_char_in_search_map(idx, search_map_data)
                item_chars.append(_char)
            merged_chars = PdfinsightReader.merge_char_rects(item_chars, pos_key="box")
            search_items = []
            for page, rects in merged_chars.items():
                search_items.append({"page": page, "outlines": [[rect.x, rect.y, rect.xx, rect.yy] for rect in rects]})
            find_res.append({"items": search_items})

        return find_res

    def get_text_in_box(self, box, get_text):
        page = str(box["page"])
        char_idx_range = self.get_char_idx_range(page)
        if char_idx_range is None:
            raise CustomError(_("The document is being parsed and cannot get text from it."))
        if not char_idx_range:
            logging.info(f"no page cache for file_id:{self.file.id}, page:{page}")
            return None, None

        chars = []
        cache_key_start = char_idx_range[0] // self.SEARCH_MAP_SIZE_PER_FILE
        cache_key_end = (char_idx_range[1] - 1) // self.SEARCH_MAP_SIZE_PER_FILE
        for cache_key in range(cache_key_start, cache_key_end + 1):
            chars_in_cache_file = self.get_search_map(cache_key)
            chars.extend(
                {
                    idx: char
                    for idx, char in chars_in_cache_file.items()
                    if char_idx_range[0] <= int(idx) < char_idx_range[1]
                }.values()
            )
        chars = chars_in_box_by_center(box["box"], texts=chars, with_white_chars=True)
        chars = PDFUtil.get_sorted_chars(chars)
        # gen_search_string在每个段落后面补了一个换行符,使框选了多个段落时起到分隔作用
        # 为使多框合并标注模式下,多个框的文本之间也有换行符,不能pop掉最后一个\n
        # if chars and chars[-1]['text'] == '\n':
        #     chars.pop()

        text = get_text(chars)
        return text, chars

    def build(self, force=False):
        lock_key = "create_pdf_cache:" + self.file.hash
        get_lock, lock = run_singleton_task(lambda: None, lock_key=lock_key)
        try:
            if get_lock or force:
                self._build(force=force)
            else:
                logging.warning(f"No need to create PDF cache in a short time for fid: {self.file.id}")
        except Exception as exp:
            logging.exception(exp)
            lock.release()

    def _build(self, force):
        pdfinsight = None
        pdf_doc = None
        if self.by_pdfinsight:
            if not (self.file.pdfinsight and localstorage.exists(self.file.pdfinsight_path())):
                logging.info(f"no pdfinsight, cannot rebuild pdf_cache: {self.file.id}")
                return
            pdfinsight = read_zip_first_file(localstorage.mount(self.file.pdfinsight_path()), msgspec_type=_Doc)
        else:
            pdf_doc = PDFDoc(localstorage.mount(self.file.pdf_path()), read_page_info=True)

        if force and localstorage.exists(self.file.pdf_cache_path()):
            localstorage.delete_dir(self.file.pdf_cache_path())

        if localstorage.exists(self.file.pdf_cache_path()):
            logging.info(f"no need rebuild pdf_cache: {self.file.id}")
            return

        logging.info(f"begin creating pdf_cache for {self.file.id}")
        localstorage.create_dir(self.file.pdf_cache_path())

        self.create_page_info_cache(pdfinsight, pdf_doc)
        self.create_chapter_info_cache(pdfinsight, pdf_doc)
        self.create_pdf_search_cache(pdfinsight, pdf_doc)
        logging.info(f"pdf_cache created for {self.file.id}")

    def create_pdf_search_cache(self, pdfinsight, pdf_doc):
        search_string, search_map, char_idx_range_on_page = self._gen_search_string(pdfinsight, pdf_doc)
        self._save_search_string(search_string)
        self._save_search_map(search_map)
        self._save_char_idx_range(char_idx_range_on_page)

    def create_chapter_info_cache(self, pdfinsight, pdf_doc):
        info = []
        max_level = 6
        syllabuses = pdfinsight.syllabuses if self.by_pdfinsight else pdf_doc.outlines
        for syllabus in syllabuses:
            page, box = None, None
            start, end = None, None
            if (syllabus.get("level") or 0) > max_level:
                continue
            syll_dest = syllabus.get("dest")
            if syll_dest:
                page = syll_dest.get("page_index")
                box = syll_dest.get("box")
            parent = syllabus.get("parent")
            if _range := syllabus.get("range"):
                start, end = _range[0], _range[1]
            info.append(
                {
                    "file_id": self.file.id,
                    "index": syllabus.get("index"),
                    "parent": parent,
                    "title": syllabus.get("title"),
                    "start": start,
                    "end": end,
                    "page": page,
                    "box": box,
                    "level": syllabus.get("level"),
                }
            )

        with open(self.chapter_info_path, "wb") as file_obj:
            file_obj.write(encode_data(info))

    def create_page_info_cache(self, pdfinsight, pdf_doc):
        info = []
        pages = pdfinsight.pages if self.by_pdfinsight else pdf_doc.pages
        for idx, page in pages.items():
            info.append(
                {
                    "page": int(idx),
                    "width": page["size"][0],
                    "height": page["size"][1],
                    "rotate": PdfinsightReader.get_page_rotation(page),
                    "meta": {
                        "ocr": page["statis"].get("ocr", False),
                        "statis": page.get("statis", {}),
                    },
                }
            )

        with open(self.page_info_path, "wb") as file_obj:
            file_obj.write(encode_data(info))

    def get_pdf_parse_status(self):
        status = PDFParseStatus.FAIL
        if localstorage.exists(self.page_info_path):
            status = PDFParseStatus.PAGE_CACHED
            if localstorage.exists(self.chapter_info_path):
                status = PDFParseStatus.COMPLETE
        return status


def optimize_outline(chars):
    """根据pdfparser解析结果重新画框，使其贴合文本边缘"""
    if not chars:
        return []

    left, top, right, bottom = None, None, None, None
    char_width = []
    for char in chars:
        box = char["box"]
        char_width.append(box[3] - box[1])
        if left is None or box[0] < left:
            left = box[0]
        if top is None or box[1] < top:
            top = box[1]
        if right is None or box[2] > right:
            right = box[2]
        if bottom is None or box[3] > bottom:
            bottom = box[3]
    margin = average(char_width) / 10
    margin = round(margin, 4)

    return [left - margin, top - margin, right + 2 * margin, bottom + 2 * margin]
