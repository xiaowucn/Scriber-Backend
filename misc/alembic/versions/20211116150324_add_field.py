"""add field

Revision ID: 860331f17514
Revises: 941c0ed9fac3
Create Date: 2021-11-16 15:03:24.634633

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "860331f17514"
down_revision = "941c0ed9fac3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cgs_result", sa.Column("is_builtin", sa.Boolean))


def downgrade():
    op.drop_column("cgs_rule", "is_builtin")
