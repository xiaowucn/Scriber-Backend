"""add_answer_data_status

Revision ID: 0b2f0841ff47
Revises: a81d4e12b9e9
Create Date: 2025-07-09 18:00:49.006026

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "0b2f0841ff47"
down_revision = "a81d4e12b9e9"
branch_labels = None
depends_on = None

table_name = "answer_data_stat"


def upgrade():
    op.create_table(
        table_name,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("answer_data_id", sa.Integer, index=True),
        sa.Column("qid", sa.Integer, nullable=False),
        sa.Column("uid", sa.Integer, nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("content", sa.Text),
        sa.Column("record", sa.Boolean, server_default=sa.text("false")),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    op.drop_table(table_name)
