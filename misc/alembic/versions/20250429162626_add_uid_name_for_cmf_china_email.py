"""add_uid_name_for_cmf_china_email

Revision ID: f6692e028c75
Revises: 749103a7944e
Create Date: 2025-04-29 16:26:26.726202

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f6692e028c75"
down_revision = "4352723890be"
branch_labels = None
depends_on = None

CMF_CHINA_EMAIL = "cmf_china_email"


def upgrade():
    op.add_column(CMF_CHINA_EMAIL, sa.Column("uid", sa.Integer, server_default=sa.text("1")))


def downgrade():
    op.drop_column(CMF_CHINA_EMAIL, "uid")
