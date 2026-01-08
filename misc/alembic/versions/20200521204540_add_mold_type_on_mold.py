"""add mold type on mold

Revision ID: 960aace38f4d
Revises: 779c1ebf1e6e
Create Date: 2020-05-21 20:45:40.668119

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "960aace38f4d"
down_revision = "779c1ebf1e6e"
branch_labels = None
depends_on = None
table = "mold"


def upgrade():
    op.add_column(table, sa.Column("mold_type", sa.Integer))
    op.execute(
        """
        UPDATE mold set mold_type = 0 WHERE mold_type is null;
    """
    )


def downgrade():
    op.drop_column(table, "mold_type")
