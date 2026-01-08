"""add field abandoned reason to law check point

Revision ID: d9204f3da621
Revises: 9e05240054d5
Create Date: 2025-07-14 11:58:38.402071

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d9204f3da621"
down_revision = "9e05240054d5"
branch_labels = None
depends_on = None


table_name = "law_check_point"
column_name = "abandoned_reason"


def upgrade():
    op.add_column(table_name, sa.Column(column_name, sa.String(255)))


def downgrade():
    op.drop_column(table_name, column_name)
