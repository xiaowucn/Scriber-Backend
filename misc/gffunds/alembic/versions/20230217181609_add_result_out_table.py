"""add result out table

Revision ID: 804ab7e37ea6
Revises: 623d1071346c
Create Date: 2023-02-17 18:16:09.228957

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '804ab7e37ea6'
down_revision = '623d1071346c'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
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
        )
        """
    )
    op.execute("""create sequence L_ID_SEQUENCE""")
    connection = op.get_bind()
    connection.execute(
        """
        CREATE OR REPLACE TRIGGER t_report_result_out_on_insert
            BEFORE INSERT
            ON t_report_result_out
            FOR EACH ROW
        BEGIN
            SELECT l_id_sequence.nextval
            INTO :new.l_id
            FROM dual;
        END;
        """
    )


def downgrade():
    pass
