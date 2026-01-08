"""add_modify_cmfchina_user_check_fields

Revision ID: 9820eb5ddafa
Revises: ca181024b2f5
Create Date: 2025-02-26 16:41:25.632699

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from remarkable.db import IS_MYSQL

# revision identifiers, used by Alembic.
revision = "9820eb5ddafa"
down_revision = "ca181024b2f5"
branch_labels = None
depends_on = None

EXISTING_TYPE = sa.JSON if IS_MYSQL else JSONB


def upgrade():
    op.alter_column(
        "cmf_china_user_field_options", "field_options", new_column_name="check_fields", existing_type=EXISTING_TYPE
    )
    op.rename_table("cmf_china_user_field_options", "cmf_china_user_check_fields")


def downgrade():
    op.alter_column(
        "cmf_china_user_check_fields", "check_fields", new_column_name="field_options", existing_type=EXISTING_TYPE
    )
    op.rename_table("cmf_china_user_check_fields", "cmf_china_user_field_options")
