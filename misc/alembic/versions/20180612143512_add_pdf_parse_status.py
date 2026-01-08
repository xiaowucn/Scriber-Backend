"""add pdf parse status

Revision ID: 54c9c565a9f2
Revises: c33f64548a56
Create Date: 2018-06-12 14:35:12.238443

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "54c9c565a9f2"
down_revision = "c33f64548a56"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file", sa.Column("pdf_parse_status", sa.Integer))


def downgrade():
    op.drop_column("file", "pdf_parse_status")
