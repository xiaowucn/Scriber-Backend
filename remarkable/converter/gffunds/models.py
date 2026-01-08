from sqlalchemy import Column, Sequence
from sqlalchemy.dialects.oracle import CLOB, DATE, NUMBER, VARCHAR2
from sqlalchemy.sql import func

from remarkable.converter.gffunds.db import BaseModel


class ReportTable(BaseModel):
    __tablename__ = "t_report_table"

    vc_id = Column(NUMBER, Sequence("VC_ID_SEQUENCE"), primary_key=True)
    file_id = Column(NUMBER)
    vc_seq_no = Column(VARCHAR2(1024))
    project_name = Column(VARCHAR2(1024))
    dt_report_date = Column(DATE)
    vc_report_type = Column(VARCHAR2(1024))
    vc_report_name = Column(VARCHAR2(1024))
    l_table_no = Column(NUMBER)
    l_table_line = Column(NUMBER)
    dt_insert_time = Column(DATE, default=func.now())
    dt_update_time = Column(DATE, default=func.now())
    tb_merge = Column(VARCHAR2(1024))
    col0 = Column(VARCHAR2(4000))
    col1 = Column(VARCHAR2(4000))
    col2 = Column(VARCHAR2(4000))
    col3 = Column(VARCHAR2(4000))
    col4 = Column(VARCHAR2(4000))
    col5 = Column(VARCHAR2(4000))
    col6 = Column(VARCHAR2(4000))
    col7 = Column(VARCHAR2(4000))
    col8 = Column(VARCHAR2(4000))
    col9 = Column(VARCHAR2(4000))
    col10 = Column(VARCHAR2(4000))
    col11 = Column(VARCHAR2(4000))
    col12 = Column(VARCHAR2(4000))
    col13 = Column(VARCHAR2(4000))
    col14 = Column(VARCHAR2(4000))
    col15 = Column(VARCHAR2(4000))
    col16 = Column(VARCHAR2(4000))
    col17 = Column(VARCHAR2(4000))
    col18 = Column(VARCHAR2(4000))
    col19 = Column(VARCHAR2(4000))
    col20 = Column(VARCHAR2(4000))
    col21 = Column(VARCHAR2(4000))
    col22 = Column(VARCHAR2(4000))
    col23 = Column(VARCHAR2(4000))
    col24 = Column(VARCHAR2(4000))


class ReportTableEx(BaseModel):
    __tablename__ = "t_report_table_ex"

    vc_id = Column(NUMBER, primary_key=True)
    dt_insert_time = Column(DATE)
    dt_update_time = Column(DATE)
    col0 = Column(CLOB)
    col1 = Column(CLOB)
    col2 = Column(CLOB)
    col3 = Column(CLOB)
    col4 = Column(CLOB)
    col5 = Column(CLOB)
    col6 = Column(CLOB)
    col7 = Column(CLOB)
    col8 = Column(CLOB)
    col9 = Column(CLOB)
    col10 = Column(CLOB)
    col11 = Column(CLOB)
    col12 = Column(CLOB)
    col13 = Column(CLOB)
    col14 = Column(CLOB)
    col15 = Column(CLOB)
    col16 = Column(CLOB)
    col17 = Column(CLOB)
    col18 = Column(CLOB)
    col19 = Column(CLOB)
    col20 = Column(CLOB)
    col21 = Column(CLOB)
    col22 = Column(CLOB)
    col23 = Column(CLOB)
    col24 = Column(CLOB)


class ReportResultOut(BaseModel):
    __tablename__ = "t_report_result_out"

    l_id = Column(NUMBER, primary_key=True)
    vc_seq_no = Column(VARCHAR2(1024))
    l_par_id = Column(VARCHAR2(1024))
    l_file_id = Column(NUMBER)
    dt_report_date = Column(DATE)
    vc_report_type = Column(VARCHAR2(1024))
    vc_report_name = Column(VARCHAR2(1024))
    vc_fund_code = Column(VARCHAR2(50))
    vc_key = Column(VARCHAR2(4000))
    vc_value = Column(VARCHAR2(4000))
    clob_value = Column(CLOB)
    l_leaf = Column(NUMBER)
    l_is_clob = Column(NUMBER)
    l_level = Column(NUMBER)
    l_block = Column(NUMBER)
    dt_insert_time = Column(DATE)
    dt_update_time = Column(DATE)
