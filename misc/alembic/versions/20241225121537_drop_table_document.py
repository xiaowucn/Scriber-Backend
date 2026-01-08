"""drop table document

Revision ID: c1679c51a5d8
Revises: afe1938aaf6e
Create Date: 2024-12-25 12:15:37.036893

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "c1679c51a5d8"
down_revision = "afe1938aaf6e"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    for table in {"document", "user_notes", "listing_rule", "question_result", "file_template"}.intersection(tables):
        op.drop_table(table)


def downgrade():
    op.create_table(
        "document",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("data", sa.JSON, nullable=False),
        sa.Column("checksum", sa.String(128), nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
    op.create_index("document_checksum_key", "document", ["checksum"], unique=True)

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
    op.create_table(
        "question_result",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("aid", sa.Integer, nullable=False, unique=True),
        sa.Column("correct", sa.Integer, nullable=False),
        sa.Column("incorrect", sa.Integer, nullable=False),
        sa.Column("blank", sa.Integer, nullable=False),
    )

    op.create_table(
        "file_template",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("hash", sa.String(32)),
        sa.Column("mold", sa.Integer),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("deleted_utc", sa.Integer, server_default=sa.text("0")),
    )
