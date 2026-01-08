"""add_law_on_cgs_dev_rule

Revision ID: 5e7dcb5dd300
Revises: 8923af538902
Create Date: 2023-01-06 14:24:33.251338

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5e7dcb5dd300"
down_revision = "8923af538902"
branch_labels = None
depends_on = None
table = "cgs_dev_rule"


def upgrade():
    op.add_column(table, sa.Column("law_id", sa.String(255), index=True))
    op.add_column(table, sa.Column("law", sa.String(255)))


def downgrade():
    op.drop_column(table, "law_id")
    op.drop_column(table, "law")
