import re
from copy import deepcopy

P_SPACE = re.compile(r"\s+")
P_STRICT_WHITESPACE = re.compile(r"^[\s　]+$", re.S)
P_NUMBER = re.compile(r"^[\d\-,\.\%\(\)]+(?:(?#单位)[(（]?(?:[十百千万亿]*元(?:[/／]股)?|%|％)[)）]?)?$", re.S)

P_ROW_HEAD = re.compile(r"[本上当\d{4}][年期](增加|减少|计提|亏损|盈利)|注册地|业务性质")
P_COL_HEAD = re.compile(r"公司名称?")


class TableUtil:
    NUMBER_PATTERN = re.compile(r"[-\d.,，一二三四五六七八九十%万亿元]|(人民币|美元|英镑|欧元|港币|新西兰元)")
    WHITESPACE_PATTERN = re.compile(r"\s")
    DATE_PATTERNS = [
        re.compile(r"(?:\d{4}年)(?:\d+月)?(?:\d+日)?"),
        re.compile(r"\d{4}[-.]\d{1,2}[-.]\d{1,2}"),
    ]

    @classmethod
    def fill_merged_cells(cls, tbl_info):
        """
        填充被合并的单元格
        """
        new_cells = deepcopy(tbl_info["cells"])
        for merged in tbl_info["merged"]:
            cell = None
            for row, col in merged:
                cell = new_cells.get("%s_%s" % (row, col))
                if cell is not None:
                    break
            if cell is not None:
                new_cell = deepcopy(cell)
                new_cell.update({"dummy": True})
                for row, col in merged:
                    new_cells.setdefault("%s_%s" % (row, col), new_cell)
        return new_cells

    @classmethod
    def group_cells(cls, cells):
        cells_by_row = {}
        cells_by_col = {}
        for idx, cell in cells.items():
            row, col = idx.split("_")
            cells_by_col.setdefault(col, {})[row] = cell
            cells_by_row.setdefault(row, {})[col] = cell
        return cells_by_row, cells_by_col

    @classmethod
    def cell_in_memory(cls, tbl, memory, **kwargs):
        res = []
        if len(tbl["cells"]) >= 600:  # 过滤太大的table
            return res
        for idx, cell in tbl["cells"].items():
            if cell.get("dummy"):
                continue
            if idx in kwargs.get("existed", []):
                continue
            if cls.is_num(cell["text"]) and not cls.is_date(cell["text"]):
                tr_heads, td_heads = cls.get_cell_headers(tbl, idx)
                for item in memory:
                    if (
                        all(tr_head in item.get("tr_heads", []) for tr_head in tr_heads)
                        and all(td_head in item.get("td_heads", []) for td_head in td_heads)
                        and idx not in res
                    ):
                        res.append(idx)
        return res

    @classmethod
    def get_cell_headers(cls, tbl, cell_idx):
        """
        获得行头和列头
        """
        tr_heads, td_heads = [], []
        new_cells = cls.fill_merged_cells(tbl)
        cells_by_row, cells_by_col = cls.group_cells(new_cells)
        origin_row, origin_col = cell_idx.split("_")  # 3, 2

        for row in sorted(map(int, cells_by_col.get(origin_col, {}).keys())):
            if row >= int(origin_row):
                break
            cell = cells_by_col.get(origin_col, {}).get(str(row))
            if (
                cell
                and not cell.get("dummy")
                and cls.delete_whitespace(cell["text"])
                and not cls.is_num(cls.delete_whitespace(cell["text"]))
            ):
                td_heads.append(cls.delete_whitespace(cell["text"]))

        for col in sorted(map(int, cells_by_row.get(origin_row, {}).keys())):
            if col >= int(origin_col):
                break
            cell = cells_by_row.get(origin_row, {}).get(str(col))
            if (
                cell
                and not cell.get("dummy")
                and cls.delete_whitespace(cell["text"])
                and not cls.is_num(cls.delete_whitespace(cell["text"]))
            ):
                tr_heads.append(cls.delete_whitespace(cell["text"]))

        return tr_heads, td_heads

    @classmethod
    def is_num(cls, text):
        text = cls.delete_whitespace(text)
        return cls.NUMBER_PATTERN.sub("", text) == ""

    @classmethod
    def is_date(cls, text):
        text = cls.delete_whitespace(text)
        for ptn in cls.DATE_PATTERNS:
            if ptn.search(text) is not None:
                return True
        return False

    @classmethod
    def delete_whitespace(cls, text):
        return cls.WHITESPACE_PATTERN.sub("", text)
