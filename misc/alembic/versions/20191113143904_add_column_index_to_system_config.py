"""add column index to system_config

Revision ID: 8d7b566995db
Revises: 0fa641f8c14f
Create Date: 2019-11-13 14:39:04.264562

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8d7b566995db"
down_revision = "0fa641f8c14f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("system_config", sa.Column("index", sa.String(255), nullable=False, server_default=""))
    op.add_column("system_config", sa.Column("enable", sa.Integer, nullable=False, server_default="1"))


def downgrade():
    op.drop_column("system_config", "index")
    op.drop_column("system_config", "enable")
