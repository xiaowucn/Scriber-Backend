"""add_external_source

Revision ID: d222a86c4333
Revises: 648403fcd88b
Create Date: 2024-10-12 09:43:55.219225

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d222a86c4333"
down_revision = "648403fcd88b"
branch_labels = None
depends_on = None
table = "ecitic_compare_record"


def upgrade():
    op.add_column(table, sa.Column("external_source", sa.String(255)))


def downgrade():
    op.drop_column(table, "external_source")
