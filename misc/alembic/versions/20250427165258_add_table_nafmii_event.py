"""add column to history

Revision ID: 4352723890be
Revises: 1ac774767290
Create Date: 2025-04-27 16:52:58.341580

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "4352723890be"
down_revision = "749103a7944e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "nafmii_event",
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("history_id", sa.Integer, nullable=False),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("type", sa.Integer, nullable=False),
        sa.Column("status", sa.Integer, nullable=False),
        sa.Column("menu", sa.String(50), nullable=False, server_default="-"),
        sa.Column("subject", sa.String(50), nullable=False, server_default="-"),
        sa.Column("ip", sa.String(50), nullable=False),
        sa.Column("client", sa.String(50), nullable=False),
        sa.Column("content", sa.String(1024), nullable=False, server_default=""),
        create_timestamp_field(
            "created_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
    )
    op.create_index("nafmii_event_history_id_key", "nafmii_event", ["history_id"], unique=True)


def downgrade():
    op.drop_table("nafmii_event")
