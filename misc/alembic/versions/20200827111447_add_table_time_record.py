"""add table time record

Revision ID: 2abae5e447f2
Revises: e070a617d639
Create Date: 2020-08-27 11:14:47.106626

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "2abae5e447f2"
down_revision = "e070a617d639"
branch_labels = None
depends_on = None
table_name = "time_record"


def upgrade():
    op.create_table(
        table_name,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("fid", sa.Integer, nullable=False, index=True),
        sa.Column("upload_stamp", sa.Integer),
        sa.Column("insight_queue_stamp", sa.Integer),
        sa.Column("insight_parse_stamp", sa.Integer),
        sa.Column("pdf_parse_stamp", sa.Integer),
        sa.Column("prompt_stamp", sa.Integer),
        sa.Column("preset_stamp", sa.Integer),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
    )


def downgrade():
    op.drop_table(table_name)
