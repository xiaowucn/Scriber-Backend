import json
from copy import deepcopy

from pdfparser.pdftools.pdfium_util import PDFiumUtil


def parse_path(key):
    return [(name, int(idxstr)) for name, idxstr in [p.split(":") for p in json.loads(key)]]


def name_path(path):
    return "_".join([k for k, i in path[1:]])


def full_path(path):
    return "_".join(["%s:%s" % (k, i) for k, i in path])


def is_table_elt(elt):
    return elt.get("class") in ["TABLE"]


def extend_list(left, right):
    if not isinstance(left, list):
        left = [left]
    ret = deepcopy(left)
    if isinstance(right, list):
        ret.extend(right)
    else:
        ret.append(right)
    return ret


def convert_image_to_pdf(filepath, outpath):
    page_info = [{"image_path": filepath}]
    ret = PDFiumUtil.create_pdf_from_images(page_info, outpath)
    return ret
