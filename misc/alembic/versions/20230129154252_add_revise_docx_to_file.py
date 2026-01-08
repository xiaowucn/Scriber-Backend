"""add_revise_docx_to_file

Revision ID: 3d141ed507fb
Revises: a3f43de76c01
Create Date: 2023-01-29 15:42:52.761896

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3d141ed507fb"
down_revision = "a3f43de76c01"
branch_labels = None
depends_on = None
table = "file"


def upgrade():
    op.add_column(table, sa.Column("revise_docx", sa.String(255)))


def downgrade():
    op.drop_column(table, "revise_docx")
