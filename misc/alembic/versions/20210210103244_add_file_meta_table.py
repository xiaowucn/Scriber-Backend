"""Add file_meta table

Revision ID: f392233cbb51
Revises: da53f64d93d3
Create Date: 2021-02-10 10:32:44.011919

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "f392233cbb51"
down_revision = "da53f64d93d3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "file_meta",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("file_id", sa.Integer, unique=True, index=True),
        sa.Column("hash", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("stock_code", sa.String(255), nullable=False),
        sa.Column("stock_name", sa.String(255), nullable=False),
        sa.Column("report_year", sa.Integer),
        sa.Column("rule_name", sa.String(255), nullable=False, index=True),
        sa.Column("publish_time", sa.Integer, nullable=False),
        sa.Column("raw_data", sa.JSON, nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
    op.create_index("uq_rule_name_hash", "file_meta", ["rule_name", "hash"], unique=True)


def downgrade():
    op.drop_table("file_meta")
