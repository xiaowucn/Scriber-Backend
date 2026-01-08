"""add field task_type

Revision ID: 8dbdb1f4ad3c
Revises: aa280dfe08e0
Create Date: 2021-11-01 13:23:12.550833

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8dbdb1f4ad3c"
down_revision = "aa280dfe08e0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file", sa.Column("task_type", sa.String(255), server_default="extract"))


def downgrade():
    op.drop_column("file", "task_type")
