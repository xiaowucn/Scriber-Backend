"""add diff tables

Revision ID: 817030ae0c71
Revises: 069876c9170f
Create Date: 2019-03-14 11:54:02.254914

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "817030ae0c71"
down_revision = "069876c9170f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "diff_file",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("uid", sa.Integer, nullable=False, index=True),
        sa.Column("name", sa.String(1024), nullable=False),
        sa.Column("hash", sa.String(32), nullable=False),
        sa.Column("pdf_hash", sa.String(32)),
        sa.Column("status", sa.Integer),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field(
            "updated_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
    )
    op.create_index("ix_diff_file_uid_hash", "diff_file", ["uid", "hash"], unique=True)

    op.create_table(
        "diff_record",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("uid", sa.Integer, nullable=False, index=True),
        sa.Column("fid1", sa.Integer, nullable=False, index=True),
        sa.Column("fid2", sa.Integer, nullable=False, index=True),
        sa.Column("name1", sa.String(1024)),
        sa.Column("name2", sa.String(1024)),
        sa.Column("dst_fid1", sa.Integer),
        sa.Column("dst_fid2", sa.Integer),
        sa.Column("cmp_id", sa.Integer),
        sa.Column("type", sa.Integer, nullable=False),
        sa.Column("total_diff", sa.Integer),
        sa.Column("status", sa.Integer, nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field(
            "updated_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
    )
    op.create_index("ix_diff_record_uid_fid1_fid2", "diff_record", ["uid", "fid1", "fid2"], unique=True)


def downgrade():
    op.drop_table("diff_file")
    op.drop_table("diff_record")
