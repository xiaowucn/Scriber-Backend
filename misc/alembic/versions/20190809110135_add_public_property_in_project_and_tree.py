"""add_public_property_in_project_and_tree

Revision ID: 8d3dd1c34700
Revises: 033f99cff0b1
Create Date: 2019-08-09 11:01:35.158220

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8d3dd1c34700"
down_revision = "033f99cff0b1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file_project", sa.Column("uid", sa.Integer, server_default=sa.text("-1")))
    op.add_column("file_tree", sa.Column("uid", sa.Integer, server_default=sa.text("-1")))


def downgrade():
    op.drop_column("file_project", "uid")
    op.drop_column("file_tree", "uid")
