"""add unique constraint to chinaamc_compare_task

Revision ID: 8c066c56f681
Revises: a5fc7e59994f
Create Date: 2024-04-15 11:46:56.483250

"""

import sqlalchemy as sa
from alembic import op

from remarkable.db import IS_MYSQL

# revision identifiers, used by Alembic.
revision = "8c066c56f681"
down_revision = "a5fc7e59994f"
branch_labels = None
depends_on = None


def upgrade():
    if IS_MYSQL:
        return
    op.drop_index("chinaamc_compare_task_name_key", "chinaamc_compare_task")
    op.execute(
        """
        with keep_ids as (
            SELECT MIN(id) AS id
            FROM chinaamc_compare_task
            WHERE deleted_utc = 0
            GROUP BY name
            HAVING COUNT(1) > 1
            union all
            SELECT MIN(id) AS id
            FROM chinaamc_compare_task
            WHERE deleted_utc = 0
            GROUP BY name
            HAVING COUNT(1) = 1
        )
        DELETE from chinaamc_compare_task WHERE id NOT IN (SELECT id FROM keep_ids) AND deleted_utc = 0;
    """
    )
    op.create_index(
        "chinaamc_compare_task_name_key",
        "chinaamc_compare_task",
        ["name"],
        unique=True,
        postgresql_where=sa.text("deleted_utc = 0"),
    )


def downgrade():
    pass
