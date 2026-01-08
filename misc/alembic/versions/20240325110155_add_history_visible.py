"""add_history_visible

Revision ID: c0d9fe6e85f8
Revises: 62170ff57718
Create Date: 2024-03-25 11:01:55.377598

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c0d9fe6e85f8"
down_revision = "62170ff57718"
branch_labels = None
depends_on = None
table = "history"


def upgrade():
    op.add_column(table, sa.Column("visible", sa.Boolean, server_default=sa.text("true")))


def downgrade():
    op.drop_column(table, "visible")
