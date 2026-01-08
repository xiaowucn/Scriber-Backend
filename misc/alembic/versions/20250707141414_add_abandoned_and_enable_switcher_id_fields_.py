"""add abandoned and enable_switcher_id fields to law check point

Revision ID: 554f1625ca69
Revises: 7af074160b1b
Create Date: 2025-07-07 14:14:14.243984

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "554f1625ca69"
down_revision = "7af074160b1b"
branch_labels = None
depends_on = None


table_name = "law_check_point"
column_name = "abandoned"
column_name2 = "enable_switcher_id"


def upgrade():
    op.add_column(table_name, sa.Column(column_name, sa.Boolean, server_default="0"))
    op.add_column(table_name, sa.Column(column_name2, sa.Integer))


def downgrade():
    op.drop_column(table_name, column_name2)
    op.drop_column(table_name, column_name)
