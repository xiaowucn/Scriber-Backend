"""add_file_project_status

Revision ID: 4e8758f73e3a
Revises: b221a24d0046
Create Date: 2024-03-15 12:13:32.728137

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "4e8758f73e3a"
down_revision = "b221a24d0046"
branch_labels = None
table = "file_project"


def upgrade():
    op.add_column(table, sa.Column("status", sa.String(255)))


def downgrade():
    op.drop_column(table, "status")
