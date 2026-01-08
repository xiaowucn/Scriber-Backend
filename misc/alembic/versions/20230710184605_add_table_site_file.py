"""add table site file

Revision ID: 375ec09b2ff6
Revises: 9b95d259cbfb
Create Date: 2023-07-10 18:46:05.965729

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "375ec09b2ff6"
down_revision = "9b95d259cbfb"
branch_labels = None
depends_on = None


def upgrade():
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


def downgrade():
    op.drop_table("site_file")
