"""add_cgs_rule_public

Revision ID: d40ae3bae312
Revises: ace0d163721c
Create Date: 2024-09-05 14:41:21.858187

"""

import sqlalchemy as sa
from alembic import op

table = "cgs_rule"


# revision identifiers, used by Alembic.
revision = "d40ae3bae312"
down_revision = "0cd100623ad7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(table, sa.Column("public", sa.Boolean, server_default=sa.text("true")))
    op.execute(f"update {table} set public=true")


def downgrade():
    op.drop_column(table, "public")
