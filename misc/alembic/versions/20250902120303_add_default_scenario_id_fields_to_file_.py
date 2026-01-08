"""add default_scenario_id fields to file_tree and project table

Revision ID: 8b7bbb10703f
Revises: 0ab80d4c5b03
Create Date: 2025-09-02 12:03:03.199291
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8b7bbb10703f"
down_revision = "0ab80d4c5b03"
branch_labels = None
depends_on = None

table_names = ["file_project", "file_tree"]
column_id = "default_scenario_id"
column_str = "default_task_type"


def upgrade():
    for table_name in table_names:
        op.add_column(table_name, sa.Column(column_id, sa.Integer))
        op.add_column(table_name, sa.Column(column_str, sa.String(255)))


def downgrade():
    for table_name in table_names:
        op.drop_column(table_name, column_id)
        op.drop_column(table_name, column_str)
