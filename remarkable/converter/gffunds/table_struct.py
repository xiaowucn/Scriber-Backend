from dataclasses import asdict, dataclass, fields
from datetime import datetime
from typing import ClassVar


@dataclass
class SQLMixin:
    @classmethod
    def attributes_to_sql(cls):
        fields_list = [field.name for field in fields(cls)]
        sql = ",".join(fields_list)
        values = ",:".join(fields_list)
        return f"({sql}) VALUES (:{values})"

    @classmethod
    def insert_sql(cls):
        sql = cls.attributes_to_sql()
        return f"INSERT INTO {cls.table_name} {sql}"

    @classmethod
    def delete_with_fid(cls, fid):
        return f"DELETE FROM {cls.table_name} WHERE file_id={fid}"

    def to_dict(self):
        return asdict(self)


@dataclass
class TReportTable(SQLMixin):
    table_name: ClassVar = "T_REPORT_TABLE"

    file_id: int
    vc_seq_no: str
    project_name: str
    dt_report_date: str
    vc_report_type: str
    vc_report_name: str
    l_table_no: int
    l_table_line: int
    dt_insert_time: datetime
    dt_update_time: datetime
    tb_merge: str | None
    col0: str | None = None
    col1: str | None = None
    col2: str | None = None
    col3: str | None = None
    col4: str | None = None
    col5: str | None = None
    col6: str | None = None
    col7: str | None = None
    col8: str | None = None
    col9: str | None = None
    col10: str | None = None
    col11: str | None = None
    col12: str | None = None
    col13: str | None = None
    col14: str | None = None
    col15: str | None = None
    col16: str | None = None
    col17: str | None = None
    col18: str | None = None
    col19: str | None = None
    col20: str | None = None
    col21: str | None = None
    col22: str | None = None
    col23: str | None = None
    col24: str | None = None

    @classmethod
    def query_sql(cls):
        query_field = ["dt_report_date", "vc_report_type", "vc_report_name", "l_table_no", "l_table_line"]
        result_field = "vc_id"
        sql = ""
        for field in query_field:
            sql += f"{field}=:{field} AND "
        limit = 1
        return f"SELECT {result_field} FROM {cls.table_name} WHERE {sql}ROWNUM={limit}"

    @classmethod
    def query_file_sql(cls, file_id):
        return f"SELECT COUNT(*) FROM {cls.table_name} WHERE file_id={file_id}"


@dataclass
class TReportTableExtend(SQLMixin):
    table_name: ClassVar = "T_REPORT_TABLE_EX"

    vc_id: int
    dt_insert_time: datetime
    dt_update_time: datetime
    col0: str | None = None
    col1: str | None = None
    col2: str | None = None
    col3: str | None = None
    col4: str | None = None
    col5: str | None = None
    col6: str | None = None
    col7: str | None = None
    col8: str | None = None
    col9: str | None = None
    col10: str | None = None
    col11: str | None = None
    col12: str | None = None
    col13: str | None = None
    col14: str | None = None
    col15: str | None = None
    col16: str | None = None
    col17: str | None = None
    col18: str | None = None
    col19: str | None = None
    col20: str | None = None
    col21: str | None = None
    col22: str | None = None
    col23: str | None = None
    col24: str | None = None


@dataclass
class TReportResultOut(SQLMixin):
    table_name: ClassVar = "T_REPORT_RESULT_OUT"

    l_file_id: int
    vc_seq_no: str
    dt_report_date: str
    vc_report_type: str
    vc_report_name: str
    vc_fund_code: str
    vc_key: str
    dt_insert_time: datetime
    dt_update_time: datetime
    vc_value: str | None = None
    l_par_id: int | None = 0
    clob_value: str | None = None
    l_leaf: int | None = 1
    l_is_clob: int = 0
    l_level: int | None = None
    l_block: int | None = None

    @classmethod
    def returning_pk_sql(cls):
        sql = cls.attributes_to_sql()
        return f"INSERT INTO {cls.table_name} {sql} RETURNING l_id INTO :pk"

    @classmethod
    def delete_with_fid(cls, fid):
        return f"DELETE FROM {cls.table_name} WHERE l_file_id={fid}"


@dataclass
class TExcelParsingResult(SQLMixin):
    table_name: ClassVar = "T_EXCEL_PARSE_RESULT_TABLE"

    file_id: int | None  # 文件id
    vc_seq_no: str | None  # 项目id
    project_name: str | None  # 项目名称
    vc_file_name: str | None  # 文件名
    vc_sheet_name: str | None  # sheet名称
    vc_report_type: str | None  # 报告类型
    l_table_line: int | None  # cell表格内行号
    dt_insert_time: datetime | None
    dt_update_time: datetime | None
    l_sheet_no: int | None = 0  # sheet 序号
    tb_merge: str | None = None  # 单元格合并信息
    is_clob: bool | None = False  # 是否为clob行，如果为clob，在入库时，会将0-50列置空，同时将数据插入新表
    col0: str | None = None
    col1: str | None = None
    col2: str | None = None
    col3: str | None = None
    col4: str | None = None
    col5: str | None = None
    col6: str | None = None
    col7: str | None = None
    col8: str | None = None
    col9: str | None = None
    col10: str | None = None
    col11: str | None = None
    col12: str | None = None
    col13: str | None = None
    col14: str | None = None
    col15: str | None = None
    col16: str | None = None
    col17: str | None = None
    col18: str | None = None
    col19: str | None = None
    col20: str | None = None
    col21: str | None = None
    col22: str | None = None
    col23: str | None = None
    col24: str | None = None
    col25: str | None = None
    col26: str | None = None
    col27: str | None = None
    col28: str | None = None
    col29: str | None = None
    col30: str | None = None
    col31: str | None = None
    col32: str | None = None
    col33: str | None = None
    col34: str | None = None
    col35: str | None = None
    col36: str | None = None
    col37: str | None = None
    col38: str | None = None
    col39: str | None = None
    col40: str | None = None
    col41: str | None = None
    col42: str | None = None
    col43: str | None = None
    col44: str | None = None
    col45: str | None = None
    col46: str | None = None
    col47: str | None = None
    col48: str | None = None
    col49: str | None = None

    @property
    def col_attributes(self):
        col_attributes = {}
        for attr_name, attr_value in self.__dict__.items():
            if attr_name.startswith("col"):
                col_attributes.update({attr_name: attr_value})
        return col_attributes

    def __post_init__(self):
        for col_value in self.col_attributes.values():
            if col_value and len(str(col_value).encode("utf-8")) >= 4000:
                self.is_clob = True
                return

    def process_table_ex_attr(self):
        ex_attr = {}
        for col_name, col_value in self.col_attributes.items():
            ex_attr.update({col_name: col_value})
            setattr(self, col_name, None)
        return ex_attr

    @classmethod
    def query_row_sql(cls, file_id, vc_seq_no, l_sheet_no, l_table_line):
        return f"SELECT vc_id FROM {cls.table_name} WHERE file_id ={file_id} AND vc_seq_no ={vc_seq_no} AND l_sheet_no ={l_sheet_no} AND l_table_line={l_table_line}"


@dataclass
class TExcelParsingResultEx(SQLMixin):
    table_name: ClassVar = "T_EXCEL_PARSE_RESULT_TABLE_EX"

    vc_id: int
    dt_insert_time: datetime | None
    dt_update_time: datetime | None
    col0: str | None = None
    col1: str | None = None
    col2: str | None = None
    col3: str | None = None
    col4: str | None = None
    col5: str | None = None
    col6: str | None = None
    col7: str | None = None
    col8: str | None = None
    col9: str | None = None
    col10: str | None = None
    col11: str | None = None
    col12: str | None = None
    col13: str | None = None
    col14: str | None = None
    col15: str | None = None
    col16: str | None = None
    col17: str | None = None
    col18: str | None = None
    col19: str | None = None
    col20: str | None = None
    col21: str | None = None
    col22: str | None = None
    col23: str | None = None
    col24: str | None = None
    col25: str | None = None
    col26: str | None = None
    col27: str | None = None
    col28: str | None = None
    col29: str | None = None
    col30: str | None = None
    col31: str | None = None
    col32: str | None = None
    col33: str | None = None
    col34: str | None = None
    col35: str | None = None
    col36: str | None = None
    col37: str | None = None
    col38: str | None = None
    col39: str | None = None
    col40: str | None = None
    col41: str | None = None
    col42: str | None = None
    col43: str | None = None
    col44: str | None = None
    col45: str | None = None
    col46: str | None = None
    col47: str | None = None
    col48: str | None = None
    col49: str | None = None
