"""add alias field to law check_point

Revision ID: 0e8c6392549e
Revises: b3100f27c465
Create Date: 2025-07-28 09:53:28.454000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0e8c6392549e"
down_revision = "b3100f27c465"
branch_labels = None
depends_on = None


table_name = "law_check_point"
column_name = "alias_name"
column_op_name = "alias_by_id"


def upgrade():
    op.add_column(table_name, sa.Column(column_name, sa.String(255), nullable=True))
    op.add_column(table_name, sa.Column(column_op_name, sa.Integer, nullable=True))


def downgrade():
    op.drop_column(table_name, column_name)
    op.drop_column(table_name, column_op_name)
