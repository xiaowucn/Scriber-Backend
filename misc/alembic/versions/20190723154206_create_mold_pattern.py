"""create mold pattern

Revision ID: b7fba2b32ffa
Revises: 318ef1d9fe3b
Create Date: 2019-03-26 15:42:06.137408

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "b7fba2b32ffa"
down_revision = "541ac77c371f"
branch_labels = None
depends_on = None


def upgrade():
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


def downgrade():
    op.drop_table("mold_pattern")
