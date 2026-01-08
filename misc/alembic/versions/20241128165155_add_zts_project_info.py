"""add_zts_project_info

Revision ID: 2ffc42d5b16a
Revises: 4537191d8b24
Create Date: 2024-11-22 16:51:55.326142

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "2ffc42d5b16a"
down_revision = "4537191d8b24"
branch_labels = None
depends_on = None

# Table names as variables
ZTS_PROJECT_INFO = "zts_project_info"


def upgrade():
    op.create_table(
        ZTS_PROJECT_INFO,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, nullable=False, index=True),
        sa.Column("exchange", sa.String(255)),
        sa.Column("inspected_utc", sa.Integer, server_default=sa.text("0")),
        sa.Column("restricted_funds", sa.Boolean),
        sa.Column("borrowing", sa.Boolean),
        sa.Column("guarantee", sa.Boolean),
        sa.Column("consistency", sa.Boolean),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    op.drop_table(ZTS_PROJECT_INFO)
