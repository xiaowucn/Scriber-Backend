"""add_sse_export_answer

Revision ID: 318ef1d9fe3b
Revises: 033f99cff0b1
Create Date: 2019-06-11 10:52:59.532235

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
from remarkable.common.migrate_util import create_jsonb_field, create_timestamp_field

revision = "318ef1d9fe3b"
down_revision = "033f99cff0b1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "special_answer",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("qid", sa.Integer),
        sa.Column("answer_type", sa.String(255)),
        create_jsonb_field("data"),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
    )


def downgrade():
    op.drop_table("special_answer")
