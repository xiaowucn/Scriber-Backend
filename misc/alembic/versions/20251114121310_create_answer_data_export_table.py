"""create answer data export table

Revision ID: e6241a0824bf
Revises: 8c9048aa75c8
Create Date: 2025-11-14 12:13:10.149989
"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "e6241a0824bf"
down_revision = "8c9048aa75c8"
branch_labels = None
depends_on = None

table_name = "answer_data_export"


def upgrade():
    op.create_table(
        table_name,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("pid", sa.Integer, nullable=False),
        sa.Column("status", sa.Integer, server_default=sa.text("1")),
        sa.Column("task_total", sa.Integer, server_default=sa.text("0")),
        sa.Column("task_done", sa.Integer, server_default=sa.text("0")),
        create_array_field("files_ids", sa.ARRAY(sa.Integer)),
        sa.Column("zip_path", sa.String(255)),
        create_timestamp_field(
            "created_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
    )


def downgrade():
    op.drop_table(table_name)
