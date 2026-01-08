"""add_stat_after_push

Revision ID: 61841645f5f7
Revises: ea7b1f29550d
Create Date: 2024-09-27 08:38:19.596166

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "61841645f5f7"
down_revision = "685bcb7407ce"
branch_labels = None
depends_on = None
table = "ecitic_file_info"


def upgrade():
    op.add_column(table, sa.Column("stat_after_push", sa.Boolean, server_default=sa.text("true")))


def downgrade():
    op.drop_column(table, "stat_after_push")
