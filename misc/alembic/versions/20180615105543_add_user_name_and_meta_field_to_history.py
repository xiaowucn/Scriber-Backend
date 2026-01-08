"""add user name and meta field to history

Revision ID: ca981d513a9f
Revises: ca20cb00c91c
Create Date: 2018-06-15 10:55:43.875496

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ca981d513a9f"
down_revision = "ca20cb00c91c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("history", sa.Column("user_name", sa.String(255)))
    op.add_column("history", sa.Column("meta", sa.JSON))


def downgrade():
    op.drop_column("history", "user_name")
    op.drop_column("history", "meta")
