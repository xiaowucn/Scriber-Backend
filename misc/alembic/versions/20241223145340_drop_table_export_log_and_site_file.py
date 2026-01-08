"""drop table export log and site file

Revision ID: afe1938aaf6e
Revises: 3722ff5b71ff
Create Date: 2024-12-23 14:53:40.945580

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "afe1938aaf6e"
down_revision = "3722ff5b71ff"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("export_log")
    op.drop_table("site_file")


def downgrade():
    op.create_table(
        "export_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("did", sa.Integer, nullable=False, index=True, unique=True),
        sa.Column("force_redo", sa.Boolean, server_default=sa.text("false")),
        sa.Column("farm_id", sa.Integer, nullable=False),
        sa.Column("status", sa.Integer, nullable=False, default=0),
        sa.Column("data", sa.Text),
        create_timestamp_field(
            "export_time", sa.Integer, server_default=sa.text("extract(epoch from now())::INTEGER")
        ),  # 导出的时间
        create_timestamp_field(
            "created_utc",
            sa.Integer,
            nullable=False,
            server_default=sa.text("extract(epoch from now())::INTEGER"),
        ),
        create_timestamp_field(
            "updated_utc",
            sa.Integer,
            nullable=False,
            server_default=sa.text("extract(epoch from now())::INTEGER"),
        ),
    )
    op.create_table(
        "site_file",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("file_id", sa.Integer, nullable=False, index=True),
        sa.Column("type", sa.String(255), nullable=False, server_default=sa.text("''")),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("published_at", sa.Integer, nullable=False),
        create_jsonb_field("stock_info", nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("link", sa.String(255), nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, nullable=False, server_default=sa.text("0")),
    )

    op.create_index("site_file_source_external_id_key", "site_file", columns=["source", "external_id"], unique=True)
