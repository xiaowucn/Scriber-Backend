"""reset deleted law order rank

Revision ID: 7af074160b1b
Revises: c8bab52d800b
Create Date: 2025-07-04 18:27:29.191870

"""

from alembic import op

from remarkable.db import IS_MYSQL

# revision identifiers, used by Alembic.
revision = "7af074160b1b"
down_revision = "c8bab52d800b"
branch_labels = None
depends_on = None


def upgrade():
    rank = "`rank`" if IS_MYSQL else "rank"
    op.execute(f"update law_order set {rank} = null where deleted_utc != 0 and {rank} > 0;")


def downgrade():
    pass
