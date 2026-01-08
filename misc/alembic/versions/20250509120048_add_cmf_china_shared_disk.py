"""add_cmf_china_shared_disk

Revision ID: 72463ab32507
Revises: 08037aaaa0dd
Create Date: 2025-05-09 12:00:48.445625

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "72463ab32507"
down_revision = "08037aaaa0dd"
branch_labels = None
depends_on = None

CMF_SHARED_DISK = "cmf_shared_disk"


def upgrade():
    op.create_table(
        CMF_SHARED_DISK,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("file_id", sa.Integer, nullable=False),
        sa.Column("path", sa.String(1024), nullable=False, server_default=""),
    )
    op.create_index("idx_cmf_shared_disk_file_id", CMF_SHARED_DISK, ["file_id"], unique=True)


def downgrade():
    op.drop_table(CMF_SHARED_DISK)
