"""add_updated_utc_for_cmf_china_email

Revision ID: 08037aaaa0dd
Revises: f6692e028c75
Create Date: 2025-04-30 09:54:59.086980

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "08037aaaa0dd"
down_revision = "f6692e028c75"
branch_labels = None
depends_on = None

CMF_CHINA_EMAIL = "cmf_china_email"


def upgrade():
    op.add_column(
        CMF_CHINA_EMAIL,
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    op.drop_column(CMF_CHINA_EMAIL, "updated_utc")
