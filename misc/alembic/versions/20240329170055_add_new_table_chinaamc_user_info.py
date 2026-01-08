"""add new table chinaamc_user_info

Revision ID: ef9e2c59bbad
Revises: 5916e6f75d62
Create Date: 2024-03-29 11:28:18.710011

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "ef9e2c59bbad"
down_revision = "5916e6f75d62"
branch_labels = None
depends_on = None

table = "chinaamc_user_info"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("uid", sa.Integer, nullable=False, unique=True),
        create_array_field("dept_ids", sa.ARRAY(sa.Text), nullable=False, server_default=sa.text("'{}'::text[]")),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    op.drop_table(table)
