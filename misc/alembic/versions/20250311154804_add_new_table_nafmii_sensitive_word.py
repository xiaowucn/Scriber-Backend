"""add new table nafmii_sensitive_word

Revision ID: b570ba455f39
Revises: 9820eb5ddafa
Create Date: 2025-03-11 15:48:04.511663

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "b570ba455f39"
down_revision = "9820eb5ddafa"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "nafmii_sensitive_word",
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sys_id", sa.Integer, nullable=True, server_default=sa.text("0")),
        sa.Column("type_id", sa.Integer, nullable=False, index=True),
        sa.Column("user_id", sa.Integer, nullable=False, index=True),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
    )

    op.create_index("nafmii_sensitive_word_sys_id_name_key", "nafmii_sensitive_word", ["sys_id", "name"], unique=True)

    op.create_table(
        "nafmii_word_type",
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
    )

    op.create_index("nafmii_word_type_name_key", "nafmii_word_type", ["name"], unique=True)


def downgrade():
    op.drop_table("nafmii_sensitive_word")
    op.drop_table("nafmii_word_type")
