"""add schema_id

Revision ID: e19465080dd7
Revises: 8dbdb1f4ad3c
Create Date: 2021-11-01 18:52:12.514832

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e19465080dd7"
down_revision = "8dbdb1f4ad3c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cgs_rule", sa.Column("schema_id", sa.Integer))
    op.add_column("cgs_result", sa.Column("schema_id", sa.Integer))


def downgrade():
    op.drop_column("cgs_rule", "schema_id")
    op.drop_column("cgs_result", "schema_id")
