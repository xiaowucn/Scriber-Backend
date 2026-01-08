"""add_col_progress_on_mold

Revision ID: 614f837441a0
Revises: 223d41686db3
Create Date: 2019-05-08 18:56:13.683185

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "614f837441a0"
down_revision = "223d41686db3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("mold", sa.Column("progress", sa.Float, server_default=sa.text("0")))
    op.add_column("mold", sa.Column("comment", sa.String(1024)))


def downgrade():
    op.drop_column("mold", "progress")
    op.drop_column("mold", "comment")
