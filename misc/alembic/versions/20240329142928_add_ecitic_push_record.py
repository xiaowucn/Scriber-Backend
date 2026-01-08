"""add_ecitic_push_record

Revision ID: 7d196d6dfae1
Revises: 1cda4a8e0b0c
Create Date: 2024-03-29 14:29:28.295039

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "7d196d6dfae1"
down_revision = "1cda4a8e0b0c"
branch_labels = None
depends_on = None


table = "ecitic_push_record"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("fid", sa.Integer, nullable=False, index=True),
        sa.Column("task_type", sa.Integer, nullable=False, index=True),
        sa.Column("push_type", sa.Integer, nullable=False, index=True),
        sa.Column("uid", sa.Integer, nullable=False),
        sa.Column("status", sa.Integer, nullable=False),
        sa.Column("data", sa.JSON, nullable=False),
        sa.Column("external_source", sa.String(255), nullable=False),
        sa.Column("visible", sa.Boolean, server_default=sa.text("true"), index=True),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    op.drop_table(table)
