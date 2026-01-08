"""
build common schema and schema convert mapping from xlsx
"""

import re
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from remarkable.config import project_root
from remarkable.plugins.zjh.util import clean_field_name


def build_fintable_schema():
    def row(data: dict):
        return {"data": data, "predictor_option": {"framework_version": "2.0"}, "mold_type": 0, "deleted_utc": 0}

    def schema(sub_schemas: list, enum_types: list):
        return {
            "schemas": sub_schemas,
            "schema_types": enum_types,
        }

    def sub_schema(name: str, columns: dict):
        return {
            "name": name,
            "orders": list(columns.keys()),
            "schema": {
                n: {
                    "type": t,
                    "required": False,
                    "multi": True,
                }
                for n, t in columns.items()
            },
        }

    finconfig = FintableColumnConfig()
    finconfig.load_excel()

    sub_schemas = []

    # root
    sub_schemas.append(sub_schema("三大报表", {n: n for n in ["资产负债表", "现金流量表", "利润表"]}))

    # 三大报表
    for table in finconfig.data:
        columns = finconfig.mapping(table, FintableColumnConfig.SYS_COMMON).keys()
        table_schema = {"报告期": "文本"}
        table_schema.update({n: "数值" for n in columns})
        sub_schemas.append(sub_schema(table, table_schema))

    # 数值类型
    sub_schemas.append(sub_schema("数值", {"数值": "数字", "单位": "文本"}))

    return row(schema(sub_schemas, []))


class FintableColumnConfig:
    xlsx_path = Path(project_root, "data/schema/fintable.xlsx")
    SYS_COMMON = 1
    SYS_KNOWLEDGE = 2
    SYS_WIND = 3
    SYS_WINDPDF = 4
    SYS_SSE = 5
    SYS_CSRC = 6
    SYS_SZSE = 7
    ESYS_COMMON = 101  # 用于变换后的对应关系
    ESYS_KNOWLEDGE = 102
    SHEETS = ["资产负债表", "现金流量表", "利润表"]

    def __init__(self) -> None:
        self.data = {}
        self._mapping = {}
        self.load_excel()
        self._zjh_cleaned_name_mapping = {}

    def load_excel(self):
        workbook = load_workbook(str(self.xlsx_path))
        for sheet_name in workbook.get_sheet_names():
            sheet = workbook.get_sheet_by_name(sheet_name)
            self.data[sheet_name] = self.load_sheet(sheet)

    def load_sheet(self, sheet: Worksheet):
        items = []
        skip_header = True
        for row in sheet.rows:
            if skip_header:
                skip_header = False
                continue
            row_data = [re.sub(r"\s+", "", c.value) if c.value else "" for c in row]
            if not row_data[self.SYS_COMMON]:
                continue
            items.append(row_data)
        return items

    def mapping(self, table: str, from_sys: int):
        mapkey = f"{table}_{from_sys}"
        need_clean = from_sys in (self.SYS_CSRC, self.ESYS_COMMON, self.ESYS_KNOWLEDGE)
        if from_sys == self.ESYS_KNOWLEDGE:
            from_sys = self.SYS_KNOWLEDGE
        if from_sys == self.ESYS_COMMON:
            from_sys = self.SYS_COMMON

        if mapkey not in self._mapping:
            self._mapping[mapkey] = {
                r[from_sys] if not need_clean else clean_field_name(r[from_sys]): r[self.SYS_COMMON]
                for r in self.data[table]
                if r[from_sys]
            }
        return self._mapping[mapkey]

    def find_common_column(self, table: str, from_sys: int, name: str) -> str:
        # 先查自己环境的 mapping
        from_sys_mapping = self.mapping(table, from_sys)
        if name in from_sys_mapping:
            return from_sys_mapping[name]

        # 再查通用 schema 或者 知识库
        if from_sys == self.SYS_CSRC:
            # 证监会特殊处理
            common_mapping = self.mapping(table, self.ESYS_COMMON)
            if name in common_mapping:
                return name

            knowledge_mapping = self.mapping(table, self.ESYS_KNOWLEDGE)
            if name in knowledge_mapping:
                return name
        else:
            common_mapping = self.mapping(table, self.SYS_COMMON)
            if name in common_mapping:
                return name

            knowledge_mapping = self.mapping(table, self.SYS_KNOWLEDGE)
            if name in knowledge_mapping:
                return name
        return None
