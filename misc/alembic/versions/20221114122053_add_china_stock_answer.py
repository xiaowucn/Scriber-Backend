"""add_china_stock_answer

Revision ID: b5c207e9eab7
Revises: b160c4f9833f
Create Date: 2022-11-14 12:20:53.561692

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "b5c207e9eab7"
down_revision = "b160c4f9833f"
branch_labels = None
depends_on = None
table_name = "china_stock_answer"


def upgrade():
    op.create_table(
        table_name,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("fid", sa.Integer, nullable=False),
        sa.Column("qid", sa.Integer, nullable=False, unique=True),
        sa.Column("tree_id", sa.Integer, nullable=False),
        sa.Column("product_name", sa.String(255)),
        sa.Column("manager_name", sa.String(255)),
        sa.Column("file_source", sa.String(255)),
        create_jsonb_field("meta"),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    op.drop_table(table_name)
