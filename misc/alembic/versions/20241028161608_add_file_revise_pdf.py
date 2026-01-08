"""add_file_revise_pdf

Revision ID: badd9f68f5a2
Revises: 798d1e80a1a6
Create Date: 2024-10-28 16:16:08.388716

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "badd9f68f5a2"
down_revision = "798d1e80a1a6"
branch_labels = None
depends_on = None
table = "file"


def upgrade():
    op.add_column(table, sa.Column("revise_pdf", sa.String(255)))


def downgrade():
    op.drop_column(table, "revise_pdf")
