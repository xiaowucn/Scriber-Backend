"""add new table chinaamc_compare_task

Revision ID: 36d690d4c2e0
Revises: ef9e2c59bbad
Create Date: 2024-04-01 15:35:06.806721

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "36d690d4c2e0"
down_revision = "ef9e2c59bbad"
branch_labels = None
depends_on = None

table = "chinaamc_compare_task"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("pid", sa.Integer, nullable=False, index=True),
        sa.Column("uid", sa.Integer, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        create_array_field("fids", sa.ARRAY(sa.Integer), nullable=False, server_default=sa.text("'{}'::integer[]")),
        sa.Column("rank", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.Integer, nullable=False, server_default=sa.text("0")),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    op.drop_table(table)
