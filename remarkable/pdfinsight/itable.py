import json
from collections import defaultdict
from functools import cached_property
from itertools import zip_longest

from remarkable.pdfinsight.ihtml_util import IHtmlUtil
from remarkable.pdfinsight.itable_utils import ITableUtil
from remarkable.pdfinsight.string_util import StringUtil


class ITable:
    def __init__(self, tables):
        self.tables = tables or []  # tables should have same column count
        self._cells = None
        self.column_count = self.fix_table_column(tables)
        self._col_count = None
        self._row_count = None
        self._html = None
        self._merged = None
        self._cell_mapping = None
        self.contains_cross_table_merge = False

    def find_cell(self, row, col):
        return self.cells.get("{}_{}".format(row, col))

    def col_cells(self, col):
        return {
            int(cell_key.split("_")[0]): cell
            for cell_key, cell in list(self.cells.items())
            if int(cell_key.split("_")[1]) == col
        }

    def row_cells(self, row):
        return {
            int(cell_key.split("_")[1]): cell
            for cell_key, cell in list(self.cells.items())
            if int(cell_key.split("_")[0]) == row
        }

    @cached_property
    def rows(self):
        rows = []
        for row in range(self.row_count):
            row = [cell for _, cell in sorted(self.row_cells(row).items(), key=lambda x: x[0])]
            rows.append(row)
        return rows

    @property
    def old_index(self):
        return self.tables[0].get("index", 0)

    @property
    def html(self):
        if not self._html:
            self._html = IHtmlUtil.convert_table_to_html(self)
        return self._html

    @property
    def row_count(self):
        if self._row_count is None:
            self._row_count = max(int(idx.split("_")[0]) for idx in self.cells) + 1
        return self._row_count

    @property
    def col_count(self):
        if self._col_count is None:
            self._col_count = max(int(cell_key.split("_")[1]) for cell_key in self.cells) + 1
        return self._col_count

    @classmethod
    def is_incomplete_next_table(cls, doc, table_1, table_2):
        if not doc.is_audit_report() and not doc.is_annual_report():
            return False
        if table_2["page"] - table_1["page"] != 1:
            return False
        if table_2["outline"][0] <= table_1["outline"][0]:
            return False
        if table_2["grid"]["rows"]:
            return False
        if len(table_1["grid"]["columns"]) - len(table_2["grid"]["columns"]) != 1:
            return False
        for _, cell in list(table_2["cells"].items()):
            text = cell["text"].strip()
            if text and not StringUtil.is_num(text):
                return False
        return True

    def fix_table_column(self, tables):
        if not tables:
            return 0
        elif len(tables) == 1:
            return self.get_table_col_size(tables[0])
        # 扫描页 分支
        else:
            columns = [self.get_table_col_size(tbl) for tbl in tables]
            column_group = defaultdict(list)
            for idx, cols in enumerate(columns):
                column_group[cols].append(idx)

            keys = list(column_group.keys())
            final_col_cnt = 0
            if len(keys) == 1:
                return self.get_table_col_size(tables[0])
            elif len(keys) >= 2:
                for idx, (col1, col2) in enumerate(zip_longest(keys, keys[1:], fillvalue=None)):
                    if idx == 0:
                        final_col_cnt = self.calc_column(tables, [col1, col2], column_group)
                    elif col2:
                        final_col_cnt = self.calc_column(tables, [final_col_cnt, col2], column_group)
                    column_group[final_col_cnt].append(column_group[col1][0])
            return final_col_cnt

    def rebuild_table_info(
        self,
        all_columns,
        table_idxs,
        valid_outline,
        origin_inner_columns,
        first_col_diff,
        col_offset_limit,
        origin_inner_line,
        tables,
    ):
        for idx in table_idxs:
            table = tables[idx]
            # 修改表格外框信息
            origin_outline = table["outline"]
            table["outline"] = [valid_outline[0], origin_outline[1], valid_outline[2], origin_outline[3]]
            # 将本表格相近内线替换与all_columns中一致
            columns = []
            if origin_inner_line:
                inner_columns = origin_inner_columns
            else:
                _columns = ITableUtil.convert_global_cols(self.get_table_columns(table), valid_outline)
                inner_columns = [col - first_col_diff for col in _columns]
            for column in inner_columns:
                col = closest_column(all_columns, column)
                columns.append(col)
            fix_columns = ITableUtil.convert_cols_from_global(columns, valid_outline)
            table["grid"]["columns"] = fix_columns
            # 将合并表格列数不一样的数据扩展为列数相同，补充merged等信息
            self.extend_table_info(table, all_columns, col_offset_limit)
            # 将内线转换一致
            normalized_inner_cols = ITableUtil.convert_cols_from_global(all_columns, valid_outline)
            table["grid"]["columns"] = normalized_inner_cols

    def calc_column(self, tables, keys, column_group):
        column_0 = keys[0]
        column_1 = keys[1]
        # 获取两个表格内线（加上表格left_position）
        columns_0 = ITableUtil.convert_global_cols(
            self.get_table_columns(tables[column_group[column_0][0]]),
            tables[column_group[column_0][0]]["outline"],
        )
        columns_1 = ITableUtil.convert_global_cols(
            self.get_table_columns(tables[column_group[column_1][0]]),
            tables[column_group[column_1][0]]["outline"],
        )

        if self.get_table_row_size(tables[column_group[column_0][0]]) >= self.get_table_row_size(
            tables[column_group[column_1][0]]
        ):
            main_columns = columns_0
            minor_columns = columns_1
            valid_outline = tables[column_group[column_0][0]]["outline"]
        else:
            main_columns = columns_1
            minor_columns = columns_0
            valid_outline = tables[column_group[column_1][0]]["outline"]

        # 比较两个表格内线是否一致
        col_offset_limit = 3.0
        all_columns = self.merge_cols(main_columns, minor_columns, col_offset_limit)

        if len(all_columns) < len(main_columns) + len(minor_columns):
            # 表明按表格各自的left_position，内线有相近的情况
            origin_inner_line = True
        else:
            origin_inner_line = False

        # 如内线不一致，以内线多的为准
        if column_0 != len(all_columns) + 1 and column_1 != len(all_columns) + 1:
            if len(main_columns) > len(minor_columns):
                all_columns = main_columns
            else:
                all_columns = minor_columns

        first_col_diff = tables[0]["outline"][0] - tables[1]["outline"][0]

        if column_0 != len(all_columns) + 1:
            self.rebuild_table_info(
                all_columns,
                column_group[column_0],
                valid_outline,
                columns_0,
                first_col_diff,
                col_offset_limit,
                origin_inner_line,
                tables,
            )

        if column_1 != len(all_columns) + 1:
            self.rebuild_table_info(
                all_columns,
                column_group[column_1],
                valid_outline,
                columns_1,
                first_col_diff,
                col_offset_limit,
                origin_inner_line,
                tables,
            )
        return len(all_columns) + 1

    @classmethod
    def merge_cols(cls, main_columns, minor_columns, col_offset_limit):
        all_columns = []
        all_columns.extend(main_columns)
        for col1 in minor_columns:
            if any(abs(col1 - col_a) < col_offset_limit for col_a in sorted(all_columns)):
                continue
            all_columns.append(col1)
        return sorted(all_columns)

    @property
    def merged(self):
        if not self._merged:
            if len(self.tables) == 1:
                self._merged = self.tables[0]["merged"]
            else:
                self._merged = self.get_merged_by_cell()
        return self._merged

    def get_merged_by_cell(self):
        merged = []
        for cell_key, cell in list(self.cells.items()):
            row, col = split_key(cell_key, convert=int)
            if row != cell["top"] or col != cell["left"]:
                continue

            if cell["bottom"] - cell["top"] < 2 and cell["right"] - cell["left"] < 2:
                continue

            merged_keys = []
            for row_tem in range(row, cell["bottom"]):
                for col_tmp in range(col, cell["right"]):
                    merged_keys.append([row_tem, col_tmp])
            if validate_merged(merged_keys):
                merged.append(merged_keys)
        return merged

    @merged.setter
    def merged(self, value):
        self._merged = value

    @property
    def cell_mapping(self):
        _ = self.cells
        return self._cell_mapping

    def table_formula_relations(self):
        return self.tables[0].get("relations")

    @property
    def cells(self):
        """
        A sequence of |_Cell| objects, one for each cell of the layout grid.
        If the table contains a span, one or more |_Cell| object references
        are repeated.
        """
        if self._cells:
            return self._cells

        def update_cross_page_merged_cell_pos(last_cell, cell, first_cells, last_cells, cell_chars, update_self=False):
            text = last_cell["text"] + cell["text"]
            chars = last_cell["chars"] + cell["chars"]
            # 刷新上面表格合并的格子数据
            last_merged_cells = []
            for row_tmp in range(last_cell["top"], last_cell["bottom"]):
                cell_tem = first_cells.get("{}_{}".format(row_tmp, col))
                if cell_tem:
                    last_merged_cells.append(cell_tem)
                    cell_tem["bottom"] = max(last_cell["bottom"], cell["bottom"])
                    cell_tem["text"] = text
                    cell_tem["chars"] = chars
                    cell_tem["origin_text"] = cell_tem["text"]
                    if cell_chars:
                        cell_tem["page"] = max([cell["page"], cell_tem["page"]])
            # 刷新下面表格合并格子的数据
            idx_offset = 1
            if update_self:
                idx_offset = 0
            for row_tmp in range(row + idx_offset, row + cell["bottom"] - cell["top"]):
                cell_tem = last_cells.get("{}_{}".format(row_tmp, col))
                if cell_tem:
                    if not last_cell["docx_meta"] and cell_tem["docx_meta"]:
                        for las_cell in last_merged_cells:
                            las_cell["docx_meta"] = las_cell["docx_meta"]

                    cell_tem["top"] = last_cell["top"]
                    cell_tem["text"] = text
                    cell_tem["origin_text"] = cell_tem["text"]
                    cell_tem["chars"] = chars
                    if cell_chars:
                        cell_tem["page"] = max([cell["page"], cell_tem["page"]])

        row_idx = 0
        cells = {}
        cell_mapping = {}
        row_continued = False
        continued_cols = []
        last_table = None
        for table_id, tbl in enumerate(self.tables):
            index = tbl["index"]
            cell_mapping[index] = {}
            if row_continued:
                row_idx -= 1
            tbl_row_begin = 0
            if table_id > 0:
                continued_row = self.tables[table_id - 1].get("continued_row", 0)
                if continued_row is not None and tbl_row_begin != continued_row:
                    tbl_row_begin = continued_row
            row_idx -= tbl_row_begin
            ITableUtil.init_cells_bound(tbl, row_idx)
            ITableUtil.fix_merged_cells(tbl, row_idx, last_table=last_table)
            if tbl.pop("merged_cross_table", False):
                self.contains_cross_table_merge = True
            last_table = tbl
            first_col_span = 0  # 无合并是0，不是1
            if (
                table_id > 0
                and tbl_row_begin == 0
                and len(tbl["grid"]["rows"]) <= 3
                and len(tbl["grid"]["columns"]) + 1 != self.column_count
            ):
                first_col_span = self.get_first_col_span(cells, row_idx, tbl)
                if first_col_span > 0:
                    self._merged = [[[row_idx, col] for col in range(first_col_span + 1)]]
            for idx in sorted(tbl["cells"].keys(), key=lambda x: split_key(x)[0]):
                cell = tbl["cells"][idx]
                cell_chars = cell["chars"]
                row, col = [int(item) for item in idx.split("_")]
                col += first_col_span if col > 0 else 0
                if row < tbl_row_begin:
                    if row_continued:
                        continue
                    #  处理第一列表是行合并，并且把底下数据行合并进去了
                    if row == 0 and cell["bottom"] - cell["top"] > tbl_row_begin:
                        col_cells = ITableUtil.col_cells(cells, row_idx + tbl_row_begin, col)
                        for col_cell in col_cells[::-1]:
                            if col_cell:
                                col_cell["bottom"] += cell["bottom"] - cell["top"] - tbl_row_begin
                                break
                    continue
                if row_continued:
                    if row == tbl_row_begin:
                        last_cell = cells.get("{}_{}".format(row + row_idx, col))
                        if last_cell:
                            if not last_cell.get("docx_meta") and cell.get("docx_meta"):
                                last_cell["docx_meta"] = cell["docx_meta"]
                            update_cross_page_merged_cell_pos(last_cell, cell, cells, tbl["cells"], cell_chars)
                            cell_mapping[index][idx] = "{}_{}".format(row + row_idx, col)
                        else:
                            cell_mapping[index][idx] = None
                        continue
                elif continued_cols and col in continued_cols:
                    if row == tbl_row_begin:
                        last_cell = cells.get("{}_{}".format(row + row_idx - 1, col))
                        if last_cell:
                            if last_cell["top"] != row + row_idx - 1:
                                last_cell = cells.get("{}_{}".format(last_cell["top"], col))
                        if last_cell:
                            update_cross_page_merged_cell_pos(last_cell, cell, cells, tbl["cells"], cell_chars, True)
                            cell_mapping[index][idx] = "{}_{}".format(row + row_idx - 1, col)
                        else:
                            cell_mapping[index][idx] = None
                        # continue
                row += row_idx
                cell["origin_text"] = cell["text"]
                cells["{}_{}".format(row, col)] = cell
                cell_mapping[index][idx] = "{}_{}".format(row, col)
            row_idx += self.get_table_row_size(tbl)
            row_continued = tbl.get("row_continued")
            continued_cols = tbl.get("continued_cols")

        self._cells = cells
        self._cell_mapping = cell_mapping
        self._fill_row_col_to_cell()
        self._fill_dummy_to_cell()
        return self._cells

    def _fill_dummy_to_cell(self):
        for key, cell in self._cells.items():
            row, col = split_key(key, convert=int)
            if row != cell["top"] or col != cell["left"]:
                cell["dummy"] = True

    def _fill_row_col_to_cell(self):
        for cell_key, cell in list(self._cells.items()):
            row, col = [int(item) for item in cell_key.split("_")]
            cell["row"] = row
            cell["col"] = col

    @staticmethod
    def get_first_col_span(cells, row_idx, tbl):
        """
        修复跨页表格第二页只有一行且第一列是合并单元格的表格
        :param cells:
        :param row_idx:
        :param tbl:
        :return:
        """
        colspan = 0
        col_count = max(int(cell_key.split("_")[1]) for cell_key in tbl["cells"]) + 1
        max_col = max(int(key.split("_")[1]) for key in cells) + 1
        min_row = min(key.split("_")[0] for key in list(tbl["cells"].keys()))
        first_col_width = (
            tbl["cells"]["{}_0".format(min_row)]["box"][2] - tbl["cells"]["{}_0".format(min_row)]["box"][0]
        )
        if max_col > col_count:
            widths = {
                key: cell["box"][2] - cell["box"][0]
                for key, cell in list(cells.items())
                if int(key.split("_")[0]) == row_idx - 1
            }
            width_sum = 0
            for col in range(max_col):
                key = "{}_{}".format(row_idx - 1, col)
                width = widths.get(key, 0)
                width_sum += width
                next_col_key = "{}_{}".format(row_idx - 1, col + 1)
                next_col_right = widths.get(next_col_key, 0)
                if abs(first_col_width - width_sum) < abs(width_sum + next_col_right - first_col_width):
                    colspan = col
                    break
        return colspan

    @classmethod
    def get_table_row_size(cls, tbl):
        return max([int(idx.split("_")[0]) for idx in tbl["cells"]] or [0]) + 1

    @classmethod
    def get_table_col_size(cls, tbl):
        # return max([int(idx.split('_')[1]) for idx in tbl['cells']]) + 1
        return len(tbl["grid"]["columns"]) + 1

    @classmethod
    def extend_table_info(cls, tbl, all_columns, col_offset_limit):
        """
        将合并表格列数不一样的数据扩展为列数相同
        :param tbl:
        :param all_columns:
        :return:
        """

        def get_merged_list(mergeds, new_cell):
            for merged in mergeds:
                if new_cell in merged:
                    return merged

        columns = ITableUtil.convert_global_cols(cls.get_table_columns(tbl), tbl["outline"])
        new_columns = []
        for col in columns:
            for col_a in all_columns:
                if abs(col - col_a) < col_offset_limit:
                    new_columns.append(col_a)
        columns = new_columns

        row_count = cls.get_table_row_size(tbl)
        if len(columns) == len(all_columns):
            return
        # print tbl['index'], columns
        mergeds = json.loads(json.dumps(tbl["merged"]))
        # print 'old_merged', mergeds
        cells_new = json.loads(json.dumps(tbl["cells"]))
        # print 'old_cell', cells_new
        mergeds_new = []
        merged_list = [cell for merged in mergeds for cell in merged]

        extend_relations = {}
        col_changed_rel = {}
        pre_old_col = 0

        diff_all_count = 0
        columns.append(tbl["outline"][2])
        for old_index, old_col in enumerate(columns):
            new_cols = [
                index for index, new_col in enumerate(all_columns) if new_col > pre_old_col and new_col < old_col
            ]
            pre_old_col = old_col
            if len(new_cols) == 0:
                continue
            diff_count = len(new_cols)
            for old_oth_col in range(old_index + 1, len(all_columns) + 1)[::-1]:
                col_changed_rel[old_oth_col] = col_changed_rel.get(old_oth_col, old_oth_col) + diff_count

            for row in range(row_count):
                for old_oth_col in range(old_index + diff_all_count + 1, len(all_columns) + 1)[::-1]:
                    old_key = "{}_{}".format(row, old_oth_col)
                    if old_key not in cells_new:
                        continue
                    new_key = "{}_{}".format(row, old_oth_col + diff_count)
                    cells_new[new_key] = cells_new.pop(old_key)
                old_key = "{}_{}".format(row, old_index + diff_all_count)
                relations = []
                for new_col in range(new_cols[0], new_cols[-1] + 1 + 1):
                    relations.append([row, new_col])
                extend_relations["{}_{}".format(row, old_index)] = relations

            diff_all_count += diff_count

        extend_keys = sorted(extend_relations.keys(), key=lambda x: [x.split("_")[0], x.split("_")[1]])
        has_deal_keys = []
        for key in extend_keys:
            if key in has_deal_keys:
                continue
            key_arr = [int(key.split("_")[0]), int(key.split("_")[1])]
            new_merged = []
            if key_arr in merged_list:
                merged = get_merged_list(mergeds, key_arr)
                mergeds.remove(merged)
                for merged_cell in merged:
                    key_new = "{}_{}".format(merged_cell[0], merged_cell[1])
                    if key_new in extend_keys:
                        new_merged.extend(extend_relations[key_new])
                        has_deal_keys.append(key_new)
                    else:
                        # new_merged.append(merged_cell)
                        new_merged.append([merged_cell[0], col_changed_rel.get(merged_cell[1], merged_cell[1])])
            else:
                new_merged = extend_relations[key]
            has_deal_keys.append(key)
            mergeds_new.append(new_merged)

        for merged in mergeds[::-1]:
            new_merged = []
            for cell in merged:
                new_merged.append([cell[0], col_changed_rel.get(cell[1], cell[1])])
            mergeds.remove(merged)
            mergeds_new.append(new_merged)
        mergeds_new = sorted(mergeds_new, key=lambda x: [x[0][0], x[0][1]])
        tbl["merged"] = mergeds_new
        tbl["cells"] = cells_new

    @classmethod
    def get_table_columns(cls, tbl):
        return tbl["grid"]["columns"]


def closest_column(valid_columns, column):
    select = column - valid_columns[0]
    index = 0
    for i in range(1, len(valid_columns)):
        select2 = column - valid_columns[i]
        if abs(select) > abs(select2):
            select = select2
            index = i
    return valid_columns[index]


def split_key(key, sep="_", convert=None):
    if sep not in key:
        raise ValueError("separator %s not in %s", sep, key)
    vals = key.split(sep)
    if len(vals) != 2:
        raise ValueError("illegal format of key %s", key)
    if convert:
        return [convert(n) for n in vals]
    return vals


def validate_merged(merged):
    merged.sort()
    col_start = merged[0][1]
    tar_row = merged[0][0]
    tar_col = col_start
    for row, col in merged:
        if row == tar_row:
            if col != tar_col:
                return False
            tar_col = col + 1
        else:
            if row - tar_row != 1 or col != col_start:
                return False
            tar_row = row
            tar_col = col_start + 1
    return True
