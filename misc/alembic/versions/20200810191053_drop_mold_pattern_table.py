"""drop mold_pattern table

Revision ID: c60d629a263e
Revises: ab87d7eefb48
Create Date: 2020-08-10 19:10:53.260440

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "c60d629a263e"
down_revision = "ab87d7eefb48"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("mold_pattern")


def downgrade():
    op.create_table(
        "mold_pattern",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("mold_id", sa.Integer, nullable=False, unique=True, index=True),
        sa.Column("patterns", sa.JSON),
        create_timestamp_field(
            "created_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
        create_timestamp_field(
            "updated_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
    )
