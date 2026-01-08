"""create table

Revision ID: 41a04103f9f0
Revises:
Create Date: 2022-12-14 12:10:24.448282

"""
from alembic import op
from sqlalchemy.exc import DatabaseError
import logging

# revision identifiers, used by Alembic.
revision = '41a04103f9f0'
down_revision = None
branch_labels = None
depends_on = None

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def upgrade():
    try:
        op.execute(
            """
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
            )
            """
        )
    except DatabaseError:
        logger.error("T_REPORT_TABLE already exists")

    try:
        op.execute(
            """
            create table T_REPORT_TABLE_EX
            (
                VC_ID          NUMBER,
                DT_INSERT_TIME DATE,
                DT_UPDATE_TIME DATE,
                COL0           CLOB,
                COL1           CLOB,
                COL2           CLOB,
                COL3           CLOB,
                COL4           CLOB,
                COL5           CLOB,
                COL6           CLOB,
                COL7           CLOB,
                COL8           CLOB,
                COL9           CLOB,
                COL10          CLOB,
                COL11          CLOB,
                COL12          CLOB,
                COL13          CLOB,
                COL14          CLOB,
                COL15          CLOB,
                COL16          CLOB,
                COL17          CLOB,
                COL18          CLOB,
                COL19          CLOB,
                COL20          CLOB,
                COL21          CLOB,
                COL22          CLOB,
                COL23          CLOB,
                COL24          CLOB
            )
            """
        )
    except DatabaseError:
        logger.error("T_REPORT_TABLE_EX already exists")
    try:
        op.execute("""create sequence VC_ID_SEQUENCE""")
    except DatabaseError:
        logger.error("sequence VC_ID_SEQUENCE already exists")

    try:
        connection = op.get_bind()
        connection.execute(
            """
            CREATE TRIGGER t_report_table_on_insert
                 BEFORE INSERT
                 ON T_REPORT_TABLE
                 FOR EACH ROW
             BEGIN
                 SELECT VC_ID_SEQUENCE.nextval
                 INTO :new.vc_id
                 FROM dual;
             END;
            """
        )
    except DatabaseError:
        logger.error("TRIGGER t_report_table_on_insert already exists")


def downgrade():
    pass
