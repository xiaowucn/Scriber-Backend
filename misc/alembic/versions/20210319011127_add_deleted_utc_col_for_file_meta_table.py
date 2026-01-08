"""add deleted_utc col for file_meta table

Revision ID: 6dea995b45fa
Revises: 935fa0752f8c
Create Date: 2021-03-19 01:11:27.192477

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6dea995b45fa"
down_revision = "935fa0752f8c"
branch_labels = None
depends_on = None
table = "file_meta"
col = "deleted_utc"


def upgrade():
    op.add_column(table, sa.Column(col, sa.Integer, server_default=sa.text("0")))


def downgrade():
    op.drop_column(table, col)
