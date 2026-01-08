"""add new table knowledge_detail

Revision ID: 1ac774767290
Revises: e260b4e4f37b
Create Date: 2025-04-23 11:27:26.479854

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "1ac774767290"
down_revision = "e260b4e4f37b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "nafmii_knowledge_detail",
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("knowledge_id", sa.Integer, nullable=False, index=True),
        sa.Column("type", sa.Integer, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.String(1000), nullable=False, server_default=""),
        sa.Column("filename", sa.String(500), nullable=False, server_default=""),
        sa.Column("file_path", sa.String(500), nullable=False, server_default=""),
        create_timestamp_field(
            "created_utc", sa.Integer, nullable=False, server_default=sa.text("extract(epoch from now())::int")
        ),
        create_timestamp_field(
            "updated_utc", sa.Integer, nullable=False, server_default=sa.text("extract(epoch from now())::int")
        ),
        create_timestamp_field("deleted_utc", sa.Integer, nullable=False, server_default=sa.text("0")),
    )


def downgrade():
    op.drop_table("nafmii_knowledge_detail")
