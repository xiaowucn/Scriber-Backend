"""add_fields_for_cmf_china_email

Revision ID: 749103a7944e
Revises: 1ac774767290
Create Date: 2025-04-27 11:58:41.047691

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "749103a7944e"
down_revision = "1ac774767290"
branch_labels = None
depends_on = None


CMF_CHINA_EMAIL = "cmf_china_email"


def upgrade():
    op.add_column(CMF_CHINA_EMAIL, sa.Column("mold_id", sa.Integer, nullable=True))
    op.add_column(CMF_CHINA_EMAIL, sa.Column("pid", sa.Integer, nullable=True))
    op.drop_index("ix_cmf_china_email_address", CMF_CHINA_EMAIL)
    op.create_index("cmf_china_email_host_account_key", CMF_CHINA_EMAIL, ["host", "account"], unique=True)


def downgrade():
    op.drop_column(CMF_CHINA_EMAIL, "mold_id")
    op.drop_column(CMF_CHINA_EMAIL, "pid")
    op.drop_index("cmf_china_email_host_account_key", CMF_CHINA_EMAIL)
