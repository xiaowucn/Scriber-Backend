"""Create table log

Revision ID: f655b554d14d
Revises: 38db66e3a598
Create Date: 2018-01-11 09:44:31.097959

"""

import json

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "f655b554d14d"
down_revision = "38db66e3a598"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "answer_dm_log",
        sa.Column("id", sa.Integer, primary_key=True),  # answer_dm_log_pkey
        sa.Column(
            "type",
            sa.String(255),
            nullable=False,
            server_default=sa.text("'DELETE'"),
            comment=json.dumps(["INSERT", "UPDATE", "DELETE"]),
        ),
        sa.Column("qid", sa.Integer, nullable=False, index=True),  # ix_answer_dm_log_aid
        sa.Column("uid", sa.Integer, nullable=False, index=True),  # ix_answer_dm_log_qid
        sa.Column("aid", sa.Integer, nullable=False, index=True),  # ix_answer_dm_log_uid
        sa.Column("data", sa.JSON, nullable=False),
        sa.Column("status", sa.Integer, nullable=False),
        sa.Column("standard", sa.Integer, nullable=False),
        sa.Column("result", sa.Integer, nullable=False),
        create_timestamp_field("dm_utc", sa.Integer, server_default=sa.text("extract(EPOCH FROM now())::INTEGER")),
        sa.Column("created_utc", sa.Integer, nullable=False),
        sa.Column("updated_utc", sa.Integer, nullable=False),
    )
    op.create_index("answer_dm_log_type_qid_uid_aid_key", "answer_dm_log", ["type", "qid", "uid", "aid"], unique=True)


def downgrade():
    op.drop_table("answer_dm_log")
