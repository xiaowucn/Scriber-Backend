"""add file id

Revision ID: 623d1071346c
Revises: 41a04103f9f0
Create Date: 2022-12-29 16:32:32.549984

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '623d1071346c'
down_revision = '41a04103f9f0'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("alter table T_REPORT_TABLE add FILE_ID NUMBER")
    op.execute("alter table T_REPORT_TABLE drop constraint UK_COMBINE_SEARCH_CONDITION")
    op.execute(
        "create index IDX_COMBINE_SEARCH_CONDITION on T_REPORT_TABLE(DT_REPORT_DATE, VC_REPORT_TYPE, VC_REPORT_NAME, L_TABLE_NO, L_TABLE_LINE)"
    )
    op.execute("create index IDX_FILE_ID on T_REPORT_TABLE(FILE_ID)")


def downgrade():
    op.execute("alter table T_REPORT_TABLE drop column FILE_ID")
    op.execute("drop index IDX_COMBINE_SEARCH_CONDITION")
    op.execute(
        "alter table T_REPORT_TABLE add constraint UK_COMBINE_SEARCH_CONDITION unique (DT_REPORT_DATE, VC_REPORT_TYPE, VC_REPORT_NAME, L_TABLE_NO, L_TABLE_LINE)"
    )
