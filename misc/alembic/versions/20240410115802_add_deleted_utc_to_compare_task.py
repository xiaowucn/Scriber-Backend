"""add deleted_utc to compare task

Revision ID: fb56fc18d5d8
Revises: db4a81c092f0
Create Date: 2024-04-10 11:58:02.110332

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "fb56fc18d5d8"
down_revision = "db4a81c092f0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "chinaamc_compare_task", sa.Column("deleted_utc", sa.Integer, nullable=False, server_default=sa.text("0"))
    )
    op.drop_index("chinaamc_compare_task_name_key", "chinaamc_compare_task")
    op.create_index(
        "chinaamc_compare_task_name_key", "chinaamc_compare_task", ["name"], postgresql_where=sa.text("deleted_utc = 0")
    )


def downgrade():
    op.drop_index("chinaamc_compare_task_name_key")
    op.drop_column("chinaamc_compare_task", "deleted_utc")
    op.create_index("chinaamc_compare_task_name_key", "chinaamc_compare_task", ["name"], unique=True)
