"""add column to nafmii_file_info

Revision ID: 6ba57dc0d73e
Revises: 12a87a40feb7
Create Date: 2025-08-27 11:54:29.519556
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6ba57dc0d73e"
down_revision = "12a87a40feb7"
branch_labels = None
depends_on = None

table_name = "nafmii_file_info"
column_name = "flag"


def upgrade():
    op.add_column(table_name, sa.Column(column_name, sa.Integer, nullable=False, server_default="0"))


def downgrade():
    op.drop_column(table_name, column_name)
