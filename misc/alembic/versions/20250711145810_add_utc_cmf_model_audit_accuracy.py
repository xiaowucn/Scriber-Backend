"""add_utc_cmf_model_audit_accuracy

Revision ID: 9e05240054d5
Revises: 0b2f0841ff47
Create Date: 2025-07-11 14:58:10.903992

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "9e05240054d5"
down_revision = "0b2f0841ff47"
branch_labels = None
depends_on = None
table_name = "cmf_model_audit_accuracy"


def upgrade():
    op.add_column(
        table_name,
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
    op.add_column(
        table_name,
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    op.drop_column(table_name, "created_utc")
    op.drop_column(table_name, "updated_utc")
