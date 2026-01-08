"""add unique index to compare task

Revision ID: 53584c2a771b
Revises: 0d98bb6e2ab6
Create Date: 2024-04-03 15:57:07.961815

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "53584c2a771b"
down_revision = "0d98bb6e2ab6"
branch_labels = None
depends_on = None

table = "chinaamc_compare_task"


def upgrade():
    op.create_index("chinaamc_compare_task_name_key", table, ["name"], unique=True)
    op.drop_column(table, "rank")


def downgrade():
    op.drop_index("chinaamc_compare_task_name_key", table)
    op.add_column(table, sa.Column("rank", sa.Integer, nullable=True))
