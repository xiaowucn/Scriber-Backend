"""add template flag field to law tables

Revision ID: a12efbf8a77b
Revises: 8b7bbb10703f
Create Date: 2025-09-08 15:21:35.102121
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a12efbf8a77b"
down_revision = "8b7bbb10703f"
branch_labels = None
depends_on = None

table_names = ["law", "law_order"]
column_name = "is_template"


def upgrade():
    for table_name in table_names:
        op.add_column(table_name, sa.Column(column_name, sa.Boolean, server_default=sa.text("false"), nullable=False))


def downgrade():
    for table_name in table_names:
        op.drop_column(table_name, column_name)
