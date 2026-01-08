"""add templates field to law_check_point table

Revision ID: 733e791c692c
Revises: 5cfccf6f540c
Create Date: 2025-08-19 16:57:08.196356
"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field

revision = "733e791c692c"
down_revision = "5cfccf6f540c"
branch_labels = None
depends_on = None

table_name = "law_check_point"


def upgrade():
    op.add_column(table_name, create_jsonb_field("templates", nullable=True))

    op.alter_column(table_name, "check_method", nullable=True, existing_type=sa.Text)


def downgrade():
    op.drop_column(table_name, "templates")

    op.alter_column(table_name, "check_method", nullable=False, existing_type=sa.Text)
