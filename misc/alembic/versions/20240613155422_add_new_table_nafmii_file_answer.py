"""add new table nafmii_file_answer

Revision ID: c7c9b14317e5
Revises: cac4de4cc3b0
Create Date: 2024-06-13 15:54:22.496709

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "c7c9b14317e5"
down_revision = "cac4de4cc3b0"
branch_labels = None
depends_on = None
table = "nafmii_file_answer"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("fid", sa.Integer, nullable=False, index=True, unique=True),
        sa.Column("status", sa.Integer, nullable=False, server_default=sa.text("0")),
        create_jsonb_field("schema", nullable=False, server_default=sa.text("'[]'::jsonb")),
        create_jsonb_field("answer", nullable=False, server_default=sa.text("'[]'::jsonb")),
        create_timestamp_field(
            "created_utc", sa.Integer, nullable=False, server_default=sa.text("extract(epoch from now())::int")
        ),
        create_timestamp_field(
            "updated_utc", sa.Integer, nullable=False, server_default=sa.text("extract(epoch from now())::int")
        ),
    )


def downgrade():
    op.drop_table(table)
