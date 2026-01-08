"""create law rules table

Revision ID: 60ca0e4885c6
Revises: db5b1076e57c
Create Date: 2025-06-11 15:10:45.499700

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "60ca0e4885c6"
down_revision = "db5b1076e57c"
branch_labels = None
depends_on = None


table_name = "law_rule"
table2_name = "law_rules_scenarios"


def upgrade():
    op.create_table(
        table_name,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("law_id", sa.Integer, index=True),
        sa.Column("content", sa.Text),
        sa.Column("enable", sa.Boolean, server_default="0"),
        sa.Column("status", sa.SmallInteger, server_default="0"),
        sa.Column("prompt", sa.Text),
        create_array_field("keywords", sa.ARRAY(sa.Text), nullable=False, server_default=sa.text("'{}'::text[]")),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
        sa.Column("updated_by_id", sa.Integer),
    )

    op.create_table(
        table2_name,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("rule_id", sa.Integer, nullable=False, index=True),
        sa.Column("scenario_id", sa.Integer, nullable=False, index=True),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
        sa.Column("updated_by_id", sa.Integer),
    )


def downgrade():
    op.drop_table(table2_name)
    op.drop_table(table_name)
