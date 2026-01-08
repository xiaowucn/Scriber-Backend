"""add_abandoned_utc_to_file

Revision ID: ca1ed427c8a3
Revises: 84ed15a816fb
Create Date: 2023-02-21 14:36:53.134561

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ca1ed427c8a3"
down_revision = "84ed15a816fb"
branch_labels = None
depends_on = None
table = "file"


def upgrade():
    op.add_column(
        table,
        sa.Column("abandoned_utc", sa.Integer, server_default=sa.text("0")),
    )


def downgrade():
    op.drop_column(table, "abandoned_utc")
