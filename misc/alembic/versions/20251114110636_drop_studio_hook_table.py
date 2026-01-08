"""drop studio hook table

Revision ID: 8c9048aa75c8
Revises: 51cbcb3e1cc6
Create Date: 2025-11-14 11:06:36.456128
"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "8c9048aa75c8"
down_revision = "51cbcb3e1cc6"
branch_labels = None
depends_on = None

table_name = "studio_hook"


def upgrade():
    op.drop_table(table_name)


def downgrade():
    op.create_table(
        table_name,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("hook_id", sa.String(16), nullable=False),
        sa.Column("callback_url", sa.String(255), nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
