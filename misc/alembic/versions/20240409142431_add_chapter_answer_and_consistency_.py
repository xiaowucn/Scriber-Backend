"""add chapter_answer and consistency_answer to compare task

Revision ID: db4a81c092f0
Revises: 53a15e5b6555
Create Date: 2024-04-09 14:24:31.045002

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field

# revision identifiers, used by Alembic.
revision = "db4a81c092f0"
down_revision = "53a15e5b6555"
branch_labels = None
depends_on = None

table = "chinaamc_compare_task"


def upgrade():
    op.add_column(table, sa.Column("chapter_status", sa.Integer, nullable=False, server_default=sa.text("0")))
    op.add_column(table, create_jsonb_field("chapter_answer", nullable=False, server_default=sa.text("'[]'")))
    op.add_column(
        table,
        sa.Column("consistency_status", sa.Integer, nullable=False, server_default=sa.text("0")),
    )
    op.add_column(table, create_jsonb_field("consistency_answer", nullable=False, server_default=sa.text("'[]'")))


def downgrade():
    op.drop_column(table, "consistency_answer")
    op.drop_column(table, "consistency_status")
    op.drop_column(table, "chapter_answer")
    op.drop_column(table, "chapter_status")
