"""add parse excel table

Revision ID: 400170f8a421
Revises: 804ab7e37ea6
Create Date: 2023-06-05 15:45:34.278642

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '400170f8a421'
down_revision = '804ab7e37ea6'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
      create table T_EXCEL_PARSE_RESULT_TABLE
        (
            VC_ID          NUMBER not null
                primary key,
            FILE_ID        NUMBER,
            VC_FILE_NAME   VARCHAR2(1024),
            VC_SHEET_NAME  VARCHAR2(1024),
            VC_SEQ_NO      VARCHAR2(1024),
            PROJECT_NAME   VARCHAR2(1024),
            VC_REPORT_TYPE VARCHAR2(1024),
            L_SHEET_NO     NUMBER,
            L_TABLE_LINE   NUMBER,
            TB_MERGE       VARCHAR2(4000),
            IS_CLOB        NUMBER(1),
            DT_INSERT_TIME DATE,
            DT_UPDATE_TIME DATE,
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
            COL25          VARCHAR2(4000),
            COL26          VARCHAR2(4000),
            COL27          VARCHAR2(4000),
            COL28          VARCHAR2(4000),
            COL29          VARCHAR2(4000),
            COL30          VARCHAR2(4000),
            COL31          VARCHAR2(4000),
            COL32          VARCHAR2(4000),
            COL33          VARCHAR2(4000),
            COL34          VARCHAR2(4000),
            COL35          VARCHAR2(4000),
            COL36          VARCHAR2(4000),
            COL37          VARCHAR2(4000),
            COL38          VARCHAR2(4000),
            COL39          VARCHAR2(4000),
            COL40          VARCHAR2(4000),
            COL41          VARCHAR2(4000),
            COL42          VARCHAR2(4000),
            COL43          VARCHAR2(4000),
            COL44          VARCHAR2(4000),
            COL45          VARCHAR2(4000),
            COL46          VARCHAR2(4000),
            COL47          VARCHAR2(4000),
            COL48          VARCHAR2(4000),
            COL49          VARCHAR2(4000),
            constraint UK_PARSE_EXCEL
                unique (VC_SEQ_NO, FILE_ID, L_SHEET_NO, L_TABLE_LINE)
        )
        """
    )
    op.execute(
        """
    create table T_EXCEL_PARSE_RESULT_TABLE_EX
    (
        VC_ID          NUMBER not null,
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
        COL24          CLOB,
        COL25          CLOB,
        COL26          CLOB,
        COL27          CLOB,
        COL28          CLOB,
        COL29          CLOB,
        COL30          CLOB,
        COL31          CLOB,
        COL32          CLOB,
        COL33          CLOB,
        COL34          CLOB,
        COL35          CLOB,
        COL36          CLOB,
        COL37          CLOB,
        COL38          CLOB,
        COL39          CLOB,
        COL40          CLOB,
        COL41          CLOB,
        COL42          CLOB,
        COL43          CLOB,
        COL44          CLOB,
        COL45          CLOB,
        COL46          CLOB,
        COL47          CLOB,
        COL48          CLOB,
        COL49          CLOB
    )
            """
    )

    op.execute("""create sequence PE_VC_ID_SEQ""")
    connection = op.get_bind()
    connection.execute(
        """
        CREATE OR REPLACE TRIGGER PE_TABLE_ON_INSERT
            BEFORE INSERT
            ON T_EXCEL_PARSE_RESULT_TABLE
            FOR EACH ROW
        BEGIN
            SELECT PE_VC_ID_SEQ.nextval
            INTO :new.VC_ID
            FROM dual;
        END;
        """
    )


def downgrade():
    pass
