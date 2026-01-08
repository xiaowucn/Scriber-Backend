"""add_cmf_model_file_ref

Revision ID: 7656159bfb68
Revises: 6d5d07276c87
Create Date: 2024-12-06 16:11:23.933091

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "7656159bfb68"
down_revision = "6d5d07276c87"
branch_labels = None
depends_on = None

# Table names as variables
CMF_MODEL_FILE_REF = "cmf_model_file_ref"


def upgrade():
    op.create_table(
        CMF_MODEL_FILE_REF,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("model_id", sa.Integer, nullable=False),
        sa.Column("fid", sa.Integer, nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
    op.create_index("cmf_model_file_ref_fid_key", CMF_MODEL_FILE_REF, ["fid"], unique=True)


def downgrade():
    op.drop_table(CMF_MODEL_FILE_REF)
