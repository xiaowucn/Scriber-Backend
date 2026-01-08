"""add_predictors_to_mold

Revision ID: a2ae2d2589ce
Revises: 7756a52ff32f
Create Date: 2019-09-18 16:48:49.298350

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a2ae2d2589ce"
down_revision = "7f9b30218e95"
branch_labels = None
depends_on = None
table = "mold"


def upgrade():
    op.add_column(table, sa.Column("predictors", sa.JSON))


def downgrade():
    op.drop_column(table, "predictors")
