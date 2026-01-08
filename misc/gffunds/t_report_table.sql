create table T_REPORT_RESULT_OUT
        (
            L_ID           NUMBER not null
                primary key,
            VC_SEQ_NO      VARCHAR2(1024),
            L_PAR_ID       VARCHAR2(1024),
            L_FILE_ID      NUMBER,
            DT_REPORT_DATE DATE,
            VC_REPORT_TYPE VARCHAR2(1024),
            VC_REPORT_NAME VARCHAR2(1024),
            VC_FUND_CODE   VARCHAR2(50),
            VC_KEY         VARCHAR2(4000),
            VC_VALUE       VARCHAR2(4000),
            CLOB_VALUE     CLOB,
            L_LEAF         NUMBER(1),
            L_IS_CLOB      NUMBER(1),
            L_LEVEL        NUMBER,
            L_BLOCK        NUMBER,
            DT_INSERT_TIME DATE,
            DT_UPDATE_TIME DATE
        );
create sequence L_ID_SEQUENCE;
CREATE OR REPLACE TRIGGER t_report_result_out_on_insert
    BEFORE INSERT
    ON t_report_result_out
    FOR EACH ROW
BEGIN
    SELECT l_id_sequence.nextval
    INTO :new.l_id
    FROM dual;
END;
