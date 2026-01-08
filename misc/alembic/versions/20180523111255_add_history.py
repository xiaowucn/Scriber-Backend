"""add_history

Revision ID: c33f64548a56
Revises: 1bd285c1b8f5
Create Date: 2018-05-23 11:12:55.557264

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "c33f64548a56"
down_revision = "1bd285c1b8f5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "history",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("uid", sa.Integer, nullable=False, index=True),
        sa.Column("qid", sa.Integer, nullable=True, index=True),
        sa.Column("action", sa.Integer, nullable=False),
        create_timestamp_field(
            "action_time", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
    )


def downgrade():
    op.drop_table("history")
