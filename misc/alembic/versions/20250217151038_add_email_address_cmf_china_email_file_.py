"""add_email_address_cmf_china_email_file_info

Revision ID: fe28e59c62bd
Revises: 260db1e01a54
Create Date: 2025-02-17 15:10:38.862286

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "fe28e59c62bd"
down_revision = "260db1e01a54"
branch_labels = None
depends_on = None

CMF_CHINA_EMAIL_FILE_INFO = "cmf_china_email_file_info"


def upgrade():
    op.add_column(CMF_CHINA_EMAIL_FILE_INFO, sa.Column("host", sa.String(255)))
    op.add_column(CMF_CHINA_EMAIL_FILE_INFO, sa.Column("account", sa.String(255)))


def downgrade():
    op.drop_column(CMF_CHINA_EMAIL_FILE_INFO, "host")
    op.drop_column(CMF_CHINA_EMAIL_FILE_INFO, "account")
