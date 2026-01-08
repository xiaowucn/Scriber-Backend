"""add_predictors_to_model_version

Revision ID: a876d91ce06c
Revises: a2ae2d2589ce
Create Date: 2019-10-14 17:00:22.660805

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a876d91ce06c"
down_revision = "a2ae2d2589ce"
branch_labels = None
depends_on = None
table = "model_version"


def upgrade():
    op.add_column(table, sa.Column("predictors", sa.JSON))


def downgrade():
    op.drop_column(table, "predictors")
