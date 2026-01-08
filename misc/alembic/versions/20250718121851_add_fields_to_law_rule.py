"""add fields to law_rule

Revision ID: 9f3880fb5348
Revises: d9204f3da621
Create Date: 2025-07-18 12:18:51.951256

"""

import sqlalchemy as sa
from alembic import op

from remarkable.db import IS_MYSQL

# revision identifiers, used by Alembic.
revision = "9f3880fb5348"
down_revision = "d9204f3da621"
branch_labels = None
depends_on = None


table_name = "law_rule"
column_name = "order_id"
column_name2 = "match_all"


def upgrade():
    op.add_column(table_name, sa.Column(column_name2, sa.Boolean, server_default="1"))
    op.add_column(table_name, sa.Column(column_name, sa.Integer, index=True))
    if not IS_MYSQL:
        op.execute("""UPDATE law_rule SET order_id = law.order_id FROM law WHERE law_rule.law_id = law.id;""")


def downgrade():
    op.drop_column(table_name, column_name)
    op.drop_column(table_name, column_name2)
