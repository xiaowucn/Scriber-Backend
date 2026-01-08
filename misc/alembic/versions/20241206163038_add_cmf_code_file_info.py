"""add_cmf_code_file_info

Revision ID: 4ce1e114a324
Revises: 7656159bfb68
Create Date: 2024-12-06 16:30:38.163345

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "4ce1e114a324"
down_revision = "7656159bfb68"
branch_labels = None
depends_on = None

# Table names as variables
CMF_FILED_FILE_INFO = "cmf_filed_file_info"


def upgrade():
    op.create_table(
        CMF_FILED_FILE_INFO,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("fid", sa.Integer, nullable=False),
        sa.Column("status", sa.Integer, nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
    op.create_index("cmf_filed_file_info_fid_key", CMF_FILED_FILE_INFO, ["fid"], unique=True)


def downgrade():
    op.drop_table(CMF_FILED_FILE_INFO)
