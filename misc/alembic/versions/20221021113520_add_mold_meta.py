"""add_mold_meta

Revision ID: b160c4f9833f
Revises: cd509277737c
Create Date: 2022-10-21 11:35:20.673237

"""

from alembic import op

from remarkable.common.migrate_util import create_jsonb_field

# revision identifiers, used by Alembic.
revision = "b160c4f9833f"
down_revision = "cd509277737c"
branch_labels = None
depends_on = None
table = "mold"


def upgrade():
    op.add_column(table, create_jsonb_field("meta"))


def downgrade():
    op.drop_column(table, "meta")
