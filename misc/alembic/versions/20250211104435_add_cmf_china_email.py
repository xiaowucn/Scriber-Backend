"""add_cmf_china_email

Revision ID: b0dff5193988
Revises: 875978cc87b2
Create Date: 2025-02-11 10:44:35.517483

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "b0dff5193988"
down_revision = "875978cc87b2"
branch_labels = None
depends_on = None

CMF_CHINA_EMAIL = "cmf_china_email"
CMF_CHINA_EMAIL_FILE_INFO = "cmf_china_email_file_info"


def upgrade():
    op.create_table(
        CMF_CHINA_EMAIL,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("host", sa.String(255)),
        sa.Column("address", sa.String(255), index=True, unique=True),
        sa.Column("password", sa.String(255)),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
    )

    op.create_table(
        CMF_CHINA_EMAIL_FILE_INFO,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("message_id", sa.Integer),
        sa.Column("fid", sa.Integer),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
    )


def downgrade():
    op.drop_table(CMF_CHINA_EMAIL)
    op.drop_table(CMF_CHINA_EMAIL_FILE_INFO)
