-- T_REPORT_TABLE
create table T_REPORT_TABLE
(
    VC_ID          NUMBER not null
        primary key,
    VC_SEQ_NO      VARCHAR2(1024),
    PROJECT_NAME   VARCHAR2(1024),
    DT_REPORT_DATE DATE,
    VC_REPORT_TYPE VARCHAR2(1024),
    VC_REPORT_NAME VARCHAR2(1024),
    L_TABLE_NO     NUMBER,
    L_TABLE_LINE   NUMBER,
    DT_INSERT_TIME DATE,
    DT_UPDATE_TIME DATE,
    TB_MERGE       VARCHAR2(1024),
    COL0           VARCHAR2(4000),
    COL1           VARCHAR2(4000),
    COL2           VARCHAR2(4000),
    COL3           VARCHAR2(4000),
    COL4           VARCHAR2(4000),
    COL5           VARCHAR2(4000),
    COL6           VARCHAR2(4000),
    COL7           VARCHAR2(4000),
    COL8           VARCHAR2(4000),
    COL9           VARCHAR2(4000),
    COL10          VARCHAR2(4000),
    COL11          VARCHAR2(4000),
    COL12          VARCHAR2(4000),
    COL13          VARCHAR2(4000),
    COL14          VARCHAR2(4000),
    COL15          VARCHAR2(4000),
    COL16          VARCHAR2(4000),
    COL17          VARCHAR2(4000),
    COL18          VARCHAR2(4000),
    COL19          VARCHAR2(4000),
    COL20          VARCHAR2(4000),
    COL21          VARCHAR2(4000),
    COL22          VARCHAR2(4000),
    COL23          VARCHAR2(4000),
    COL24          VARCHAR2(4000),
    constraint UK_COMBINE_SEARCH_CONDITION
        unique (DT_REPORT_DATE, VC_REPORT_TYPE, VC_REPORT_NAME, L_TABLE_NO, L_TABLE_LINE)
);

-- comment
comment on column T_REPORT_TABLE.vc_id is '递增序列号';
comment on column T_REPORT_TABLE.project_name is '项目名称';
comment on column T_REPORT_TABLE.vc_seq_no is '批次号';
comment on column T_REPORT_TABLE.dt_report_date is '报告日期';
comment on column T_REPORT_TABLE.vc_report_type is '报告类型';
comment on column T_REPORT_TABLE.vc_report_name is '报告名称';
comment on column T_REPORT_TABLE.l_table_no is '表格序号';
comment on column T_REPORT_TABLE.l_table_line is '表内序号';
comment on column T_REPORT_TABLE.dt_insert_time is '插入时间';
comment on column T_REPORT_TABLE.dt_update_time is '更新时间';
comment on column T_REPORT_TABLE.tb_merge is '单元格合并情况';
comment on column T_REPORT_TABLE.tb_merge is '表格列';


-- sequence
create sequence VC_ID_SEQUENCE;

-- trigger
CREATE OR REPLACE TRIGGER t_report_table_on_insert
    BEFORE INSERT
    ON t_report_table
    FOR EACH ROW
BEGIN
    SELECT VC_ID_SEQUENCE.nextval
    INTO :new.vc_id
    FROM dual;
END;

-- table structure t_report_table_ex
create table t_report_table_ex
(
    vc_id          NUMBER, --外键
    dt_insert_time date,   --插入时间
    dt_update_time date,   --更新时间
    col0           CLOB,   --表格列
    col1           CLOB,   --表格列
    col2           CLOB,   --表格列
    col3           CLOB,   --表格列
    col4           CLOB,   --表格列
    col5           CLOB,   --表格列
    col6           CLOB,   --表格列
    col7           CLOB,   --表格列
    col8           CLOB,   --表格列
    col9           CLOB,   --表格列
    col10          CLOB,   --表格列
    col11          CLOB,   --表格列
    col12          CLOB,   --表格列
    col13          CLOB,   --表格列
    col14          CLOB,   --表格列
    col15          CLOB,   --表格列
    col16          CLOB,   --表格列
    col17          CLOB,   --表格列
    col18          CLOB,   --表格列
    col19          CLOB,   --表格列
    col20          CLOB,   --表格列
    col21          CLOB,   --表格列
    col22          CLOB,   --表格列
    col23          CLOB,   --表格列
    col24          CLOB    --表格列

);

-- 2022/12/29 update
alter table T_REPORT_TABLE add FILE_ID NUMBER;
alter table T_REPORT_TABLE drop constraint UK_COMBINE_SEARCH_CONDITION;
create index IDX_COMBINE_SEARCH_CONDITION on T_REPORT_TABLE(DT_REPORT_DATE, VC_REPORT_TYPE, VC_REPORT_NAME, L_TABLE_NO, L_TABLE_LINE);
create index IDX_FILE_ID on T_REPORT_TABLE(FILE_ID);
