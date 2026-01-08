"""create table rule result

Revision ID: c461565ae980
Revises: 71df5399f3e8
Create Date: 2019-03-04 12:21:09.574336

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "c461565ae980"
down_revision = "71df5399f3e8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rule_result",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("rule", sa.String(255), nullable=False),
        create_array_field("schema_cols", sa.ARRAY(sa.String)),
        sa.Column("result", sa.Integer, server_default="0", nullable=False),
        sa.Column("comment", sa.String(1024)),
        sa.Column("comment_pos", sa.JSON),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    op.drop_table("rule_result")
