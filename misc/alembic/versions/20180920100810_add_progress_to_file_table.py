"""add_progress_to_file_table

Revision ID: 723e8d943441
Revises: 5b6c66aeefbb
Create Date: 2018-09-20 10:08:10.916034

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "723e8d943441"
down_revision = "5b6c66aeefbb"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file", sa.Column("progress", sa.String(255)))


def downgrade():
    op.drop_column("file", "progress")
