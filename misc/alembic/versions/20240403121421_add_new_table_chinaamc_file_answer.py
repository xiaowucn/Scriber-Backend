"""add new table chinaamc file answer

Revision ID: 0d98bb6e2ab6
Revises: 36d690d4c2e0
Create Date: 2024-04-03 12:14:21.621692

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "0d98bb6e2ab6"
down_revision = "36d690d4c2e0"
branch_labels = None
depends_on = None

table = "chinaamc_file_answer"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("task_id", sa.Integer, nullable=False),
        sa.Column("fid", sa.Integer, nullable=False, index=True),
        sa.Column("status", sa.Integer, nullable=False, server_default=sa.text("0")),
        create_jsonb_field("schema", nullable=False, server_default=sa.text("'[]'::jsonb")),
        create_jsonb_field("answer", nullable=False, server_default=sa.text("'[]'::jsonb")),
        create_timestamp_field(
            "created_utc", sa.Integer, nullable=False, server_default=sa.text("extract(epoch from now())::int")
        ),
        create_timestamp_field(
            "updated_utc", sa.Integer, nullable=False, server_default=sa.text("extract(epoch from now())::int")
        ),
    )
    op.create_index("chinaamc_file_answer_task_id_fid_key", table, ["task_id", "fid"], unique=True)


def downgrade():
    op.drop_table(table)
