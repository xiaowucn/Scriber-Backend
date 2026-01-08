from collections import defaultdict
from typing import Any

from remarkable.converter.gffunds.models import ReportTable, ReportTableEx
from remarkable.pdfinsight.reader import MergedTable


class ReportTableRows:
    def __init__(self, table: MergedTable):
        self.table = table

    def get_rows(self):
        rows = defaultdict(list)
        for cell_idx, cell in self.table.cells.items():
            row_num = cell_idx.split("_")[0]
            cell.update({"cell_idx": cell_idx})
            rows[row_num].append(cell)

        for row in rows.values():
            row.sort(key=self.sort_cells)

        return dict(sorted(rows.items(), key=lambda d: int(d[0])))

    @staticmethod
    def sort_cells(cell):
        return int(cell["cell_idx"].split("_")[-1])


class ReportTableData:
    def __init__(self, rows: dict):
        self.rows = rows

    def extract_data(self, common_data: dict[str, Any], table_idx):
        rows_data = []
        extend_rows = []

        for row_idx, row in self.rows.items():
            row_dict = {**common_data, "l_table_no": table_idx, "l_table_line": row_idx}
            column = 0
            for cell in row:
                self.extract_cell_text(cell, column, row_dict)
                column += 1
            ex_dict = row_dict.copy()
            for key, value in row_dict.items():
                if key.startswith("col") and (truncate_str := self.truncate_string(value)) and value != truncate_str:
                    row_dict[key] = truncate_str
            if ex_dict != row_dict:
                extend_rows.append(
                    (
                        ReportTable(**row_dict),
                        ReportTableEx(**{key: value for key, value in ex_dict.items() if key.startswith("col")}),
                    )
                )
            else:
                rows_data.append(ReportTable(**row_dict))
        return rows_data, extend_rows

    @staticmethod
    def truncate_string(input_string, max_bytes=4000, encoding="utf-8"):
        if len(input_string.encode(encoding)) <= max_bytes:
            return input_string
        truncated_bytes = input_string.encode(encoding)[:max_bytes]
        truncated_string = truncated_bytes.decode(encoding, "ignore")
        return truncated_string

    @staticmethod
    def extract_cell_text(cell: dict, column: int, row: dict):
        dummy = cell.get("dummy", False)
        merged_cells = row.get("tb_merge")
        if dummy:
            cell["text"] = ""
            if merged_cells:
                row["tb_merge"] = f"{merged_cells},{cell['cell_idx']}"
            else:
                row["tb_merge"] = cell["cell_idx"]
        text = "".join(cell["text"].split("\n")) if cell["text"] else ""
        row.update({f"col{column}": text})


class ReportTableService:
    def __init__(self, tables: dict[str, MergedTable]):
        self.tables = tables

    def process(self, common_data):
        table_data = []
        extend_rows = []
        for table in sorted(set(self.tables.values()), key=lambda x: x.index):
            rows = ReportTableRows(table).get_rows()
            data = ReportTableData(rows)

            table_data_, extend_rows_ = data.extract_data(common_data, table.index)
            table_data.extend(table_data_)
            extend_rows.extend(extend_rows_)

        return table_data, extend_rows
