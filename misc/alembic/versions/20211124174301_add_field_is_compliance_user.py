"""add field is_compliance_user

Revision ID: 468886368ee4
Revises: b5fd9af58c67
Create Date: 2021-11-24 17:43:01.325235

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "468886368ee4"
down_revision = "b5fd9af58c67"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cgs_result", sa.Column("is_compliance_user", sa.Boolean))
    op.add_column("cgs_result", sa.Column("user_reason", sa.Text))


def downgrade():
    op.drop_column("cgs_result", "is_compliance_user")
    op.drop_column("cgs_result", "user_reason")
