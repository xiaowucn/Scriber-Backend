"""add_col_link_on_file

Revision ID: 0fa641f8c14f
Revises: 771b3e7d47b3
Create Date: 2019-11-06 18:41:58.598521

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0fa641f8c14f"
down_revision = "771b3e7d47b3"
branch_labels = None
depends_on = None
table = "file"


def upgrade():
    op.add_column(table, sa.Column("link", sa.String(500), server_default=sa.text("''")))


def downgrade():
    op.drop_column(table, "link")
