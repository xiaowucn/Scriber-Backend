"""add task_action field

Revision ID: 61fbd211374e
Revises: 31bbce390d07
Create Date: 2023-05-11 10:21:01.567004

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.constants import HistoryAction

# revision identifiers, used by Alembic.
revision = "61fbd211374e"
down_revision = "31bbce390d07"
branch_labels = None
depends_on = None

table_name = "training_data"


def upgrade():
    op.add_column(
        table_name,
        sa.Column("task_action", sa.Integer, server_default=sa.text(f"{HistoryAction.CREATE_TRAINING_DATA}")),
    )


def downgrade():
    op.drop_column(table_name, "task_action")
