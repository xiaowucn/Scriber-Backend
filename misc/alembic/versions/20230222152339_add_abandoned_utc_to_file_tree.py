"""add_abandoned_utc_to_file_tree

Revision ID: 33d6332107dd
Revises: ca1ed427c8a3
Create Date: 2023-02-22 15:23:39.050750

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "33d6332107dd"
down_revision = "ca1ed427c8a3"
branch_labels = None
depends_on = None
table = "file_tree"


def upgrade():
    op.add_column(
        table,
        sa.Column("abandoned_utc", sa.Integer, server_default=sa.text("0")),
    )


def downgrade():
    op.drop_column(table, "abandoned_utc")
