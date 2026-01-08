"""add started to compare task

Revision ID: a5fc7e59994f
Revises: fb56fc18d5d8
Create Date: 2024-04-10 12:42:57.360146

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a5fc7e59994f"
down_revision = "fb56fc18d5d8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "chinaamc_compare_task", sa.Column("started", sa.Boolean, nullable=False, server_default=sa.text("false"))
    )


def downgrade():
    op.drop_column("chinaamc_compare_task", "started")
