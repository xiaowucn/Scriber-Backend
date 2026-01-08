"""add_user_role_ref

Revision ID: 685bcb7407ce
Revises: f4fdc6836807
Create Date: 2024-08-28 14:20:00.609657

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "685bcb7407ce"
down_revision = "f4fdc6836807"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_role_ref",
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("user_id", sa.Integer),
        sa.Column("role_id", sa.Integer),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )

    op.create_table(
        "role_permission_ref",
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("role_id", sa.Integer),
        sa.Column("permission_id", sa.Integer),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )

    op.create_unique_constraint("user_role_ref_unique", "user_role_ref", ["user_id", "role_id"])
    op.create_unique_constraint("role_permission_ref_unique", "role_permission_ref", ["role_id", "permission_id"])


def downgrade():
    op.drop_table("user_role_ref")
    op.drop_table("role_permission_ref")
