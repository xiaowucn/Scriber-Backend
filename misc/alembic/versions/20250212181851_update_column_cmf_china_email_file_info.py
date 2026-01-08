"""update_column_cmf_china_email_file_info

Revision ID: 8589376f779d
Revises: b0dff5193988
Create Date: 2025-02-12 18:18:51.498091

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8589376f779d"
down_revision = "b0dff5193988"
branch_labels = None
depends_on = None

CMF_CHINA_EMAIL = "cmf_china_email"
CMF_CHINA_EMAIL_FILE_INFO = "cmf_china_email_file_info"


def upgrade():
    op.alter_column(CMF_CHINA_EMAIL, "address", new_column_name="account", existing_type=sa.String(255))
    op.alter_column(CMF_CHINA_EMAIL_FILE_INFO, "message_id", new_column_name="email_id", existing_type=sa.Integer)


def downgrade():
    op.alter_column(CMF_CHINA_EMAIL, "account", new_column_name="address", existing_type=sa.String(255))
    op.alter_column(CMF_CHINA_EMAIL_FILE_INFO, "email_id", new_column_name="message_id", existing_type=sa.Integer)
