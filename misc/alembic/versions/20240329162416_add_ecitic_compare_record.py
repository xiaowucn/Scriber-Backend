"""add_ecitic_compare_record

Revision ID: 0d41b614d5c8
Revises: 7d196d6dfae1
Create Date: 2024-03-29 16:24:16.164822

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "0d41b614d5c8"
down_revision = "7d196d6dfae1"
branch_labels = None
depends_on = None


table = "ecitic_compare_record"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("qid", sa.Integer, nullable=False, index=True),
        sa.Column("std_qid", sa.Integer, nullable=False, index=True),
        sa.Column("mold", sa.Integer, nullable=False, index=True),
        sa.Column("trigger_type", sa.Integer, nullable=False, index=True),
        sa.Column("uid", sa.Integer, nullable=False),
        sa.Column("is_diff", sa.Boolean, server_default=sa.text("true"), index=True),
        create_jsonb_field("question", nullable=False),
        create_jsonb_field("std_question", nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, nullable=False, server_default=sa.text("0")),
    )


def downgrade():
    op.drop_table(table)
