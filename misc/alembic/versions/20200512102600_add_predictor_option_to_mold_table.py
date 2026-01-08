"""add predictor_option to mold table

Revision ID: 779c1ebf1e6e
Revises: 4a77bf575cd7
Create Date: 2020-05-12 10:26:00.988214

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.

revision = "779c1ebf1e6e"
down_revision = "4a77bf575cd7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("mold", sa.Column("predictor_option", sa.JSON))


def downgrade():
    op.drop_column("mold", "predictor_option")
