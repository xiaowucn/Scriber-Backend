import json
from copy import deepcopy
from itertools import chain
from typing import Callable, Iterable

from remarkable.common.util import box_to_outline


def calliper_diff(left: dict, right: dict, *, param: dict = None, del_keys: tuple[str, ...] = ("item",)) -> list[dict]:
    from calliper_diff.diff_data import diff_data
    from pdfparser.pdftools.interdoc import Interdoc

    left = Interdoc.restore_page_merged_table(left)
    right = Interdoc.restore_page_merged_table(right)

    if param is None:
        param = {
            "kaiti_bold": False,  # 是否包含楷体加粗差异
            "ignore_case": True,  # 是否忽略大小写
            "ignore_punctuations": True,  # 是否忽略标点差异
            "ignore_chapt_numbers": True,  # 是否忽略章节号差异
            "char_ignore_rule": "all",
            "detailed_diff_log": False,
            "debug_data_path": None,
            "fontname": "",
            "fontstyle": "",
        }
    # 构造TABLE时用的是合并表格的cells, 会导致不同index的table中cells是一样的, deepcopy后续会报错
    dfd: tuple[list, dict] = diff_data(json.loads(json.dumps(left)), json.loads(json.dumps(right)), param)

    for item in dfd[0]:
        for key in ("left_eles", "right_eles") + del_keys:
            item.pop(key, None)
        if "main_type" in item:
            item["main_type"] = item["main_type"].value

        for key in ("left", "right"):
            item[key] = [str(w) for w in (item.get(key) or [])]

    return dfd[0]


def fake_interdocs(items: Iterable[dict], reader, *, need_table=False, key_dumps_func: Callable) -> dict[str, dict]:
    docs = {}
    for item in items:
        fake_interdoc = {
            k: deepcopy(reader.data[k])
            for k in (
                "id",
                "name",
                "path",
                "pages",
                "model_version",
                "thin",
                # "tables",
                # "combo_tables",
                "use_combo_tables",
                "embedded_syllabuses",
                # "syllabuses",
                "syllabuses_parsed_by",
            )
            if k in reader.data
        }
        diff_paras = {}
        diff_tables = {}
        for box_info in item["data"]:
            for box in box_info["boxes"]:
                out_line = box_to_outline(box["box"])
                for ele_type, ele in reader.find_elements_by_outline(box["page"], out_line):
                    if ele_type == "PARAGRAPH":
                        diff_paras.setdefault(ele["index"], ele)
                    elif ele_type == "TABLE" and need_table:
                        diff_tables.setdefault(ele["index"], ele)

        for para in diff_paras.values():
            merge_chars_count = para.get("merge_chars_count")
            if para.get("continued") and merge_chars_count:
                para["chars"] = para["page_merged_paragraph"]["chars"][:-merge_chars_count]
                para["text"] = para["page_merged_paragraph"]["text"][:-merge_chars_count]

        diff_pages = {str(item["page"]) for item in chain(diff_paras.values(), diff_tables.values())}
        fake_interdoc["pages"] = {
            page_idx: page for page_idx, page in fake_interdoc["pages"].items() if page_idx in diff_pages
        }
        fake_interdoc["paragraphs"] = deepcopy(list(diff_paras.values())) if diff_paras else []
        fake_interdoc["tables"] = deepcopy(list(diff_tables.values())) if need_table else []
        docs.setdefault(key_dumps_func(item["key"]), fake_interdoc)
    return docs
