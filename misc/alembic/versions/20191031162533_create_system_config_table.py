"""create system_config table

Revision ID: 771b3e7d47b3
Revises: a876d91ce06c
Create Date: 2019-10-31 16:25:33.852899

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "771b3e7d47b3"
down_revision = "7eafbf6d13db"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "system_config",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("data", sa.JSON),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    op.drop_table("system_config")
