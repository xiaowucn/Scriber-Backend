"""add user notes table

Revision ID: 5b6c66aeefbb
Revises: 47c9fab0799f
Create Date: 2018-09-18 14:09:14.929833

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "5b6c66aeefbb"
down_revision = "a9dc1896d241"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_notes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("uid", sa.Integer, nullable=False),
        sa.Column("file_id", sa.Integer, nullable=False),
        sa.Column("rule_id", sa.Integer, nullable=False),
        sa.Column("notes", sa.String(255), nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
    )

    op.create_index("uix_user_notes_uid_fileid", "user_notes", ["uid", "file_id", "rule_id"], unique=True)

    op.create_table(
        "listing_rule", sa.Column("id", sa.Integer, primary_key=True), sa.Column("name", sa.String(255), nullable=False)
    )


def downgrade():
    op.drop_table("user_notes")
    op.drop_table("listing_rule")
