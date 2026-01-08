"""add new table knowledge

Revision ID: e260b4e4f37b
Revises: 74e81916325f
Create Date: 2025-04-22 14:32:32.727551

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "e260b4e4f37b"
down_revision = "74e81916325f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "nafmii_knowledge",
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.Integer, nullable=False),
        sa.Column("user_id", sa.Integer, nullable=False, index=True),
        create_timestamp_field(
            "created_utc", sa.Integer, nullable=False, server_default=sa.text("extract(epoch from now())::int")
        ),
        create_timestamp_field(
            "updated_utc", sa.Integer, nullable=False, server_default=sa.text("extract(epoch from now())::int")
        ),
        create_timestamp_field("deleted_utc", sa.Integer, nullable=False, server_default=sa.text("0")),
    )
    op.create_index("nafmii_knowledge_type_name_key", "nafmii_knowledge", ["type", "name"], unique=True)


def downgrade():
    op.drop_table("nafmii_knowledge")
