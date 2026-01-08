"""add_file_project_source

Revision ID: b221a24d0046
Revises: 3fbfd10873c5
Create Date: 2024-03-13 14:51:41.492407

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b221a24d0046"
down_revision = "3fbfd10873c5"
branch_labels = None
depends_on = None
table = "file_project"


def upgrade():
    op.add_column(table, sa.Column("source", sa.String(255)))


def downgrade():
    op.drop_column(table, "source")
