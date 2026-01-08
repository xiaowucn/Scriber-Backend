"""create law check point table

Revision ID: 699d0e470e64
Revises: 5b3de4ad2921
Create Date: 2025-07-02 12:05:42.139116

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "699d0e470e64"
down_revision = "5b3de4ad2921"
branch_labels = None
depends_on = None


table_name = "law_check_point"


def upgrade():
    op.create_table(
        table_name,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("order_id", sa.Integer, nullable=False, index=True),
        sa.Column("rule_id", sa.Integer, nullable=False),
        sa.Column("rule_content", sa.Text, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("subject", sa.Text, nullable=False),
        sa.Column("check_type", sa.SmallInteger, nullable=False),
        sa.Column("core", sa.Text, nullable=False),
        sa.Column("check_method", sa.Text, nullable=False),
        sa.Column("review_status", sa.SmallInteger, nullable=False),
        create_jsonb_field("meta", nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("enable", sa.Boolean, default="0"),
        sa.Column("parent_id", sa.Integer, nullable=True),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
        sa.Column("updated_by_id", sa.Integer),
        sa.Column("reviewer_id", sa.Integer),
    )


def downgrade():
    op.drop_table(table_name)
