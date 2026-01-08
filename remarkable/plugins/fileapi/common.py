import io
import itertools
import logging
import os
import re
import traceback
from datetime import datetime
from json.encoder import JSONEncoder
from typing import Callable

from marshmallow import validate
from pdfminer.pdfpage import PDFPage
from pdfparser.pdftools.pdf_doc import PDFDoc

from remarkable.pw_models.model import NewMold

try:
    from pdfparser.pdftools.pdf_ocr_page import aio_process_ocr_if_need
except ImportError:
    from pdfparser.pdftools.pdf_ocr_page import aio_process_single_page as aio_process_ocr_if_need
from pdfparser.pdftools.pdf_util import PDFUtil

from remarkable.common.exceptions import CustomError
from remarkable.common.storage import localstorage
from remarkable.common.util import chars_in_box_by_center
from remarkable.config import get_config


def page_num_by_pdfpage(data):
    try:
        bytes_file = io.BytesIO(data)
        return len(list(PDFPage.get_pages(bytes_file)))
    except Exception:
        error_stack = traceback.format_exc()
        logging.error(error_stack)
    return 0


def get_pdf_pages(data):
    # page = None
    # try:
    #     page = len(rxcountpages.findall(data.decode("latin1")))
    # except UnicodeDecodeError:
    #     logging.error("get pdf pages error")
    # if not page:
    page = page_num_by_pdfpage(data)
    return page


def clear_tmp_files(*paths):
    for _path in paths:
        if os.path.exists(_path):
            os.remove(_path)


class LabelEncoder(JSONEncoder):
    def default(self, o):
        res = o.text if hasattr(o, "text") else ""
        return res


def is_valid_key_path_in_molds(key_path: str, molds: list[NewMold]):
    for mold in molds:
        if is_valid_key_path(key_path, mold):
            return True, mold
    return False, None


def is_valid_key_path(key_path: str, mold: NewMold):
    for path in key_path[1:]:
        if not any(
            path in orders for orders in itertools.chain([schema["orders"] for schema in mold.data.get("schemas", [])])
        ):
            return False
    return True


def predict_element(cached_crude_answer, aid, group_by, has_accurate_answer=True):
    ret = []
    if not cached_crude_answer:
        return ret
    items = cached_crude_answer.get(aid)
    if not items:
        return ret
    items = items[:10]

    if group_by == "page":
        grouped_items = [
            (key, list(items))
            for key, items in itertools.groupby(sorted(items, key=lambda p: p["page"]), lambda p: p["page"])
        ]
        ret = sorted(
            [
                {
                    "score": sum(item["score"] for item in page_items),
                    "text": "PAGE %s" % (page + 1,),
                    "page": page,
                    "outlines": [item["outline"] for item in page_items],
                }
                for page, page_items in grouped_items
            ],
            key=lambda g: g["score"],
            reverse=True,
        )
    else:
        ret = [
            {"score": item["score"], "text": item["text"], "page": item["page"], "outlines": [item["outline"]]}
            for item in items
        ]
    crude_answer_threshold = get_config("web.crude_answer_threshold") or 0
    if not has_accurate_answer and crude_answer_threshold:
        ret = [item for item in ret if item["score"] >= crude_answer_threshold]
    return ret


def get_text_from_chars_with_white(chars, *args, **kwargs):
    lines = PDFUtil.split_chars(chars, 10000)
    line_list = []
    text = []
    for line in lines:
        for char in line:
            text.append({"text": char["text"], "box": char["box"]})
        line_list.append(text)
        text = []
    if text:
        line_list.append(text)
    return line_list


async def get_text_in_box_with_ocr(box, file, get_text_func: Callable, doc=None, page=None):
    pdf_path = localstorage.mount(file.pdf_path())
    if not doc:
        doc = PDFDoc(pdf_path, page_range=[box["page"]])
        pages = doc.pages
        page = pages[box["page"]]

    ocr_name = get_config("client.ocr.service", "pai")
    await aio_process_ocr_if_need(
        page,
        box["page"],
        doc,
        pdf_path,
        ocr_name=ocr_name,
        detect_rotation=True,
        force_ocr=True,
        frames=[{"outline": box["box"]}],
    )
    if page.get("statis", {}).get("ocr_error_msg", "") == "license expired!":
        raise CustomError("license expired!")

    chars = chars_in_box_by_center(box["box"], page, with_white_chars=True)
    text = get_text_func(chars)
    logging.debug(f"get_text_in_box_with_ocr: {text}")
    return text, chars


class DatetimeEncoder(JSONEncoder):
    def default(self, o):
        res = str(o) if isinstance(o, datetime) else ""
        return res


class NoneOfWrapper(validate.NoneOf):
    def __call__(self, value) -> str:
        try:
            if value.strip() in self.iterable:
                raise validate.ValidationError(self._format_error(value))
        except TypeError:
            pass

        return value


def validate_keyword(data):
    p_word = re.compile(r"^[\w\s\u4e00-\u9fa5,\.]+$")
    if not p_word.match(data):
        return False
    return True
