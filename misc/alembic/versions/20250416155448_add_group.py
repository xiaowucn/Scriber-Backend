"""add_group

Revision ID: 1f98e63f9085
Revises: 84095debb368
Create Date: 2025-04-11 15:54:48.607706

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "1f98e63f9085"
down_revision = "84095debb368"
branch_labels = None
depends_on = None

table = "cmf_group"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("name", sa.String(255), unique=True),
        sa.Column("description", sa.String(255)),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )

    op.create_table(
        "cmf_user_group_ref",
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("user_id", sa.Integer),
        sa.Column("cmf_group_id", sa.Integer),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )

    op.create_index("cmf_user_group_ref_unique", "cmf_user_group_ref", ["user_id", "cmf_group_id"], unique=True)

    op.create_table(
        "cmf_group_ref",
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("cmf_group_id", sa.Integer),
        sa.Column("file_tree_id", sa.Integer),
        sa.Column("mold_id", sa.Integer),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
    op.create_index("cmf_group_file_tree_ref_unique", "cmf_group_ref", ["cmf_group_id", "file_tree_id"], unique=True)
    op.create_index("cmf_group_mold_ref_unique", "cmf_group_ref", ["cmf_group_id", "mold_id"], unique=True)


def downgrade():
    op.drop_table("cmf_group_ref")
    op.drop_table("cmf_user_group_ref")
    op.drop_table(table)
