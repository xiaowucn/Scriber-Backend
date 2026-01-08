"""add_user

Revision ID: 1bd285c1b8f5
Revises: 1bfeb34e6a27
Create Date: 2018-05-23 10:59:35.291086

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "1bd285c1b8f5"
down_revision = "1bfeb34e6a27"
branch_labels = None
depends_on = None

fields = (
    create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
)


def upgrade():
    op.create_table(
        "admin_user",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("password", sa.String(255), nullable=False),
        sa.Column("salt", sa.String(255), nullable=False),
        sa.Column("permission", sa.JSON),
        sa.Column("login_utc", sa.Integer, server_default=sa.text("0")),  # 最近一次登录时间
        sa.Column("login_count", sa.Integer, server_default=sa.text("0")),  # 登录访问次数
        *fields,
    )
    op.create_unique_constraint("admin_user_name_key", "admin_user", ["name"])


def downgrade():
    op.drop_table("admin_user")
