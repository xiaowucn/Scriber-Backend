"""add_cmf_china_panorama

Revision ID: 685e3097facb
Revises: b449768c77a7
Create Date: 2025-02-25 11:28:35.545906

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "685e3097facb"
down_revision = "b449768c77a7"
branch_labels = None
depends_on = None


CMF_CHINA_FILE_REVIEWED = "cmf_china_file_reviewed"
CMF_CHINA_USER_FIELD_OPTIONS = "cmf_china_user_field_options"


def upgrade():
    op.create_table(
        CMF_CHINA_FILE_REVIEWED,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("uid", sa.Integer),
        sa.Column("file_id", sa.Integer, index=True, unique=True),
        sa.Column("reviewed_count", sa.Integer, server_default="1"),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
    )

    op.create_table(
        CMF_CHINA_USER_FIELD_OPTIONS,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("uid", sa.Integer),
        sa.Column("mold_id", sa.Integer),
        create_jsonb_field("field_options", nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
    )

    op.create_index(
        "uix_cmf_china_user_field_options_uid_mold_id", CMF_CHINA_USER_FIELD_OPTIONS, ["uid", "mold_id"], unique=True
    )


def downgrade():
    op.drop_table(CMF_CHINA_FILE_REVIEWED)
    op.drop_table(CMF_CHINA_USER_FIELD_OPTIONS)
