"""add refresh status fields to law order table

Revision ID: 65193c454a43
Revises: 60ca0e4885c6
Create Date: 2025-06-18 10:04:42.476580

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field

# revision identifiers, used by Alembic.
revision = "65193c454a43"
down_revision = "60ca0e4885c6"
branch_labels = None
depends_on = None


table_name = "law_order"
column_name = "refresh_status"


def upgrade():
    op.add_column(table_name, sa.Column(column_name, sa.SmallInteger, server_default="0"))  # schema 层兼容
    op.add_column(table_name, create_jsonb_field("meta", nullable=False, server_default=sa.text("'{}'::jsonb")))


def downgrade():
    op.drop_column(table_name, "meta")
    op.drop_column(table_name, column_name)
