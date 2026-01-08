"""add_cgs_dev_rule

Revision ID: 879736f1b4a7
Revises: 8ce5a303d5d5
Create Date: 2022-12-13 16:05:16.168533

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "879736f1b4a7"
down_revision = "8ce5a303d5d5"
branch_labels = None
depends_on = None
table = "cgs_dev_rule"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, primary_key=True),
        create_timestamp_field(
            "created_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("rule_type", sa.String(255), nullable=False, index=True),
        sa.Column("content", sa.Text, nullable=False),
    )


def downgrade():
    op.drop_table(table)
