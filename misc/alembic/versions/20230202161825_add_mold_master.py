"""add_mold_master

Revision ID: 0651c57946f2
Revises: 3d141ed507fb
Create Date: 2023-02-02 16:18:25.092259

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0651c57946f2"
down_revision = "3d141ed507fb"
branch_labels = None
depends_on = None
table = "mold"


def upgrade():
    op.add_column(table, sa.Column("master", sa.Integer))


def downgrade():
    op.drop_column(table, "master")
