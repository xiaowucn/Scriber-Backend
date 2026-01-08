import logging
import re
from collections import Counter, OrderedDict, defaultdict
from datetime import UTC, datetime
from functools import cached_property
from itertools import groupby
from typing import Match

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt, index_in_space_string
from remarkable.predictor.common_pattern import (
    CURRENCY,
    DATE_PATTERN,
    PERCENT_PATTERN,
    R_HYPHENS,
    UNIT_PATTERN,
)
from remarkable.predictor.schema_answer import CharResult

from .reader import PdfinsightReader, PdfinsightTable, PdfinsightTableCell

table_title_patterns = PatternCollection([r"表|如下|附[件一二三四五六七八九十]"])
sub_title_patterns = PatternCollection([r"每股收益（元）$"])
table_unit_patterns = PatternCollection([rf"单位[:：]{CURRENCY}?(?P<dst>.*?[{UNIT_PATTERN}])"])
cell_data_patterns = PatternCollection(
    [
        re.compile(r"^\d+(\.\d+)?[%％]?$"),
        re.compile(r"[-—–]?\d+(,\d+)+(\.\d+)?[%％]?"),
        re.compile(r"^[-—–]$"),
        re.compile(r"不[低高]于\s?\d+(\.\d+)?[%％]?$"),
    ]
)

date_header_patterns = PatternCollection([r"^(19|20)\d{2}$"])

header_cell_unit_patterns = PatternCollection(
    [
        # NOTE: 越靠前的 pattern 优先级越高，越通用的 pattern 要放在后面，作为兜底。
        # 新增的 pattern 尽可能写严格，并且放在前面
        r"数量[（（\(](?P<dst>只|个|股|头)[\)）]",
        r"人民币(?P<dst>元)",
        rf"[（（\(]?(?P<dst>{PERCENT_PATTERN})[\)）]?",
        rf"[（\(](?P<dst>{UNIT_PATTERN})[\)）]",
    ]
)
data_cell_unit_patterns = PatternCollection(
    [rf"[（\(]?(?P<dst>{UNIT_PATTERN})[\)）]?", rf"[（（\(]?(?P<dst>{PERCENT_PATTERN})[\)）]?"]
)
percent_unit_patterns = PatternCollection([rf"[（\(]?(?P<dst>{PERCENT_PATTERN})[\)）]?"])
date_patterns = re.compile(DATE_PATTERN)
P_SERIAL_NUMBER = re.compile("序号")
P_INVALID_CELL = re.compile(rf"^[{R_HYPHENS}+]$")

invalid_feature_pattern = PatternCollection(["^半?年[度末]$"])
special_split_pattern = re.compile(r"\n/|/\n|\n年$")

logger = logging.getLogger(__name__)


class ParsedTable:
    pdfinsight_table: PdfinsightTable
    elements_above: list[dict]
    tabletype: int
    unit: "ElementResult"  # noqa
    title: "ElementResult"  # noqa
    raw_rows: list[list[PdfinsightTableCell]]
    height: int
    row_tags: list[str]
    regions: list["ParsedTableRegion"]

    def __init__(
        self,
        pdfinsight_table: PdfinsightTable,
        elements_above: list[dict] = None,
        tabletype=None,
        width_from_all_rows=False,
        special_title_patterns=None,
    ):  # raw data
        self.pdfinsight_table = pdfinsight_table
        # NOTE: ordring: bottom to top
        self.elements_above = sorted(elements_above, key=lambda e: e["index"], reverse=True) if elements_above else []
        self.tabletype = self.parse_shape(tabletype)
        self.raw_rows = self.pdfinsight_table.sorted_rows()
        self.normalize_table_headers()
        self.height = len(self.raw_rows)

        # parsed results
        self.unit = self.parse_unit()
        self.title = self.parse_title(special_title_patterns=special_title_patterns)
        self.cols_counter = self.find_cols_counter()
        self.row_tags = self.parse_row_tags()
        self.regions = self.parse_regions(self.row_tags, width_from_all_rows=width_from_all_rows)

    @property
    def rows(self) -> list[list["ParsedTableCell"]]:
        return [row for region in self.regions for row in region.rows]

    @property
    def cols(self) -> list[list["ParsedTableCell"]]:
        ret = defaultdict(list)
        for row in self.rows:
            for cell in row:
                ret[cell.colidx].append(cell)
        return list(ret.values())

    @property
    def body(self) -> list["ParsedTableCell"]:
        return [cell for row in self.rows for cell in row if not cell.is_header]

    @property
    def header(self) -> list["ParsedTableCell"]:
        return [cell for row in self.rows for cell in row if cell.is_header]

    @property
    def element(self) -> dict:
        return self.pdfinsight_table.element

    def cell(self, ridx, cidx) -> "ParsedTableCell":
        return self.rows[ridx][cidx]

    def get_row_text(self, row_idx):
        row = self.rows[row_idx]
        if not row:
            return ""
        return clean_txt("".join(cell.text for cell in row))

    def parse_title(self, special_title_patterns=None):
        def is_title(ele, table) -> bool:
            if ele["class"] != "PARAGRAPH":
                return False

            if special_title_patterns and special_title_patterns.nexts(clean_txt(ele["text"])):
                return True

            if len(ele["text"]) > 50 and not (ele["text"].endswith(":") or ele["text"].endswith("：")):
                return False

            # TODO: 依据：居中段落
            ele_left, ele_right = ele["outline"][0], ele["outline"][2]
            table_left, table_right = table["outline"][0], table["outline"][2]
            left_margin = ele_left - table_left
            right_margin = table_right - ele_right
            if left_margin > 0 and right_margin > 0 and abs(left_margin - right_margin) < 10:
                return True

            if table_title_patterns.nexts(ele["text"]):
                return True

            return False

        for ele in self.elements_above:
            if is_title(ele, self.element):
                return CharResult(ele, ele["chars"])
        return None

    def parse_unit(self):
        def find_unit(ele) -> Match:
            if ele["class"] != "PARAGRAPH":
                return None
            match = table_unit_patterns.nexts(ele["text"])
            return match

        for ele in self.elements_above:
            match = find_unit(ele)
            if not match:
                continue
            unit_slice = slice(*match.span("dst"))

            return CharResult(ele, ele["chars"][unit_slice])
        return None

    def parse_regions(self, tags, width_from_all_rows=False) -> list["ParsedTableRegion"]:
        """用 header 划分区域
        ---
        header
        header
        dataline
        dataline
        ---
        header
        ...
        ---


        ---
        subtitile
        header
        dataline
        dataline
        ---
        header
        ...
        ---

        """
        regions = []
        region = None
        meet_header = "none"  # none -> in -> out -> (start new region) none
        for ridx, tag in enumerate(self.row_tags):
            if ridx == 0 or (tag == "header" and meet_header == "out"):
                # start a new region
                region = [ridx, ridx]
                regions.append(region)
                meet_header = "in" if tag == "header" else "none"
            else:
                region[1] = ridx
                if tag == "header":
                    meet_header = "in"
                elif meet_header == "in":
                    meet_header = "out"

        # 调整 subtitle：紧挨着 header 的 subtitle 应该属于下一个 region
        for rgidx in range(1, len(regions)):
            lastregion = regions[rgidx - 1]
            region = regions[rgidx]
            for ridx in range(region[0] - 1, lastregion[0], -1):
                if tags[ridx] == "subtitle":
                    lastregion[1] -= 1
                    region[0] -= 1
                else:
                    break

        parsed_regions = []
        for num, (start, end) in enumerate(regions):
            parsed_region = ParsedTableRegion(
                self,
                start,
                end,
                num,
                row_headers_last=parsed_regions[-1].raw_header_rows if parsed_regions else None,
                width_from_all_rows=width_from_all_rows,
            )
            parsed_regions.append(parsed_region)
        return parsed_regions

    @staticmethod
    def is_subtitle(row: list[PdfinsightTableCell]):
        # TODO: 还要确认是来自同一个单元格的 dummy
        real_cells = [c for c in row if not c.get("dummy", False) and c["text"]]
        return len(real_cells) == 1

    def parse_row_tags(self) -> list[str]:
        row_tags = [None] * self.height

        def must_be_dataline(row: list[PdfinsightTableCell]):
            # # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/11182?projectId=36&treeId=59&fileId=883&schemaId=2&page=33
            data_cell, counts = 0, 0
            for cell in row:
                if not cell["text"] or cell.get("dummy"):
                    continue
                if cell_data_patterns.nexts(cell["text"].strip()):
                    data_cell += 1
                counts += 1
            if not counts:
                return False
            return data_cell / counts >= 0.5

        def filter_subtitle(subtitle_indexes):
            ret = []
            # 若存在连续的sub_title 则只取第一个
            for _, idx in groupby(enumerate(subtitle_indexes), lambda x: x[1] - x[0]):
                subtitle_group = [k for _, k in idx]
                ret.append(subtitle_group[0])
            return ret

        def row_range(row: list[PdfinsightTableCell]) -> tuple[int, int]:
            row_start = min(c["top"] for c in row)
            row_end = max(c["bottom"] for c in row)
            return row_start, row_end

        # 肯定为 dataline 的
        dataline_idx = [ridx for ridx in range(self.height) if must_be_dataline(self.raw_rows[ridx])]

        # 第一行为年份 2017 2018 类似的描述时 从dataline_idx中去除第一行
        if 0 in dataline_idx:
            first_row = self.raw_rows[0]
            cells = [cell for cell in first_row if date_header_patterns.nexts(clean_txt(cell["text"]))]
            if len(cells) / len(first_row) >= 0.5:
                dataline_idx.remove(0)

        # 推断 subtitle
        subtitle_idx = [ridx for ridx in range(self.height) if self.is_subtitle(self.raw_rows[ridx])]
        subtitle_idx = filter_subtitle(subtitle_idx)

        # 在 subtitle 划分的每个区域找 header
        header_idx = []
        for i, j in zip([0] + subtitle_idx, subtitle_idx + [self.height]):
            if i == j:
                continue
            header_idx.extend(self.find_header_idx(i, j, subtitle_idx, dataline_idx))

        # TODO: pdfinsight bug 段落识别成了表格的一行 file_id: 1211
        # if subtitle_idx and subtitle_idx[0] != 0:
        #     subtitle_idx.insert(0, 0)

        # 对每一行进行判定: header, dataline, subtitle
        for ridx in range(self.height):
            if row_tags[ridx]:
                continue
            row_tag = "dataline"
            row = self.raw_rows[ridx]
            if ridx in subtitle_idx:
                row_tag = "subtitle"
            elif ridx in header_idx:
                row_tag = "header"
            row_start, row_end = row_range(row)
            if row_start == 0 and row_end == self.height:
                # 当有一列为全部合并时, 则只改变当前行
                # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/11182?projectId=36&treeId=59&fileId=883&schemaId=2&page=33
                row_start = ridx
                row_end = ridx + 1
            for i in range(row_start, row_end):
                try:
                    row_tags[i] = row_tag
                except IndexError:
                    pass
        return row_tags

    def parse_shape(self, table_type: int | None = None) -> int:
        if table_type is not None:
            return table_type
        if self.is_table_kv():
            return TableType.KV.value
        # todo 添加判断表格为table_row table_tuple的方法
        return self.tabletype

    @cached_property
    def possible_titles(self) -> list[str]:
        titles = []
        if title := clean_txt(self.pdfinsight_table.element.get("title")):
            titles.append(title)
        if self.title and (title := clean_txt(self.title.text)) and title not in titles:
            titles.append(title)
        if (
            self.elements_above
            and (title := clean_txt(self.elements_above[0].get("text") or ""))
            and title not in titles
        ):
            titles.append(title)
        return titles

    def is_table_kv(self):
        # 表格每一行均有两列且未合并
        return all((len(row) == 2 and all((not cell.dummy for cell in row)) for row in self.rows))

    def find_cells_by_outline(self, page, outline):
        cells = []
        for row in self.rows:
            for cell in row:
                if cell.page == page and PdfinsightReader.overlap_percent(cell.outline, outline) > 0.618:
                    cells.append(cell)
        return cells

    def find_cells_by_text(self, text):
        cells = [cell for row in self.rows for cell in row if clean_txt(cell.text) == clean_txt(text)]
        return cells

    @staticmethod
    def calculate_axis_length(cells, axis="row"):
        """计算给定行/列的独立单元格数目(合并单元格视为一个独立单元格,只记一次数)"""
        if axis not in ("row", "col"):
            raise ValueError(f'axis must be "row" or "col", not "{axis}"')
        length = 0
        for cell in cells:
            if axis == "row":
                if cell["right"] - cell["left"] == 1 or cell["left"] == int(cell["index"].split("_")[1]):
                    length = length + 1
            if axis == "col":
                if cell["bottom"] - cell["top"] == 1 or cell["top"] == int(cell["index"].split("_")[0]):
                    length = length + 1
        return length

    def find_cols_counter(self):
        cols = Counter()
        for row in self.raw_rows:
            cols.update([self.calculate_axis_length(row, axis="row")])
        return cols

    def find_header_idx(self, start_index, end_index, subtitle_idx, dataline_idx):
        """寻找列头行的index
        - 统计出现最多的列数认为是 数据列数
        - 取第一行满足 数据列数 的行认为是头部
        """
        header_idx = set()
        max_header_idx = start_index
        find_max_header_idx = False
        for row_len, count in sorted(self.cols_counter.items(), key=lambda x: x[0], reverse=True):
            if count < 2:
                break
            for idx, row in enumerate(self.raw_rows[start_index:end_index], start=start_index):
                # 第一个行独立单元格数目达到最大的行即可认为是列头行
                axis_length = self.calculate_axis_length(row, axis="row")
                if (
                    idx == start_index and len([cell for cell in row if not cell.get("dummy")]) != 1
                ):  # note: 第一行是列头的可能性很大 这里计算长度时忽略其单元格是否合并
                    axis_length = len(row)
                if axis_length == row_len:
                    max_header_idx = idx
                    find_max_header_idx = True
                    break
            if find_max_header_idx:
                break
        for i in range(start_index, max_header_idx + 1):
            if i not in subtitle_idx and i not in dataline_idx:
                header_idx.add(i)
        return header_idx

    def find_subtitle_row_idx(self, max_header_idx):
        subtitle_row_idx = []
        # 从header以下的行开始遍历
        for idx, row in enumerate(self.raw_rows[max_header_idx + 1 :], start=max_header_idx + 1):
            if self.calculate_axis_length(row, axis="row") != max(self.cols_counter.keys()):
                subtitle_row_idx.append(idx)
        return subtitle_row_idx

    def normalize_table_headers(self):
        """
        主要是对年份信息做处理
            最大年-largest_year_minus_0
            第二大年-largest_year_minus_1
            第三大年-largest_year_minus_2
            ...
        """
        largest_year = self.find_largest_year()
        if largest_year:
            for row in self.raw_rows:
                for cell in row:
                    cell["normalized_text"] = self.normalize_cell_text(cell["text"], largest_year)

    def find_largest_year(self):
        years = set()
        for row in self.raw_rows:
            for cell in row:
                largest_year = self.find_largest_year_in_text(cell["text"])
                if largest_year:
                    years.add(largest_year)
                    cell["_largest_year"] = largest_year  # 标记该cell, 认为可泛化
        return max(years) if years else 0

    def find_largest_year_in_text(self, text):
        text = clean_txt(text)
        years = set()
        for match in date_patterns.finditer(text):
            text = text[: match.span()[0]] + text[match.span()[1] :]  # 去掉已经被匹配过的内容
            years.add(self.revise_year_str(match.group()))
        return max(years) if years else 0

    def normalize_cell_text(self, text, largest_year):
        ret = OrderedDict()
        if text.count("/") == 1 and not special_split_pattern.search(text):
            for sub_text in re.compile(r"/").split(clean_txt(text)):
                self.normalize_sub_text(sub_text, largest_year, ret)
        else:
            for sub_text in special_split_pattern.split(text):
                sub_text = clean_txt(sub_text)
                self.normalize_sub_text(sub_text, largest_year, ret)
        return "".join(list(ret.keys()))

    @staticmethod
    def normalize_sub_text(sub_text, largest_year, ret):
        if not sub_text or len(sub_text) == 1:
            return
        if invalid_feature_pattern.nexts(sub_text):
            return
        for match in date_patterns.finditer(sub_text):
            match_year = ParsedTable.revise_year_str(match.group())
            if match_year:
                sub_text = date_patterns.sub(f"largest_year_minus_{largest_year - match_year}", sub_text)
        ret.update({sub_text: None})

    @classmethod
    def revise_year_str(cls, text):
        cn2en_map = {
            "〇": "0",
            "零": "0",
            "一": "1",
            "二": "2",
            "三": "3",
            "四": "4",
            "五": "5",
            "六": "6",
            "七": "7",
            "八": "8",
            "九": "9",
        }
        text = "".join(cn2en_map.get(t, t) for t in text)
        match = re.search(r"\d{4}", text)
        return int(match.group()) if match and cls.is_valid_year(int(match.group())) else 0

    @classmethod
    def is_valid_year(cls, year: int):
        # 简单验证一下提取年度的有效性(1990~2030)
        return -30 <= year - datetime.now(UTC).year <= 10


class ParsedTableRegion:
    table: ParsedTable
    start: int
    end: int
    num: int
    width: int
    height: int
    raw_rows: list[list[PdfinsightTableCell]]
    raw_header_rows: list[list[PdfinsightTableCell]]
    rows: list[list["ParsedTableCell"]]
    row_header_list: list[list["ParsedTableCell"]]
    col_header_list: list[list["ParsedTableCell"]]

    def __init__(
        self,
        table: ParsedTable,
        start: int,
        end: int,
        num: int,
        row_headers_last: list[list[PdfinsightTableCell]] = None,
        width_from_all_rows=False,
    ):
        # raw data
        self.table = table
        self.start, self.end = start, end
        self.num = num
        self.raw_rows = table.raw_rows[self.start : self.end + 1]
        self.row_tags = table.row_tags[self.start : self.end + 1]
        self.height = len(self.raw_rows)
        self.width = max(len(row) for row in self.raw_rows) if width_from_all_rows else len(self.raw_rows[0])

        # parsed results
        self.rows: list[list[ParsedTableCell]] = [[] for _ in range(self.height)]
        self.row_header_list: list[list[ParsedTableCell]] = [[] for _ in range(self.height)]
        self.col_header_list: list[list[ParsedTableCell]] = [[] for _ in range(self.width)]
        self.parse(row_headers_last)
        self.fix_headers()

    def parse(self, row_headers_last):
        # TODO: TABLETYPE_COL will have no row headers (but this is not aways true)
        header_rows = [row for row, tag in zip(self.raw_rows, self.row_tags) if tag == "header"]
        col_header_from_first = False
        if self.table.tabletype != TableType.KV.value and not header_rows:
            if row_headers_last:
                # 本 region 没有 header，就取上一个 region 的 header
                header_rows = row_headers_last
            else:
                # 再没有只好取第一行
                header_rows = [self.raw_rows[0]]
                col_header_from_first = True
                # logging.warning("can't find region row headers, use the first row")
                # logging.warning('|'.join({cell['text'] for cell in self.raw_rows[0]}))

        col_header_idx = self.determine_col_header_idx(header_rows)

        subtitle = None
        for rowidx in range(self.height):
            raw_row, row_tag = self.raw_rows[rowidx], self.row_tags[rowidx]
            if row_tag == "subtitle":
                cells = sorted({c["text"] for c in raw_row})
                subtitle = "".join(cells)
            for colidx in range(self.width):
                try:
                    raw_cell = raw_row[colidx]
                except IndexError:
                    logger.debug(
                        f"merge table columns is not equal, page: {self.table.element['page']}, "
                        f"title : {self.table.element['title']}"
                    )
                    continue
                dummy = raw_cell.get("dummy", False)
                merge_to = self.table.pdfinsight_table.cell_merged_to(rowidx + self.start, colidx) if dummy else None
                is_col_header = row_tag == "header" or (col_header_from_first and rowidx == 0)
                is_row_header = colidx < col_header_idx

                # create cell
                cell = ParsedTableCell(
                    rowidx + self.start,
                    colidx,
                    raw_cell,
                    self,
                    dummy=dummy,
                    is_header=is_col_header or is_row_header,
                    is_col_header=is_col_header,
                    is_row_header=is_row_header,
                    col_header_cells=self.col_header_list[colidx],
                    row_header_cells=self.row_header_list[rowidx],
                    merge_to=merge_to,
                )
                cell.subtitle = subtitle
                cell.col_header_cells = self.col_header_list[colidx]
                cell.row_header_cells = self.row_header_list[rowidx]
                if is_col_header:
                    if not (cell.dummy and cell.text in [c.text for c in self.col_header_list[colidx]]):
                        self.col_header_list[colidx].append(cell)
                if is_row_header:
                    if not (cell.dummy and cell.text in [c.text for c in self.row_header_list[rowidx]]):
                        self.row_header_list[rowidx].append(cell)
                self.rows[rowidx].append(cell)
                cell.parse_unit()

        self.raw_header_rows = header_rows

    def determine_col_header_idx(self, header_rows):
        if self.table.tabletype == TableType.ROW.value:
            col_header_idx = 0
        else:
            col_header_idx = max(row[0]["right"] - row[0]["left"] for row in header_rows) if header_rows else 1

        # 第一列为 '序号' 时  col_header_idx + 1
        if header_rows and header_rows[0] and P_SERIAL_NUMBER.search(clean_txt(header_rows[0][0]["text"])):
            col_header_idx += 1
        else:
            first_col_texts = {
                P_INVALID_CELL.sub("", rows[0]["text"])
                for rows in self.raw_rows
                if rows and (rows[0].get("dummy", False) is False)
            }
            if "".join(first_col_texts) == "":
                # 第一列全为空或者仅有中划线
                col_header_idx += 1
        return col_header_idx

    def fix_headers(self):
        """针对一些情况对 header 解析特殊处理

        case 1: | AAA | 占比 | BBB | 占比 |
        处理：如有重复的 col header，把前一格 col header 也带上
        """
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/6619#note_688681
        if len(self.col_header_list) % 2 != 0:
            # 当为奇数列时，不做处理
            return
        col_headers = ["_".join([c.text for c in headers]) for headers in self.col_header_list]
        col_header_slots = defaultdict(list)
        for col_idx, val in enumerate(col_headers):
            col_header_slots[val].append(col_idx)
        for key, slot in col_header_slots.items():
            if key == "":
                continue
            if len(slot) <= 1:
                continue
            for col_idx in slot:
                if col_idx == 0:
                    continue
                # 修正 col_header_list
                self.col_header_list[col_idx] = self.col_header_list[col_idx - 1] + self.col_header_list[col_idx]
                # 更新 cell.col_header_cells
                for row in self.rows:
                    if len(row) <= col_idx:
                        continue
                    row[col_idx].col_header_cells = self.col_header_list[col_idx]


class ParsedTableCell:
    rowidx: int
    colidx: int
    raw_cell: PdfinsightTableCell
    text: str
    width: int
    height: int
    col_header_cells: list["ParsedTableCell"]
    row_header_cells: list["ParsedTableCell"]
    unit: "ElementResult"  # noqa
    dummy: bool
    is_header: bool
    is_row_header: bool
    is_col_header: bool
    subtitle: str
    region: ParsedTableRegion
    merge_to: tuple[int, int]

    def __init__(
        self,
        rowidx,
        colidx,
        cell,
        region,
        dummy=False,
        is_header=False,
        is_col_header=False,
        is_row_header=False,
        col_header_cells=None,
        row_header_cells=None,
        merge_to=None,
    ):
        self.rowidx = rowidx
        self.colidx = colidx
        self.raw_cell = cell
        self.text = cell["text"]
        self.normalized_text = cell.get("normalized_text") or cell["text"]
        self.width = cell["right"] - cell["left"]
        self.height = cell["bottom"] - cell["top"]
        self.dummy = dummy
        self.is_header = is_header
        self.is_col_header = is_col_header
        self.is_row_header = is_row_header
        self.region = region
        self.col_header_cells = col_header_cells or []
        self.row_header_cells = row_header_cells or []
        self.merge_to = merge_to

        self.parse_unit()

    def __repr__(self):
        return self.text

    @property
    def headers(self) -> list["ParsedTableCell"]:
        return self.row_header_cells + self.col_header_cells

    @property
    def outline(self) -> tuple[float, float, float, float]:
        return self.raw_cell["box"]

    @property
    def page(self) -> int:
        return self.raw_cell["page"]

    @property
    def indexstr(self) -> str:
        return self.raw_cell["index"]

    @property
    def table(self) -> ParsedTable:
        return self.region.table

    @property
    def original(self) -> PdfinsightTableCell:
        if not self.dummy:
            return self
        if self.merge_to:
            return self.table.cell(*self.merge_to)
        return None

    def parse_unit(self):
        def get_unit_slice(match_res, text) -> slice | None:
            match_text = match_res.group()
            dst_value = match_res.group("dst")
            if dst_value is None:
                return None
            offset = match_text.index(dst_value)
            _start = match_res.span()[0] + offset
            _end = _start + len(dst_value)
            _start, _end = index_in_space_string(text, (_start, _end))
            return slice(*(_start, _end))

        def get_unit_from_subtitle() -> CharResult | None:
            if self.rowidx == 0:
                return None
            for row_index in range(self.rowidx - 1, 0, -1):
                if self.table.row_tags[row_index] == "subtitle":
                    row_above = self.table.raw_rows[row_index]
                    cell = row_above[0]
                    if not sub_title_patterns.search(cell["text"]):  # 出于谨慎考虑,须满足此白名单
                        break
                    matches = list(data_cell_unit_patterns.finditer(cell["text"]))
                    if matches and (u_slice := get_unit_slice(matches[-1], cell["text"])):
                        return CharResult(self.table.element, cell["chars"][u_slice])
            return None

        unit = None
        for match in (header_cell_unit_patterns if self.is_header else data_cell_unit_patterns).finditer(
            clean_txt(self.text)
        ):
            if unit_slice := get_unit_slice(match, self.text):
                unit = CharResult(self.table.element, self.raw_cell["chars"][unit_slice])
                break
        if not self.is_header:
            if not unit:
                #  如果上方有小标题,从小标题找
                unit = get_unit_from_subtitle()

            if not unit:
                for inherited_unit in [cell.unit for cell in self.col_header_cells + self.row_header_cells] + [
                    self.region.table.unit
                ]:
                    if inherited_unit:
                        unit = inherited_unit
                        break
        self.unit = unit

    def __str__(self):
        return self.text


def parse_table(
    element: PdfinsightTable | dict,
    tabletype=None,
    elements_above=None,
    pdfinsight_reader=None,
    width_from_all_rows=False,  # ParsedTableRegion.width 是否取自表格宽度最长的一行的宽度 默认false, 即取第一行的宽度
    special_title_patterns=None,
) -> ParsedTable:
    if isinstance(element, dict):
        element = PdfinsightTable(element)
    if pdfinsight_reader:
        if elements_above is None:
            elements_above = pdfinsight_reader.find_elements_near_by(element.index, amount=5, step=-1)
    return ParsedTable(
        element,
        tabletype=tabletype,
        elements_above=elements_above,
        width_from_all_rows=width_from_all_rows,
        special_title_patterns=special_title_patterns,
    )
