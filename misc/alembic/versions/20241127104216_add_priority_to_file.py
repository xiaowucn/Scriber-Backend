"""add priority to file

Revision ID: 4537191d8b24
Revises: 5cc2d31f1051
Create Date: 2024-11-27 10:42:16.842739

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "4537191d8b24"
down_revision = "5cc2d31f1051"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file", sa.Column("priority", sa.Integer, nullable=True, server_default=sa.text("9")))


def downgrade():
    op.drop_column("file", "priority")
