"""add rank to file

Revision ID: 47b6faeaeded
Revises: 974e147f86ab
Create Date: 2024-03-20 10:49:01.000383

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "47b6faeaeded"
down_revision = "974e147f86ab"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file", sa.Column("rank", sa.Integer, nullable=False, server_default=sa.text("0")))


def downgrade():
    op.drop_column("file", "rank")
