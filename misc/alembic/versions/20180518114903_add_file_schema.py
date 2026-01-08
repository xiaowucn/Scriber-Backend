"""add file schema

Revision ID: 1bfeb34e6a27
Revises: 4ea9158f33bf
Create Date: 2018-05-18 11:49:03.905561

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1bfeb34e6a27"
down_revision = "4ea9158f33bf"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file_tree", sa.Column("default_mold", sa.Integer))
    op.add_column("file", sa.Column("mold", sa.Integer))


def downgrade():
    op.drop_column("file_tree", "default_mold")
    op.drop_column("file", "mold")
