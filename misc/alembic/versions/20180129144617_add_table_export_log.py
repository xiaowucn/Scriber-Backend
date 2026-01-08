"""add table export_log

Revision ID: 8f08a5390eca
Revises: f655b554d14d
Create Date: 2018-01-29 14:46:17.718990

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "8f08a5390eca"
down_revision = "f655b554d14d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "export_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("did", sa.Integer, nullable=False, index=True, unique=True),
        sa.Column("force_redo", sa.Boolean, server_default=sa.text("false")),
        sa.Column("farm_id", sa.Integer, nullable=False),
        sa.Column("status", sa.Integer, nullable=False, default=0),
        sa.Column("data", sa.Text),
        create_timestamp_field(
            "export_time", sa.Integer, server_default=sa.text("extract(EPOCH FROM now())::INTEGER")
        ),  # 导出的时间
        create_timestamp_field(
            "created_utc",
            sa.Integer,
            nullable=False,
            server_default=sa.text("extract(EPOCH FROM now())::INTEGER"),
        ),
        create_timestamp_field(
            "updated_utc",
            sa.Integer,
            nullable=False,
            server_default=sa.text("extract(EPOCH FROM now())::INTEGER"),
        ),
    )


def downgrade():
    op.drop_table("export_log")
