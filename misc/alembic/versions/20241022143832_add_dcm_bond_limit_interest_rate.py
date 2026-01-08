"""add_dcm_bond_limit_interest_rate

Revision ID: c6c4c0b7142a
Revises: badd9f68f5a2
Create Date: 2024-10-22 14:38:32.850595

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c6c4c0b7142a"
down_revision = "badd9f68f5a2"
branch_labels = None
depends_on = None
table = "dcm_bond_limit"


def upgrade():
    op.add_column(table, sa.Column("interest_rate", sa.String(255)))


def downgrade():
    op.drop_column(table, "interest_rate")
