"""add scenario and chatdoc_unique fields to file

Revision ID: acc6d6c86727
Revises: 9f3880fb5348
Create Date: 2025-07-23 14:41:03.033104

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "acc6d6c86727"
down_revision = "9f3880fb5348"
branch_labels = None
depends_on = None


table_name = "file"
column_name = "scenario_id"
column_name2 = "chatdoc_unique"


def upgrade():
    op.add_column(table_name, sa.Column(column_name, sa.Integer, index=True))
    op.add_column(table_name, sa.Column(column_name2, sa.String(255)))


def downgrade():
    op.drop_column(table_name, column_name)
    op.drop_column(table_name, column_name2)
