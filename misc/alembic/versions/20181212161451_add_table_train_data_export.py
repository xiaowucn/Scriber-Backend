"""add table training_data

Revision ID: 1c93b2b267e8
Revises: a402dd9b21e0
Create Date: 2018-12-12 16:14:51.972376

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "1c93b2b267e8"
down_revision = "a402dd9b21e0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "training_data",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("mold", sa.Integer, nullable=False),
        sa.Column("from_id", sa.Integer),
        sa.Column("to_id", sa.Integer),
        sa.Column("task_total", sa.Integer, server_default=sa.text("0")),
        sa.Column("task_done", sa.Integer, server_default=sa.text("0")),
        sa.Column("zip_path", sa.String(255)),
        create_timestamp_field(
            "created_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
    )


def downgrade():
    op.drop_table("training_data")
