"""add_last_tree_id_to_file

Revision ID: c70c103b2e85
Revises: 4e2853667d69
Create Date: 2023-02-28 09:52:36.593674

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c70c103b2e85"
down_revision = "4e2853667d69"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "file",
        sa.Column("origin_tree_id", sa.Integer),
    )
    op.add_column(
        "file_tree",
        sa.Column("origin_ptree_id", sa.Integer),
    )


def downgrade():
    op.drop_column("file", "origin_tree_id")
    op.drop_column("file_tree", "origin_ptree_id")
