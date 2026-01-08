"""alter_cgs_dev_rule

Revision ID: c8bab52d800b
Revises: 699d0e470e64
Create Date: 2025-07-03 16:22:18.092417

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c8bab52d800b"
down_revision = "699d0e470e64"
branch_labels = None
depends_on = None

table = "cgs_dev_rule"


def upgrade():
    op.alter_column(table, "law", type_=sa.Text, existing_type=sa.String(255))


def downgrade():
    op.alter_column(table, "law", type_=sa.String(255), existing_type=sa.Text)
