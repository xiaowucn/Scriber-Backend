"""add_deleted_utc_to_mold

Revision ID: 541ac77c371f
Revises: 318ef1d9fe3b
Create Date: 2019-07-22 16:51:12.927464

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "541ac77c371f"
down_revision = "318ef1d9fe3b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("mold", sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")))


def downgrade():
    op.drop_column("mold", "deleted_utc")
