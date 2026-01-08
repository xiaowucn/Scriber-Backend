from collections import defaultdict
from copy import deepcopy
from itertools import chain


class ITableUtil:
    @staticmethod
    def row_cells(cells, col_count, row_idx, col_begin=0):
        """
        Sequence of cells in the row at *row_idx* in this table.
        """
        return [cells.get("{}_{}".format(row_idx, col_idx)) for col_idx in range(col_begin, col_count)]

    @staticmethod
    def col_cells(cells, row_count, col_idx):
        """
        Sequence of cells in the column at *column_idx* in this table.
        """
        return [cells.get("{}_{}".format(row_idx, col_idx)) for row_idx in range(row_count)]

    @staticmethod
    def convert_global_cols(cols, outlines):
        return [col + outlines[0] for col in cols]

    @staticmethod
    def convert_cols_from_global(cols, outlines):
        return [col - outlines[0] for col in cols]

    @classmethod
    def init_cells_bound(cls, tbl, row_base):
        for idx, cell in list(tbl["cells"].items()):
            row, col = idx.split("_")
            row, col = int(row) + row_base, int(col)
            cell.setdefault("left", col)
            cell.setdefault("right", col + 1)
            cell.setdefault("top", row)
            cell.setdefault("bottom", row + 1)

    @classmethod
    def fix_merged_cells(cls, tbl, row_base, overwrite=False, last_table=None):
        """
        填充被合并的单元格
        """
        cells = tbl["cells"]
        for merged in tbl["merged"]:
            cell = None
            max_row = row_base + max(row for row, col in merged)
            max_col = max(col for row, col in merged)
            for row, col in merged:
                cell = cells.get("{}_{}".format(row, col))
                if cell is not None:
                    cell["right"] = max_col + 1
                    cell["bottom"] = max_row + 1
                    break
            if cell is not None:
                for row, col in merged:
                    key = "{}_{}".format(row, col)
                    if overwrite or cells.get(key) is None:
                        cells[key] = deepcopy(cell)
            if (
                last_table
                and MergeUtils.is_table_start_merged(merged, row_base)
                and MergeUtils.merged_cells_text_empty(cells, merged)
            ):
                last_table_max_row, _ = MergeUtils.get_tbl_row_col_size(last_table)
                suitable_merged = MergeUtils.merged_match(last_table["merged"], merged, last_table_max_row, tbl)
                if suitable_merged:
                    MergeUtils.modify_cell_with_matched_merged(tbl, last_table, merged, suitable_merged)
                    tbl["merged_cross_table"] = True


class MergeUtils:
    @classmethod
    def merged_cells_text_empty(cls, cells, cell_keys):
        joined_text = "".join([cells.get("{}_{}".format(*cell_key), {}).get("text", "") for cell_key in cell_keys])
        return len(joined_text) == 0

    @classmethod
    def get_merge_direction(cls, merged):
        # directions: [1, 0], [0, 1]
        merged_by_rows = defaultdict(list)
        for item in merged:
            merged_by_rows[item[0]].append(item)
        directions = set()
        if len(merged_by_rows) > 1:
            directions.add((1, 0))
        if any(len(row) > 1 for row in list(merged_by_rows.values())):
            directions.add((0, 1))
        return directions

    @classmethod
    def find_suitable_merged_match(
        cls, last_table_merged, current_merged_directions, last_table_last_row, current_merged_col
    ):
        suitable_merged_matches = []
        for merged_item in last_table_merged:
            for cell_key in merged_item:
                # 最后一行必须存在
                if last_table_last_row == cell_key[0] and current_merged_col == cell_key[1]:
                    suitable_merged_matches.append(merged_item)
                    break
        # 应该只会找到一个或者一个都没找到
        assert len(suitable_merged_matches) <= 1
        return suitable_merged_matches[0] if suitable_merged_matches else None

    @classmethod
    def get_merged_cell_text(cls, tbl, merged):
        text = "".join([tbl["cells"].get("{}_{}".format(row, col), {}).get("text", "") for row, col in merged])
        return text

    @classmethod
    def merged_match(cls, last_table_merged, current_table_merged, last_table_last_row, tbl):
        current_merged_directions = cls.get_merge_direction(current_table_merged)
        # 目前限制合并方向向下，且只有这一个合并方向
        if not (len(current_merged_directions) == 1 and (1, 0) in current_merged_directions):
            return None
        current_merged_col = current_table_merged[0][1]
        if not last_table_merged and not cls.get_merged_cell_text(tbl, current_table_merged):
            return [[last_table_last_row, current_merged_col]]
        return cls.find_suitable_merged_match(
            last_table_merged, current_merged_directions, last_table_last_row, current_merged_col
        )

    @classmethod
    def modify_cell_with_matched_merged(cls, tbl, last_tbl, current_table_merged, last_table_merged):
        last_cell_key = "{}_{}".format(*last_table_merged[0])
        last_cell = last_tbl["cells"][last_cell_key]
        for merged in current_table_merged:
            current_cell_key = "{}_{}".format(*merged)
            if current_cell_key not in tbl["cells"]:
                continue
            tbl["cells"][current_cell_key]["text"] = last_cell["text"]
            tbl["cells"][current_cell_key]["chars"] = last_cell["chars"]

        # 两个表跨页merge时，更新merge列信息
        if len({col for row, col in chain(last_table_merged, current_table_merged)}) == 1:
            current_merged_row_count = len(current_table_merged)
            last_merged_row_count = len(last_table_merged)
            for row, col in last_table_merged:
                last_tbl["cells"]["{}_{}".format(row, col)]["bottom"] += current_merged_row_count
            for row, col in current_table_merged:
                _cell = tbl["cells"].get("{}_{}".format(row, col))
                if not _cell:
                    continue
                _cell["top"] -= last_merged_row_count

    @classmethod
    def get_tbl_row_col_size(cls, tbl):
        max_row, max_col = 0, 0
        for cell_key in list(tbl["cells"].keys()):
            row, col = [int(item) for item in cell_key.split("_")]
            max_row = max(max_row, row)
            max_col = max(max_col, col)
        return max_row, max_col

    @classmethod
    def is_table_start_merged(cls, merged, row_base):
        return merged[0][0] - row_base == 0
