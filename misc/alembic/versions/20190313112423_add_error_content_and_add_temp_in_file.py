"""add_error_content_and_add_temp_in_file

Revision ID: 069876c9170f
Revises: afdc6d64506d
Create Date: 2019-03-13 11:24:23.649319

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "069876c9170f"
down_revision = "afdc6d64506d"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file", sa.Column("annotation_path", sa.String(255)))

    op.create_table(
        "error_content",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("uid", sa.Integer),
        sa.Column("fid", sa.Integer),
        sa.Column("rule_result_id", sa.Integer),
        sa.Column("content", sa.String(8096)),
        sa.Column("error_status", sa.Integer),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
    )


def downgrade():
    op.drop_table("error_content")
    op.drop_column("file", "annotation_path")
