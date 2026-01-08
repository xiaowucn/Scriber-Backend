import os
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from operator import itemgetter
from pathlib import Path
from typing import Any

import tiktoken

from remarkable.config import get_config, project_root

os.environ["TIKTOKEN_CACHE_DIR"] = str(Path(project_root) / "data" / "tmp" / "openai")


@dataclass
class Tokenizer:
    tokenizer_map: dict[str, Any] = field(default_factory=dict)

    @cached_property
    def encoder(self):
        return tiktoken.get_encoding("cl100k_base")

    def encode(self, text: str, **encoding_kwargs) -> list[int]:
        encoder = self.encoder
        if isinstance(encoder, tiktoken.Encoding):
            return encoder.encode(text, **encoding_kwargs)
        return encoder.encode(text)

    def decode(self, tokens: list[int]) -> str:
        encoder = self.encoder
        if isinstance(encoder, tiktoken.Encoding):
            return encoder.decode(tokens)
        return encoder.decode(tokens)

    def token_length(self, text: str, **encoding_kwargs):
        return len(self.encode(text, **encoding_kwargs))

    def split_by_length(self, texts: list[str], max_token_length: int = 8192):
        token_lens = []
        for text in texts:
            token_len = self.token_length(text)
            if sum(token_lens) + token_len >= max_token_length:
                yield texts[: len(token_lens)]
                texts = texts[len(token_lens) :]
                token_lens = [token_len]
            else:
                token_lens.append(token_len)
        if texts:
            yield texts


TOKEN_ENCODER = Tokenizer()


def is_value(chars, allow_empty=True):
    if len(chars) == 0:
        return allow_empty
    chars = chars.strip()
    chars = chars.replace("\n", "")
    return sum(
        [item in " 、~/_‐-─—－-–－ー-－–-−ー—0123456789,，.%％百千万元份人民币()（）HKDJPY" for item in chars]
    ) == len(chars)


class ContentType(str, Enum):
    TABLE = "table"
    PARA = "paragraph"


class InterdocHelper:
    @classmethod
    def process(cls, interdoc):
        interdoc = cls.merge_tables_separated_by_page(interdoc)
        interdoc = cls.merge_paras_separated_by_page(interdoc)
        return interdoc

    @classmethod
    def merge_tables_separated_by_page(cls, interdoc):
        # pylint: disable=too-many-locals
        if "combo_tables" not in interdoc:
            return cls.merge_tables_separated_by_page_v1(interdoc)
        new_tables = []
        visited = set()
        table_dict = {table["index"]: table for table in interdoc.get("tables", [])}
        for item in interdoc.get("tables", []):
            if item["index"] in visited:
                continue
            combo_table_idx = item.get("combo_table_idx")
            if combo_table_idx is not None and combo_table_idx >= 0:
                combo_table = interdoc["combo_tables"][combo_table_idx]
                visited.update(combo_table["table_indices"])
                tables = [table_dict[idx] for idx in combo_table["table_indices"]]
                new_grid = combo_table["merged_grid"]
                new_merged = combo_table.get("merged", [])
                new_cells = {}
                for idx, cell_idxes in combo_table["cells"].items():
                    # len(cell_idx) is usually 2, sometimes grater than 2
                    _new_cells = [table_dict[cell_idx[0]]["cells"].get(cell_idx[1]) for cell_idx in cell_idxes]
                    _new_cells = [cell for cell in _new_cells if cell]
                    if len(_new_cells) == 1:
                        new_cells[idx] = _new_cells[0]
                    elif len(_new_cells) > 1:
                        new_cell = dict(_new_cells[0])
                        new_cell["text"] += "".join([cell["text"] for cell in _new_cells[1:]])
                        new_cells[idx] = new_cell
                item["origin_cells"] = item["cells"]
                item["origin_grid"] = item["grid"]
                item["origin_merged"] = item.get("merged", [])
                item["cells"] = new_cells
                item["grid"] = new_grid
                item["merged"] = new_merged
                rects = {}
                for table in tables:
                    rects.setdefault(table["page"], []).append(table["outline"])
                item["rects"] = rects
                item["pages"] = sorted(rects.keys())
            else:
                item["pages"] = [item["page"]]
                item["rects"] = {item["page"]: [item["outline"]]}
            new_tables.append(item)
        interdoc["tables"] = new_tables
        return interdoc

    @classmethod
    def merge_tables_separated_by_page_v1(cls, interdoc):
        # pylint: disable=too-many-locals,too-many-statements
        new_tables = []
        visited = set()
        table_dict = {table["index"]: table for table in interdoc.get("tables", [])}
        # pylint: disable=too-many-nested-blocks
        for item in interdoc.get("tables", []):
            if item["index"] in visited:
                continue
            merged_table = item.get("page_merged_table")
            if merged_table and isinstance(merged_table, dict):
                cells_idx = cls.int_dict_keys(merged_table["cells_idx"])
                visited.update(cells_idx.keys())
                tables = []
                new_cells: dict[str, Any] = {}
                # new_rows = []
                # new_columns = []
                new_merged = []
                for idx, table_cells_idx in sorted(cells_idx.items(), key=lambda x: x[0]):
                    table = table_dict[idx]
                    tables.append(table)

                    for new_key, old_key in table_cells_idx.items():
                        old_cell = table["cells"].get(old_key)
                        if old_cell is None:
                            continue
                        if new_key in new_cells:
                            new_cell = new_cells[new_key]
                            new_cell = dict(new_cell)
                            new_cell["text"] += old_cell["text"]
                            new_cells[new_key] = new_cell
                        else:
                            new_cells[new_key] = old_cell

                    r_table_rows = {}
                    r_table_cols = {}
                    for new_key, old_key in table_cells_idx.items():
                        new_row, new_col = [int(i) for i in new_key.split("_")]
                        old_row, old_col = [int(i) for i in old_key.split("_")]
                        r_table_rows[old_row] = new_row
                        r_table_cols[old_col] = new_col

                    for merged in table.get("merged", []):
                        new_merged_item = []
                        for merged_cell in merged:
                            new_row = r_table_rows.get(merged_cell[0])
                            new_col = r_table_cols.get(merged_cell[1])
                            if new_row is None or new_col is None:
                                continue
                            new_merged_item.append([new_row, new_col])
                        new_merged.append(new_merged_item)
                item["origin_cells"] = item["cells"]
                item["origin_merged"] = item.get("merged", [])
                item["cells"] = new_cells
                item["merged"] = new_merged
                rects = {}
                for table in tables:
                    rects.setdefault(table["page"], []).append(table["outline"])
                item["rects"] = rects
                item["pages"] = sorted(rects.keys())
            else:
                item["pages"] = [item["page"]]
                item["rects"] = {item["page"]: [item["outline"]]}
            new_tables.append(item)
        interdoc["tables"] = new_tables
        return interdoc

    @classmethod
    def merge_paras_separated_by_page(cls, interdoc):
        new_paras = []
        visited = set()
        para_dict = {para["index"]: para for para in interdoc.get("paragraphs", [])}
        for item in interdoc.get("paragraphs", []):
            if item["index"] in visited:
                continue
            merged_para = item.get("page_merged_paragraph")
            if merged_para and isinstance(merged_para, dict):
                idxes = merged_para["paragraph_indices"]
                visited.update(idxes)
                paras = [para_dict[idx] for idx in idxes if idx in para_dict]
                rects = {}
                for para in paras:
                    rects.setdefault(para["page"], []).append(para["outline"])
                item["rects"] = rects
                item["pages"] = sorted(rects.keys())
                item["text"] = "".join([para["text"] for para in paras])
            else:
                item["pages"] = [item["page"]]
                item["rects"] = {item["page"]: [item["outline"]]}
            new_paras.append(item)

        interdoc["paragraphs"] = new_paras
        return interdoc

    @staticmethod
    def int_dict_keys(item):
        int_keys = [key for key in item.keys() if isinstance(key, str) and key.isdigit()]
        for key in int_keys:
            item[int(key)] = item.pop(key)
        return item


class Document:
    def __init__(self, interdoc):
        self.id = interdoc["id"]
        self.doc = interdoc
        self.paragraphs = interdoc.get("paragraphs", []) + interdoc.get("captions", [])
        self.tables = interdoc.get("tables", [])

    @classmethod
    def _get_merged_cell_dict(cls, raw_table):
        merged_cell_dict = {}
        for merged in raw_table.get("merged", []):
            for cell_id in merged[1:]:
                merged_cell_dict.setdefault(tuple(merged[0]), []).append(tuple(cell_id))
        return merged_cell_dict

    @classmethod
    def _get_cell_text_dict(cls, table: dict):
        merged_cell_dict = cls._get_merged_cell_dict(table)
        cell_dict = {}
        row_idxes, col_idxes = set(), set()
        for cell_id, cell in list(table["cells"].items()):
            x, y = [int(_x) for _x in cell_id.split("_")]
            cell_text = cell["text"]
            row_idxes.add(x)
            col_idxes.add(y)
            cell_dict[(x, y)] = cell_text
            # copy text info to merged cell
            for sub_cell_id in merged_cell_dict.get((x, y), []):
                # assert sub_cell_id not in cell_dict
                if sub_cell_id in cell_dict:
                    continue
                cell_dict[sub_cell_id] = cell_text
        return cell_dict, row_idxes, col_idxes

    @classmethod
    def get_table_markdown(cls, raw_table, add_title=True, add_header_line=True, remove_num: bool = False):
        cell_texts, row_idxes, col_idxes = cls._get_cell_text_dict(raw_table)
        n_row = len(row_idxes)
        n_col = len(col_idxes)

        md_table = raw_table["title"] + "\n" if add_title else ""
        header_line = "|" + "-|" * n_col + "\n"
        for i in range(n_row):
            if add_header_line or i > 0:
                md_table += "|"
            for j in range(n_col):
                if (i, j) not in cell_texts:
                    continue
                _text = cell_texts[(i, j)].replace("\n", "")
                if remove_num and is_value(_text):
                    _text = " "
                if i == 0:
                    if add_header_line:
                        md_table += _text + "|"
                else:
                    md_table += _text + "|"
            if add_header_line or i > 0:
                md_table += "\n"
            if i == 0 and add_header_line:
                md_table += header_line
        return md_table

    @classmethod
    def format_para(cls, para: dict):
        return {
            "index": para["index"],
            "text": approx_trim_for_embedding(para["text"]),
        }

    @classmethod
    def format_table(cls, table: dict):
        return {
            "index": table["index"],
            "text": approx_trim_for_embedding(cls.get_table_markdown(table)),
        }

    @classmethod
    def format_content_node(cls, typ: str, text: str, node, text_for_chat=None):
        """None index for chapter content"""
        return {
            "type": typ,
            "text": text_for_chat or text,
            "emb_text": text if text_for_chat is not None else None,
            "index": node["index"],
        }

    def make_contents(self) -> list[dict]:
        contents = []
        for para in self.paragraphs:
            contents.append(self.format_para(para))
        for table in self.tables:
            contents.append(self.format_table(table))

        contents.sort(key=itemgetter("index"))

        return contents


def n_token(text: str) -> int:
    return TOKEN_ENCODER.token_length(text)


def approx_trim(text: str, n: int, binary_search=True, token_func=n_token):
    """希望return x=text[:z], 满足 n_token(x)=n 精确实现比较困难，做一个大约的版本 n_token(x)<min(n+100, 1.1*n)"""
    if binary_search:
        return binary_token_trim(text, n, token_func=token_func)

    num_token = token_func(text)
    if num_token == 0:
        return text
    if n < 0:
        return ""
    if num_token <= n:
        return text
    nchar = n / num_token * len(text)  # 粗略应对token和char的数量不一致
    nchar = int(nchar)
    text = text[:nchar]
    result_n = token_func(text)
    if result_n > min(n + 100.0, 1.1 * n):
        return approx_trim(text, int(max(n - 100.0, 0.9 * n)), token_func=token_func)
    return text


def binary_token_trim(text, n, token_func=n_token):
    """希望return x=text[:z], 满足 n_token(x)=n 用二分查找精确搜索x，复杂度是n*log(n)"""
    if n < 0:
        return ""

    num_token = token_func(text)
    if num_token == 0 or num_token <= n:
        return text

    lb, ub = 0, len(text) - 1  # (lb, ub]
    while lb + 1 < ub:
        mid = (lb + ub) // 2
        if token_func(text[:mid]) > n:
            ub = mid
        else:
            lb = mid

    return text[:lb]


def approx_trim_for_embedding(text: str) -> str:
    embedding_token_limit = int(get_config("ai.embedding_token_limit", 5000))
    return approx_trim(text, embedding_token_limit, token_func=TOKEN_ENCODER.token_length)
