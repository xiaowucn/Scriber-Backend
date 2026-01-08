"""add column push_answer_at to nafmii_file_info

Revision ID: 71999603561c
Revises: 6ba57dc0d73e
Create Date: 2025-08-27 18:31:25.771721
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "71999603561c"
down_revision = "6ba57dc0d73e"
branch_labels = None
depends_on = None

table_name = "nafmii_file_info"
column_name = "push_answer_at"


def upgrade():
    op.add_column(table_name, sa.Column(column_name, sa.Integer, nullable=False, server_default="0"))


def downgrade():
    op.drop_column(table_name, column_name)
